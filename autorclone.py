import os
import json
import time
import glob
import psutil
import logging
import subprocess
import configparser

import filelock

from logging.handlers import RotatingFileHandler

# ------------配置项开始------------------

# Account目录
sa_json_folder = r'/root/folderrclone/accounts'  # 绝对目录，最后没有 '/'，路径中不要有空格

# Rclone运行命令
# 1. 填你正在用/想要用的，这里写的是move，也可以是copy/sync ......
# 2. 建议加上 `--rc` ，不加也没事，后面脚本会自动加上的
# 3. 因为不起screen，如果你希望关注rclone运行的状态，请一定要用 `--log-file` 将rclone输出重定向到文件
cmd_rclone = 'rclone move /home/tomove GDrive:/tmp --drive-server-side-across-configs -v --log-file /tmp/rclone.log'

# 检查rclone间隔 (s)
check_after_start = 60  # 在拉起rclone进程后，休息xxs后才开始检查rclone状态，防止 rclone rc core/stats 报错退出
check_interval = 10  # 主进程每次进行rclone rc core/stats检查的间隔

# rclone帐号更换监测条件
switch_sa_rules = {
    'up_than_750': False,  # 当前帐号已经传过750G
    'zero_transferred_between_check_interval': True,  # 两次检查间隔期间rclone传输的量为0
    'error_user_rate_limit': True,  # Rclone 直接提示rate limit错误
    'all_transfers_in_zero': True,  # 当前所有transfers传输size均为0
}

# TODO rclone帐号切换方法 (runtime or config)
# runtime 是修改启动rclone时附加的 `--drive-service-account-file` 参数
# config 是修改rclone的配置文件 `$HOME/.config/rclone/rclone.conf` ，此时你需要指定后面的rclone配置参数参数
switch_sa_way = 'runtime'

# rclone配置参数 （当且仅当 switch_sa_way 为 `config` 时使用，且需要修改）
rclone_config_path = '/root/.config/rclone/rclone.conf'  # Rclone 配置文件位置
rclone_dest_name = 'GDrive'  # Rclone目的地名称

# 本脚本临时文件
instance_lock_path = r'/tmp/autorclone.lock'
instance_config_path = r'/tmp/autorclone.conf'

# 本脚本运行日志
script_log_file = r'/tmp/autorclone.log'
logging_datefmt = "%m/%d/%Y %I:%M:%S %p"
logging_format = "%(asctime)s - %(levelname)s - %(threadName)s - %(funcName)s - %(message)s"

# ------------配置项结束------------------

# 运行变量
instance_config = {}
sa_jsons = []

# 日志相关
logFormatter = logging.Formatter(fmt=logging_format, datefmt=logging_datefmt)

logger = logging.getLogger()
logger.setLevel(logging.NOTSET)
while logger.handlers:  # Remove un-format logging in Stream, or all of messages are appearing more than once.
    logger.handlers.pop()

if script_log_file:
    fileHandler = RotatingFileHandler(filename=script_log_file, mode='a',
                                      backupCount=2, maxBytes=5 * 1024 * 1024,
                                      encoding=None, delay=0)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


def write_config(name, value):
    instance_config[name] = value
    with open(instance_config_path, 'w') as f:
        json.dump(instance_config, f, sort_keys=True)


# 获得下一个Service Account Credentials JSON file path
def get_next_sa_json_path(_last_sa):
    if _last_sa not in sa_jsons:  # 空字符串或者错误的sa_json_path，从头开始取
        next_sa_index = 0
    else:
        _last_sa_index = sa_jsons.index(_last_sa)
        next_sa_index = _last_sa_index + 1
    # 超过列表长度从头开始取
    if next_sa_index > len(sa_jsons):
        next_sa_index = next_sa_index - len(sa_jsons)
    return sa_jsons[next_sa_index]


def switch_sa_by_config(cur_sa):
    # 获得rclone配置
    config = configparser.ConfigParser()
    config.read(rclone_config_path)

    # 更改SA信息
    sa_in_config = config[rclone_dest_name]['service_account_file']
    config[rclone_dest_name]['service_account_file'] = cur_sa
    logger.info('Change rclone.conf SA information from %s to %s' % (sa_in_config, cur_sa))

    # 保存
    with open(rclone_config_path, 'w') as configfile:
        config.write(configfile)

    logger.info('Change rclone.conf SA information Success')


def get_email_from_sa(sa):
    return json.load(open(sa, 'r'))['client_email']


