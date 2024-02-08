#! /usr/bin/bash

export DISPLAY=:0

logdir=/opt/ERL2/log/startup

# make sure the startup log directory exists
if [ ! -d ${logdir} ]; then
    mkdir -p ${logdir}
fi

# start the Erl2Tank.py module
/usr/bin/python3 /opt/ERL2/python/Erl2Tank.py > ${logdir}/$(/bin/date +%Y%m%d-%H%M%S-%3N).log 2>&1
