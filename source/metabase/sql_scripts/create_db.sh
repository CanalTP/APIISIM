#!/bin/sh

# Creates a new database and a new user, this user will be the owner of the database.
# Once created, the database is initialized with the schema defined in set_schema.sql
# and finally it is populated with some data.

DB_NAME="afimb_db" # New database to create
USER_NAME="afimb_user" # New user, will be the owner of the new database
ADMIN_NAME="postgres" # User with admin rights (required to create a new database)

# Create user and database. then give all privileges on database to user.
psql -U $ADMIN_NAME -h localhost -c "CREATE USER $USER_NAME with encrypted password '$USER_NAME';" &&
psql -U $ADMIN_NAME -h localhost -c "CREATE DATABASE $DB_NAME owner $USER_NAME;" &&
psql -U $ADMIN_NAME -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $USER_NAME;" &&

# Create PostGIS extension in order to have Geography type
# PostGIS 2
# psql -U $ADMIN_NAME -h localhost -c "CREATE EXTENSION IF NOT EXISTS postgis;" $DB_NAME &&

# PostGIS 1.5
psql -U $ADMIN_NAME -d $DB_NAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql &&
psql -U $ADMIN_NAME -d $DB_NAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql &&
psql -U $ADMIN_NAME -d $DB_NAME -c "select postgis_lib_version();" &&
psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON geometry_columns TO PUBLIC;" &&
psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;" &&
psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON geography_columns TO PUBLIC;" &&

# Next, set the database schema and populate database with some data.
echo "Password for <$USER_NAME> is <$USER_NAME>"
psql -U $USER_NAME -h localhost -f ./set_schema.sql $DB_NAME &&
psql -U $USER_NAME -h localhost -f ./populate_db.sql $DB_NAME
