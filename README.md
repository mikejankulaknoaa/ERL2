# ERL2

README.md last updated 6/16/2023 mjankulak

Welcome to the ERL2 Project!

This code was developed on the Raspberry Pi 4 platform.

For development and testing purposes the ERL2 repository was
cloned to /opt/ERL2 on the Pi, and owned by an 'erl2' local
account, but it can be cloned to any location and owned by
any user and it will adapt to circumstance.

The most important step before beginning is to create your
own erl2.conf configuration file. You should copy the sample
file from the cfg directory, rename it, and edit it to specify
whatever parameters are appropriate to this specific ERL2 Tank.

This may look something like this:

cd /opt/ERL2 # or wherever you have cloned this repository

cp cfg/erl2.conf.sample erl2.conf

vi erl2.conf # or nano or whatever Pi editor you prefer

Note that the erl2.conf file itself is not contained within
the github repository, so as to avoid overwriting local
customizations with defaults when updating your local files
with updates from the repository. It maybe be helpful to
inspect cfg/erl2.conf.sample from time to time to see what
new/default paramters have been added.

You can delete or comment-out parameters in erl2.conf and the
system will revert to its internally-defined default values
for those parameters.