if __name__ == '__main__':
    # 单例模式 (￣y▽,￣)╭
    instance_check = filelock.FileLock(instance_lock_path)
    with instance_check.acquire(timeout=0):
        # 加载account信息
        sa_jsons = glob.glob(os.path.join(sa_json_folder, '*.json'))
        if len(sa_jsons) == 0:
            logger.error('No Service Account Credentials JSON file exists.')
            exit(1)

        # 加载instance配置
        if os.path.exists(instance_config_path):
            logger.info('Instance config exist, Load it...')
            config_raw = open(instance_config_path).read()
            instance_config = json.loads(config_raw)

        # 对上次记录的pid信息进行检查，并强行杀掉，防止孤儿进程问题
        if 'last_pid' in instance_config:
            last_pid = instance_config.get('last_pid')
            logger.debug('Last PID exist in config, Start to check if it is a rclone process and still alive')
            if psutil.pid_exists(last_pid):
                last_proc = psutil.Process(last_pid)
                logger.error('The Last PID information - pid: %s, name: %s', (last_pid, last_proc.name()))
                if last_proc.name().find('rclone') > -1:
                    logger.fatal('The last process seems still alive, Force Killed')
                    last_proc.kill()

        # 对上次记录的sa信息进行检查，如果有的话，重排sa_jsons
        # 这样我们就每次都从一个新的750G开始了
        last_sa = instance_config.get('last_sa', '')
        if last_sa in sa_jsons:
            logger.info('Get `last_sa` from config, resort list `sa_jsons`')
            last_sa_index = sa_jsons.index(last_sa)
            sa_jsons = sa_jsons[last_sa_index:] + sa_jsons[:last_sa_index]

        # 修正cmd_rclone 防止 `--rc` 缺失
        if cmd_rclone.find('--rc') == -1:
            logger.warning('Lost important param `--rc` in rclone commands, AutoAdd it.')
            cmd_rclone += ' --rc'

        # 帐号切换循环
        while True:
            logger.info('Switch to next SA..........')
            current_sa = get_next_sa_json_path(last_sa)
            write_config('last_sa', current_sa)
            logger.info('Get SA information, file: %s , email: %s' % (current_sa, get_email_from_sa(current_sa)))

            # 切换Rclone运行命令
            if switch_sa_way == 'config':
                switch_sa_by_config(current_sa)
                cmd_rclone_current_sa = cmd_rclone
            else:
                # 默认情况视为`runtime`，附加'--drive-service-account-file'参数
                cmd_rclone_current_sa = cmd_rclone + ' --drive-service-account-file %s' % (current_sa,)

            # 起一个subprocess调rclone
            proc = subprocess.Popen(cmd_rclone_current_sa, shell=True)

            # 等待，以便rclone完全起起来
            logger.info('Let wait %s seconds to full call rclone subprocess' % (check_after_start,))
            time.sleep(check_after_start)
            logger.info('Run Rclone command: `%s` Success in pid %s' % (cmd_rclone_current_sa, proc.pid,))
            write_config('last_pid', proc.pid)  # 记录pid信息

            # 主进程使用 `rclone rc core/stats` 检查子进程情况
            cnt_error = 0
            cnt_403_retry = 0
            cnt_transfer_last = 0
            cnt_get_rate_limit = False
            while True:
                try:
                    response = subprocess.check_output('rclone rc core/stats', shell=True)
                except subprocess.CalledProcessError as error:
                    cnt_error = cnt_error + 1
                    err_msg = 'check core/stats failed for %s times,' % cnt_error
                    if cnt_error > 3:
                        logger.error(err_msg + ' Force kill exist rclone process %s.' % proc.pid)
                        proc.kill()
                        exit(1)

                    logger.warning(err_msg + ' Wait %s seconds to recheck.' % check_interval)
                    time.sleep(check_interval)
                    continue  # 重新检查
                else:
                    cnt_error = 0

                # 解析 `rclone rc core/stats` 输出
                response_json = json.loads(response.decode('utf-8').replace('\0', ''))
                cnt_transfer = response_json.get('bytes', 0)

                # 输出当前情况
                logger.info('Transfer Status - Upload: %s GiB, Avg upspeed: %s MiB/s, Transfered: %s.' % (
                    response_json.get('bytes', 0) / pow(1024, 3),
                    response_json.get('speed', 0) / pow(1024, 2),
                    response_json.get('transfers', 0)
                ))

                # 判断是否应该进行切换
                should_switch = 0
                switch_sa_level = 0

                # 检查当前总上传是否超过 750 GB
                if switch_sa_rules.get('up_than_750', False):
                    switch_sa_level += 1

                    if cnt_transfer > 750 * pow(1000, 3):  # 这里是 750GB 而不是 750GiB
                        should_switch += 1

                # 检查监测期间rclone传输的量
                if switch_sa_rules.get('zero_transferred_between_check_interval', False):
                    switch_sa_level += 1

                    if cnt_transfer - cnt_transfer_last == 0:  # 未增加
                        cnt_403_retry += 1
                        if cnt_403_retry > 100:  # 超过100次检查均未增加
                            should_switch += 1
                    else:
                        cnt_403_retry = 0
                    cnt_transfer_last = cnt_transfer

                # Rclone 直接提示错误403
                if switch_sa_rules.get('error_user_rate_limit', False):
                    switch_sa_level += 1

                    last_error = response_json.get('lastError', '')
                    # 考虑可能出现其他lastError覆盖ratelimitexceed，只要出现一次userratelimit就不再做检查
                    if cnt_get_rate_limit or last_error.find('userRateLimitExceeded') > -1:
                        cnt_get_rate_limit = True
                        should_switch += 1

                # 检查当前transferring的传输量
                if switch_sa_rules.get('all_transfers_in_zero', False):
                    switch_sa_level += 1

                    graceful = True
                    if response_json.get('transferring', False):
                        for transfer in response_json['transferring']:
                            # 处理`bytes`或者`speed`不存在的情况（认为该transfer已经完成了） @yezi1000
                            if 'bytes' not in transfer or 'speed' not in transfer:
                                continue
                            elif transfer.get('bytes', 0) != 0 and transfer.get('speed', 0) > 0:  # 当前还有未完成的传输
                                graceful = False
                                break
                    if graceful:
                        should_switch += 1

                # 大于设置的更换级别
                if should_switch >= switch_sa_level:
                    logger.info('Transfer Limit may hit, Kill exist rclone process %s' % proc.pid)
                    proc.kill()  # 杀掉当前rclone进程
                    break  # 退出主进程监测循环，从而切换到下一个帐号

                time.sleep(check_interval)
