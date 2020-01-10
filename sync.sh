#!/bin/bash

help()
{
   echo ""
   echo "Usage: $0 -s remoteA -d remoteB -a 1 -b 600"
   echo -e "\t-s Name of the source remote"
   echo -e "\t-d Name of the destination remote"
   echo -e "\t-a First service account #, e.g 1 for sa_1 or 35 for sa_35"
   echo -e "\t-b Last service account #, e.g 90 for sa_90 or 600 for sa_600"
   echo -e "\t-p Path of the service accounts json files, absolute path without / at the end"
   echo -e "\t-v Enable rclone basic logging (Optional), /tmp/gdrive_sync.log"
   echo -e "\t-m Enable rclone detailed logging (Optional), /tmp_gdrive_sync.log"
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
   echo "Parameters are empty";
   help
fi

#Loop until the last service account
while [ $opt_startSa -lt $opt_endSa ]; do
	echo "Using Service Account $opt_startSa"
	
	if [ "$opt_basicLog" -ne 0 ]; then # Basic Logging
		/usr/bin/rclone sync $opt_source: $opt_destination: \
		--drive-server-side-across-configs -c \
		--fast-list --no-update-modtime --max-backlog 220000 \
		--tpslimit 6 --checkers 128 --max-transfer 750G --stats 5s \
		--drive-service-account-file=$opt_pathSa/sa-$opt_startSa.json \
		-v --log-file=/tmp/gdrive_sync.log
	elif [ "$opt_advLog" -ne 0 ]; then # Detailed Logging
		/usr/bin/rclone sync $opt_source: $opt_destination: \
		--drive-server-side-across-configs -c \
		--fast-list --no-update-modtime --max-backlog 220000 \
		--tpslimit 6 --checkers 128 --max-transfer 750G --stats 5s \
		--drive-service-account-file=$opt_pathSa/sa-$opt_startSa.json \
		-vv --log-file=/tmp/gdrive_sync.log
	else # No logging
		/usr/bin/rclone sync $opt_source: $opt_destination: \
		--drive-server-side-across-configs -c \
		--fast-list --no-update-modtime --max-backlog 220000 \
		--tpslimit 6 --checkers 128 --max-transfer 750G --stats 5s \
		--drive-service-account-file=$opt_pathSa/sa-$opt_startSa.json
	fi
	
	let opt_startSa++

done
