@echo off
echo.

echo Setting up python path 
SET SPDIR=C:\Python27\Lib\site-packages\
IF NOT EXIST %SPDIR% goto err
echo %~dp0source > %SPDIR%apiisim.pth

color 0A
echo SUCCESS.
goto fin

:err
color 0C
echo ! Failure, unknown path: %SPDIR%
goto fin

:fin
echo.
pause

