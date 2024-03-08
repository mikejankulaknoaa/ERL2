#! /usr/bin/bash

export DISPLAY=:0

# directory for startup logs
logdir=/opt/ERL2/log/startup

# directory with (optional) scripts to run before startup
scriptdir=/opt/ERL2/bin/startup

# make sure the startup log directory exists
if [ ! -d ${logdir} ]; then
    mkdir -p ${logdir}
fi

# if the startup directory exists
if [ -d ${scriptdir} ]; then

  # loop through all files in the startup directory
  while IFS='' read -r -d '' filename; do
    echo "found filename [${filename}]"

    # if a file is executable
    if [ -x "${filename}" ]; then
      # execute it!
      "${filename}"
    fi

  done < <(find ${scriptdir} -maxdepth 1 -type f -print0)

fi

# start the Erl2Startup.py module
/usr/bin/python3 /opt/ERL2/python/Erl2Startup.py > ${logdir}/$(/bin/date +%Y%m%d-%H%M%S-%3N).log 2>&1

