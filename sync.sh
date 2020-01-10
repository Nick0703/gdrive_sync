#!/bin/bash

Reset_Color='\033[0m'
Red='\033[0;31m'
Green='\033[0;32m'
Blue='\033[0;34m'
Purple='\033[0;35m'
Cyan='\033[0;36m'

help()
{
   echo ""
   echo "Usage: $0 -s remoteA -d remoteB -a 1 -b 600 -p /home/user/service_accounts"
   echo -e "\t-s Name of the source remote"
   echo -e "\t-d Name of the destination remote"
   echo -e "\t-a First service account #, e.g 1 for sa_1 or 35 for sa_35"
   echo -e "\t-b Last service account #, e.g 90 for sa_90 or 600 for sa_600"
   echo -e "\t-p Path of the service accounts json files, absolute path without / at the end"
   echo -e "\t-v Enable rclone basic logging "$Green"(Optional)"$Reset_Color", /tmp/gdrive_sync.log"
   echo -e "\t-m Enable rclone detailed logging "$Green"(Optional)"$Reset_Color"/tmp_gdrive_sync.log"
   exit 1
}

opt_basicLog=0
opt_advLog=0

while getopts "s:d:a:b:p:vm" opt; do
   case "$opt" in
      s ) opt_source="$OPTARG" ;;
      d ) opt_destination="$OPTARG" ;;
      a ) opt_startSa="$OPTARG" ;;
      b ) opt_endSa="$OPTARG" ;;
      p ) opt_pathSa="$OPTARG" ;;
      v ) opt_basicLog=1 ;;
      m ) opt_advLog=1 ;;
      ? ) help ;;
   esac
done

# Check if the parameters are empty
if [ -z "$opt_source" ] || [ -z "$opt_destination" ] || \
		[ -z "$opt_startSa" ] || [ -z "$opt_endSa" ] || \
		[ -z "$opt_pathSa" ]
then
   echo -e $Red"Error: Some parameters are empty"$Reset_Color;
   help
fi

rclone_cmd="/usr/bin/rclone sync $opt_source: $opt_destination: \
--drive-server-side-across-configs -c \
--fast-list --no-update-modtime \
--tpslimit 6 --checkers 128 --max-transfer 750G --stats 5s \
--drive-service-account-file=$opt_pathSa/sa-$opt_startSa.json"
rclone_vLog=" -v --log-file=/tmp/gdrive_sync.log"
rclone_vvLog=" -vv --log-file=/tmp/gdrive_sync.log"

#Loop until the last service account
while [ $opt_startSa -lt $opt_endSa ]; do
	echo -e "Starting the Sync"
	echo "Using Service Account $opt_startSa"
	
	if [ "$opt_basicLog" -ne 0 ]; then # Basic Logging
		eval $rclone_cmd$rclone_vLog
	elif [ "$opt_advLog" -ne 0 ]; then # Detailed Logging
		eval $rclone_cmd$rclone_vvLog
	else # No logging
		eval $rclone_cmd
	fi
	
	let opt_startSa++

done
