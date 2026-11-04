#!/bin/sh
# Report the size of an ISO output folder and its archive, and warn when the
# archive grows past ARCHIVE_WARN_GB or free space drops under FREE_WARN_GB.
# Never deletes anything. Usage: out-report.sh [dir] (default: ./out)
DIR="${1:-out}"; AW="${ARCHIVE_WARN_GB:-20}"; FW="${FREE_WARN_GB:-15}"
[ -d "$DIR" ] || exit 0
gb() { du -sk "$1" 2>/dev/null | awk '{printf "%.1f", $1 / 1048576}'; }
n() { find "$1" -name '*.iso' 2>/dev/null | wc -l; }
FREE=$(df -Pk "$DIR" | awk 'NR == 2 {printf "%.1f", $4 / 1048576}')
A=0; [ -d "$DIR/archive" ] && A=$(gb "$DIR/archive")
echo "out report ($DIR): $(n "$DIR") ISOs, $(gb "$DIR") GB total; archive: $( [ -d "$DIR/archive" ] && n "$DIR/archive" || echo 0) ISOs, $A GB; free: $FREE GB"
awk -v a="$A" -v w="$AW" 'BEGIN {exit !(a > w)}' && echo "WARNING: $DIR/archive is $A GB (over ${AW} GB). Review and remove old ISOs there by hand."
awk -v f="$FREE" -v w="$FW" 'BEGIN {exit !(f < w)}' && echo "WARNING: only $FREE GB free on the disk holding $DIR (under ${FW} GB)."
exit 0
