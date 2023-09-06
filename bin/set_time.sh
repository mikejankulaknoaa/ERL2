#!/bin/bash
STR=$(timedatectl status)
SUB="synchronized: yes"
case $STR in

  *"$SUB"*)
    msg="Network time present set the RTC..."
    string=$(date +%y%m%d%T)
    year=${string:0:2}
    month=${string:2:2}
    day=${string:4:2}
    hour=${string:6:2}
    min=${string:9:2}
    sec=${string:12:2}
    retval=$(/usr/local/bin/megaind 0 rtcwr $month $day $year $hour $min $sec)
    dt=$(/bin/date)
    echo "$dt:  $msg $retval"
    exit
    ;;

  *)
    msg="Network time not present use the RTC"
    t=$(/usr/local/bin/megaind 0 rtcrd)
    dt=$(sudo /bin/date --set "$t")
    echo "$dt:  $msg"
    exit
    ;;

esac
