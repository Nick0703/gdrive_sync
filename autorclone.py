import os
import json
import time
import glob
import logging
import subprocess

import filelock

# ------------配置项开始------------------

# Account目录
sa_json_folder = r'/home/folderrclone/accounts'  # 最后没有 '/'

# Rclone移动的源和目的地
rclone_src = '/home/tomove'
rclone_des = 'GDrive:/tmp'

# 日志文件
rclone_log_file = r'/tmp/rclone.log'  # Rclone日志输出
script_log_file = r'/tmp/autorclone.log'  # 本脚本运行日志

# 本脚本临时文件
instance_lock_path = r'/tmp/autorclone.lock'
instance_config_path = r'/tmp/autorclone.conf'

# 检查rclone间隔 (s)
check_interval = 10

# 更换rclone帐号严格度 (1-3) 数字越大，监测越严格，建议为 2
switch_sa_level = 2

# Rclone运行命令
cmd_rclone = [
    # Rclone基本命令
    'rclone', 'move', rclone_src, rclone_des,
    # 基本配置项（不要改动）
    '--drive-server-side-across-configs',  # 优先使用Server Side
    '-rc',  # 启用rc模式，此项不可以删除，否则无法正确切换
    '-v', '--log-file', rclone_log_file,
    # 其他配置项，默认不启用，为rclone默认参数，请根据自己需要更改
    # '--ignore-existing',
    # '--fast-list',
    # '--tpslimit 6',
    # '--transfers 12',
    # '--drive-chunk-size 32M',
    # '--drive-acknowledge-abuse',
]

# ------------配置项结束------------------

instance_config = {}
sa_jsons = []


def write_config(name, value):
    instance_config[name] = value
    with open(instance_config_path, 'w') as f:
        json.dump(instance_config, f, sort_keys=True)


# 获得下一个Service Account Credentials JSON file path
def get_next_sa_json_path(_last_sa):
    if _last_sa not in sa_jsons:
        next_sa_index = 0
    else:
        _last_sa_index = sa_jsons.index(_last_sa)
        next_sa_index = _last_sa_index + 1

    # 超过列表长度从头开始取
    if next_sa_index > len(sa_jsons):
        next_sa_index = next_sa_index - len(sa_jsons)
    return sa_jsons[next_sa_index]


if __name__ == '__main__':
    # 单例模式 (￣y▽,￣)╭
    instance_check = filelock.FileLock(instance_lock_path)
    with instance_check.acquire(timeout=0):
        # 加载account信息
        sa_jsons = glob.glob(os.path.join(sa_json_folder, '*.json'))
        if len(sa_jsons) == 0:
            raise RuntimeError('No Service Account Credentials JSON file exists')

        # 加载instance配置
        if os.path.exists(instance_config_path):
            config_raw = open(instance_config_path).read()
            instance_config = json.loads(config_raw)

        if switch_sa_level > 2 or switch_sa_level < 0:
            switch_sa_level = 2

        # 如果有的话，重排sa_jsons
        last_sa = instance_config.get('last_sa', '')
        if last_sa in sa_jsons:
            last_sa_index = sa_jsons.index(last_sa)
            sa_jsons = sa_jsons[last_sa_index:] + sa_jsons[:last_sa_index]

        # 帐号切换循环
        while True:
            current_sa = get_next_sa_json_path(last_sa)
            write_config('last_sa', current_sa)

            # 起一个subprocess调rclone，并附加'--drive-service-account-file'参数
            cmd_rclone_current_sa = cmd_rclone + ['--drive-service-account-file', current_sa]
            p = subprocess.Popen(cmd_rclone_current_sa, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 主进程使用 `rclone rc core/stats` 检查子进程情况
            cnt_error = 0
            cnt_403_retry = 0
            cnt_transfer_last = 0
            cmd_stats = 'rclone rc core/stats'
            while True:
                try:
                    response = subprocess.check_output(cmd_stats, shell=True)
                except subprocess.CalledProcessError as error:
                    cnt_error = cnt_error + 1
                    if cnt_error >= 3:
                        p.kill()
                        raise RuntimeError('Rclone may finish all work and exit, for 3 times check core/stats failed.')
                    continue
                else:
                    cnt_error = 0

                response_processed = response.decode('utf-8').replace('\0', '')
                response_processed_json = json.loads(response_processed)

                should_switch = 0

                # 比较两次检查期间rclone传输的量
                cnt_transfer = response_processed_json['bytes']
                if cnt_transfer - cnt_transfer_last == 0:  # 未增加
                    cnt_403_retry += 1
                    if cnt_403_retry > 200:  # 超过200次检查均未增加
                        should_switch += 1
                else:
                    cnt_403_retry = 0
                cnt_transfer_last = cnt_transfer

                # 检查当前transferring的传输量
                graceful = True
                for transfer in response_processed_json['transferring']:
                    if transfer['bytes'] != 0 and transfer['speed'] > 0:  # 当前还有未完成的传输
                        graceful = False
                        break
                if graceful:
                    should_switch += 1

                # 大于设置的更换级别
                if should_switch >= switch_sa_level:
                    p.kill()  # 杀掉当前rclone进程
                    break  # 退出主进程监测循环，切换到下一个帐号

                time.sleep(check_interval)
