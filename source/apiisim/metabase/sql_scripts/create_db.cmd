@echo off

REM Creates a new database and a new user, this user will be the owner of the database.
REM Once created, the database is initialized with the schema defined in set_schema.sql
REM and finally it is populated with some data.
if /%1/ EQU // (
echo "missing config file"
SET PROMPT=1
goto err
)

set configfile="%1"

if NOT EXIST %configfile% (
echo %1 not found
SET PROMPT=1
goto err
)

if /%configfile:~-5,4%/ NEQ /.cmd/ (
echo incorrect config file: %1
SET PROMPT=1
goto err
)

SET USER_PASS=
SET ADMIN_PASS=

call "%1"

if /%USER_PASS%/ EQU // (
    SET /p USER_PASS=Password for %USER_NAME%: 
    SET PROMPT=1
    echo.
)

if /%ADMIN_PASS%/ EQU // (
    SET /p ADMIN_PASS=Password for %ADMIN_NAME%: 
    SET PROMPT=1
    echo.
)

REM Check that admin password is OK
SET PGPASSWORD=%ADMIN_PASS%
psql -U %ADMIN_NAME% -h localhost -c "\q"
if %errorlevel% NEQ 0 goto err

REM Create user and database. then give all privileges on database to user.
psql -U %ADMIN_NAME% -h localhost -c "CREATE USER %USER_NAME% with encrypted password '%USER_PASS%';"
psql -U %ADMIN_NAME% -h localhost -c "CREATE DATABASE %DB_NAME% owner %USER_NAME%;"
if %errorlevel% NEQ 0 goto err
psql -U %ADMIN_NAME% -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %USER_NAME%;"
if %errorlevel% NEQ 0 goto err

REM Create PostGIS extension in order to have Geography type
REM PostGIS 2
psql -U %ADMIN_NAME% -h localhost -c "CREATE EXTENSION IF NOT EXISTS postgis;" %DB_NAME%
if %errorlevel% NEQ 0 goto err

REM Next, set the database schema and populate database with some data.
SET PGPASSWORD=%USER_PASS%
psql -w -U %USER_NAME% -h localhost -f "%~dp0set_schema.sql" %DB_NAME%
if /%POPULATE_DB%/ EQU /true/ (
if "%POPULATE_DB_SCRIPT%" NEQ "" (
REM If path is relative, use dirname.
REM If path is absolute, let it as is.
SET POPULATE_DB_SCRIPT="%~dp0%POPULATE_DB_SCRIPT%"
)
psql -w -U %USER_NAME% -h localhost -f %POPULATE_DB_SCRIPT% %DB_NAME%
)

color 0A
goto fin

:err
color 0C
goto fin

:fin
echo.
if /%PROMPT%/ EQU /1/ pause

