REM New database to create
SET DB_NAME="afimb_navitia_db"
REM New user, will be the owner of the new database
SET USER_NAME="afimb_navitia_user"
REM User with admin rights (required to create a new database)
SET ADMIN_NAME="postgres"
REM If true, database will be populated with some example data. Otherwise, database will be left empty.
SET POPULATE_DB=true
REM Script that will be executed to populate database (if POPULATE_DB is true)
SET POPULATE_DB_SCRIPT=populate_db_mis_only_navitia.sql
