# Gdrive Sync

This script will use rclone to sync in-between two different Google Drives using service accounts.

# Requirements
1. Service Accounts json files should have the prefix **sa_** and a number as the suffix, like **sa_1.json**.
	- To rename all of them, I suggest make a copy of your service accounts folder first.
	- Run this command **ls | cat -n | while read n f; do mv "$f" "sa-$n.json"; done**
2. Both remote **source** and **destination** should be in your rclone config file.
