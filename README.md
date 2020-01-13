# Gdrive Sync

This script will use rclone to sync in-between two different Google Drives using service accounts.

# Requirements
1. Service Accounts json files should have the prefix **sa_** and a number as the suffix, like **sa_1.json**.
	- To rename all of them, I suggest make a copy of your service accounts folder first.
	- Run this command **ls | cat -n | while read n f; do mv "$f" "sa-$n.json"; done**
2. Both remote **source** and **destination** should be in your rclone config file.

## Usage

**sync.sh -s remoteA: -d remoteB: -a 1 -b 90 -p /home/user/sa/**

	-s Name of the source remote or specific folder
	   E.g remoteA: or remoteA:FolderB
	-d Name of the destination remote or specific folder
	   E.g remoteB: or remoteB:FolderA
	-a First service account # to use, e.g 1 for sa_1
	-b Last service account # to stop at, e.g 90 for sa_90
	-p Path of the service accounts json files (Absolute path)
    -v Enable rclone basic logging (Optional), /tmp/gdrive_sync.log
	-m Enable rclone detailed logging (Optional), /tmp_gdrive_sync.log
	   Please note that enabling this flag will create a large file.
