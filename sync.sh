#!/bin/bash
start="$(date -u +%s)"
Reset_Color='\033[0m'
Red='\033[0;31m'
Green='\033[0;32m'

help()
{
   echo ""
   echo "Usage: $0 -s remoteA: -d remoteB: -a 1 -b 90 -p /home/user/sa/"
   echo -e "\t-s Name of the source remote or specific folder"
   echo -e "\t   E.g remoteA: or remoteA:FolderB"
   echo -e "\t-d Name of the destination remote or specific folder"
   echo -e "\t   E.g remoteB: or remoteB:FolderA"
   echo -e "\t-a First service account # to use, e.g 1 for sa_1"
   echo -e "\t-b Last service account # to stop at, e.g 90 for sa_90"
   echo -e "\t-p Path of the service accounts json files"$Red" (Absolute path)"$Reset_Color
   echo -e "\t-v Enable rclone basic logging "$Green"(Optional)"$Reset_Color", /tmp/gdrive_sync.log"
   echo -e "\t-m Enable rclone detailed logging "$Green"(Optional)"$Reset_Color"/tmp_gdrive_sync.log"
   echo -e "\t   Please note that enabling this flag will create a large file."
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

rclone_cmd="/usr/bin/rclone sync $opt_source $opt_destination \
--drive-server-side-across-configs -c \
--fast-list --no-update-modtime --max-backlog 220000 \
--tpslimit 3 --checkers 3 --max-transfer 735G --stats 5s \
--drive-service-account-file=$opt_pathSa""sa-$opt_startSa.json"
rclone_vLog=" -v --log-file=/tmp/gdrive_sync.log"
rclone_vvLog=" -vv --log-file=/tmp/gdrive_sync.log"

#Loop until the last service account
echo -e $Green"Starting the Sync"$Reset_Color
if [ "$opt_basicLog" -ne 0 ] || [ "$opt_advLog" -ne 0 ]; then
	echo "Logging enabled, file in /tmp/gdrive_sync.log"
	echo ""
fi

while [ $opt_startSa -lt $opt_endSa ]; do
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
end="$(date -u +%s)"
tmin=$(( (end-start)/60 ))
tsec=$(( (end-start)%60 ))
echo -e $Green"Total elapse time: $tmin minutes $tsec seconds"
