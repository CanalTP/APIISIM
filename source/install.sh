#!/bin/sh

PREV_OPTION="PythonOption mod_pywebsocket.handler_root"
NEW_OPTION="PythonOption PLANNER_DB_URL \"postgresql+psycopg2://postgres:postgres@localhost/afimb_navitia_db\""

python setup.py install &&
cp -a apiisim/planner/planner_wsh.py /var/www/pywebsocket/handlers/planner_wsh.py &&
sed -i "/$PREV_OPTION/a$NEW_OPTION" /etc/apache2/mods-enabled/python.conf &&
/etc/init.d/apache2 restart &&

echo "Installation successful"
