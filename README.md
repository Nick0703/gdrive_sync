# Autorclone 

A python script lists Which Use Service Account to bypass the 750G upload file size limit on Google Drive
based on [folderclone](https://github.com/Spazzlo/folderclone)

Different from The exist project, This repo use [Rclone](https://rclone.org) to **transfer files from local disk 
to Google Drive or Team Drive**.

## Requirements for using the scripts

* Python ^3.4 **(Use 64-Bit Python only)**
* Python Library which list in `requirements.txt`
* Rclone ^1.41 (To support `service_account_credentials` feature )

## Setup

> Chinese Version: [使用Service Account突破rclone单账号GD每日750G上传限制](//blog.rhilip.info/archives/1135/)

1. setup `multifactory.py`
    1) Head over to <https://console.developers.google.com/> and sign in with your account.
    2) Click "Library" on the left column, then click on "Select a project" at the top. Click on `NEW PROJECT` on the top-right corner of the new window.
    3) In the Project name section, input a project name of your choice. Wait till the project creation is done and then click on "Select a project" again at the top and select your project.
    4) Select "OAuth consent screen" and fill out the **Application name** field with a name of your choice. Scroll down and hit "Save"
    5) Select "Credentials"  and select Create credentials. Choose "OAuth client ID". Choose "Other" as your **Application type** and hit "Create". Hit "Ok". You will now be presented with a list of "OAuth 2.0 client IDs". At the right end, there will be a download icon. Select it to download and save it as `credentials.json` in the script folder.
    6) Find out how many projects you'll need. For example, a 100 TB job will take approximately 135 service accounts to make a full clone. Each project can have a maximum of 100 service accounts. In the case of the 100TB job, we will need 2 projects. `multifactory.py` conveniently includes a quick setup option. Run the following command `python3 multifactory.py --quick-setup N`. **Replace `N` with the amount of projects you need!**. If you want to only use new projects instead of existing ones, make sure to add `--new-only` flag. It will automatically start doing all the hard work for you.
    6a) Running this for the first time will prompt you to login with your Google account. Login with the same account you used for Step 1. If will then ask you to enable a service. Open the URL in your browser to enable it. Press Enter once it's enabled.

2. Steps to add all the service accounts to the Shared Drive
    1) Once `multifactory.py` is done making all the accounts, open Google Drive and make a new Shared Drive to copy to.
    2) Run the following command `python3 masshare.py -d SDFolderID`. Replace the `SDFolderID` with `XXXXXXXXXXXXXXXXXXX`. The Folder ID can be obtained from the Shared Drive URL `https://drive.google.com/drive/folders/XXXXXXXXXXXXXXXXXXX`. `masshare.py` will start adding all your service accounts.

3. Steps for `autorclone.py`
    1) Change script config at the beginning of file.
    2) Run it manually in `screen` or Add to crontab like `0 */1 * * * /usr/bin/python3 /path/to/autorclone.py`
