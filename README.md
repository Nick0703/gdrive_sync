# Gdrive Sync

This script will use rclone to sync in-between two different Google Drives using service accounts.

# Requirements
1. Service Accounts json files should have the prefix **sa_** and a number as the suffix, like **sa_1.json**.
	- To rename all of them, I suggest make a copy of your service accounts folder first.
	- Run this command **ls | cat -n | while read n f; do mv "$f" "sa-$n.json"; done**
2. Both remote **source** and **destination** should be in your rclone config file.

## Usage

**sync.sh -s remoteA -d remoteB -a 1 -b 600 -p /home/user/service_accounts**

	-s Name of the source remote
	-d Name of the destination remote
	-a First service account #, e.g 1 for sa_1 or 35 for sa_35
	-b Last service account #, e.g 90 for sa_90 or 600 for sa_600
	-p Path of the service accounts json files, absolute path without / at the end
    -v Enable rclone basic logging (Optional), /tmp/gdrive_sync.log
	-m Enable rclone detailed logging (Optional), /tmp_gdrive_sync.log
