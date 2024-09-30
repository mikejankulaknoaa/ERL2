@echo off
setlocal

set erl2dir=C:\Users\erl2\OneDrive - University of Miami\Documents\ERL2\

:: Set the current date and time in YYYYMMDD-HHMMSS-ss format
set timestamp=%date:~-4%%date:~4,2%%date:~7,2%-%time:~0,2%%time:~3,2%%time:~6,2%-%time:~9,2%

:: echo timestamp is: %timestamp%

:: seems to be replacing spaces with zeroes
set timestamp=%timestamp: =0%

:: echo timestamp is: %timestamp%

:: Get the main ERL2 path
::set pwd="%cd%"
::for %%F in (%pwd%) do set erl2dir=%%~dpF

:: echo erl2dir is: %erl2dir%

:: Make sure log directory exists
set logdir=%erl2dir%log\
if not exist "%logdir%" mkdir "%logdir%"
set logdir=%logdir%startup\
if not exist "%logdir%" mkdir "%logdir%"

:: echo logdir is: %logdir%

:: Set the log file path and name
set logfile=%logdir%%timestamp%.log

:: echo logfile is: %logfile%

:: Python and the startup module
set python=C:\Users\erl2\AppData\Local\Microsoft\WindowsApps\python.exe
set erl2startup=%erl2dir%python\Erl2Startup.py

:: echo python is: python%
:: echo erl2startup is: %erl2startup%

:: Start up ERL2! Redirect output to a timestamped logfile

"%python%" "%erl2startup%" > "%logfile%" 2>&1



