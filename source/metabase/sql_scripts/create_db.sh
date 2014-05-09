#!/bin/bash

# Creates a new database and a new user, this user will be the owner of the database.
# Once created, the database is initialized with the schema defined in set_schema.sql
# and finally it is populated with some data.

source $(dirname $0)/create_db.config

read -s -p "Password for $USER_NAME: " USER_PASS
echo

read -s -p "Password for $ADMIN_NAME: " ADMIN_PASS
echo $ADMIN_PASS

# Check that admin password is OK
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -h localhost -c '\q'
if [ $? != 0 ]; then
    exit 1
fi

# Create user and database. then give all privileges on database to user.
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -h localhost -c "CREATE USER $USER_NAME with encrypted password '$USER_PASS';" &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -h localhost -c "CREATE DATABASE $DB_NAME owner $USER_NAME;" &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $USER_NAME;" &&

# Create PostGIS extension in order to have Geography type
# PostGIS 2
# psql -U $ADMIN_NAME -h localhost -c "CREATE EXTENSION IF NOT EXISTS postgis;" $DB_NAME &&

# PostGIS 1.5
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -c "select postgis_lib_version();" &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON geometry_columns TO PUBLIC;" &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;" &&
PGPASSWORD=$ADMIN_PASS psql -U $ADMIN_NAME -d $DB_NAME -c "GRANT ALL ON geography_columns TO PUBLIC;" &&

# Next, set the database schema and populate database with some data.
PGPASSWORD=$USER_PASS psql -w -U $USER_NAME -h localhost -f $(dirname $0)/set_schema.sql $DB_NAME &&
PGPASSWORD=$USER_PASS psql -w -U $USER_NAME -h localhost -f $(dirname $0)/populate_db.sql $DB_NAME
