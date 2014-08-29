#!/bin/sh

LOG_DIR="/var/log/apiisim"
PREV_OPTION="PythonOption mod_pywebsocket.handler_root"
DB_URL_OPTION="PythonOption PLANNER_DB_URL \"postgresql+psycopg2://postgres:postgres@localhost/afimb_navitia_db\""
LOG_FILE_OPTION="PythonOption PLANNER_LOG_FILE \"$LOG_DIR/planner.log\""
MOD_PYTHON_CONF_FILE="/etc/apache2/mods-enabled/python.conf"

# Install python module
python setup.py install &&

# Add apache module and set its configuration
cp -a apiisim/planner/planner_wsh.py /var/www/pywebsocket/handlers/planner_wsh.py &&
grep PLANNER_DB_URL $MOD_PYTHON_CONF_FILE > /dev/null
if [ $? -ne 0 ]; then
    sed -i "/$PREV_OPTION/a$DB_URL_OPTION" $MOD_PYTHON_CONF_FILE || exit 1
fi

grep PLANNER_LOG_FILE $MOD_PYTHON_CONF_FILE > /dev/null
if [ $? -ne 0 ]; then
    sed -i "/$PREV_OPTION/a$LOG_FILE_OPTION" $MOD_PYTHON_CONF_FILE || exit 1
fi

# Create directory to store logs
mkdir -p $LOG_DIR &&
chgrp www-data $LOG_DIR &&
chmod g+w $LOG_DIR &&

/etc/init.d/apache2 restart &&

echo "Installation successful"
