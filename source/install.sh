#!/bin/sh

LOG_DIR="/var/log/apiisim"
PREV_OPTION="PythonOption mod_pywebsocket.handler_root"
NEW_OPTION1="PythonOption PLANNER_DB_URL \"postgresql+psycopg2://postgres:postgres@localhost/afimb_navitia_db\""
NEW_OPTION2="PythonOption PLANNER_LOG_FILE \"$LOG_DIR/planner.log\""

# Install python module
python setup.py install &&

# Add apache module and set its configuration
cp -a apiisim/planner/planner_wsh.py /var/www/pywebsocket/handlers/planner_wsh.py &&
sed -i "/$PREV_OPTION/a$NEW_OPTION1" /etc/apache2/mods-enabled/python.conf &&
sed -i "/$PREV_OPTION/a$NEW_OPTION2" /etc/apache2/mods-enabled/python.conf &&

# Create directory to store logs
mkdir -p $LOG_DIR &&
chgrp www-data $LOG_DIR &&
chmod g+w $LOG_DIR &&

/etc/init.d/apache2 restart &&

echo "Installation successful"
