#!/bin/sh

APT_OPTIONS="-y"

# Postgresql 9.3 and PostGIS 2.1
touch /etc/apt/sources.list.d/pgdg.list &&
echo "deb http://apt.postgresql.org/pub/repos/apt/ wheezy-pgdg main" >> /etc/apt/sources.list.d/pgdg.list &&
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - &&
apt-get $APT_OPTIONS update &&
# apt-get $APT_OPTIONS upgrade &&
apt-get $APT_OPTIONS install postgresql-9.3 pgadmin3 &&
apt-get $APT_OPTIONS install postgresql-9.3-postgis postgresql-contrib &&

# Python libraries
apt-get $APT_OPTIONS install python-psycopg2 &&
apt-get $APT_OPTIONS install python-sqlalchemy &&
apt-get $APT_OPTIONS install python-flask &&
apt-get $APT_OPTIONS install python-pip &&
pip install geoalchemy2 &&
pip install websocket-client &&
pip install jsonschema &&

# Install custom flask-restful
apt-get $APT_OPTIONS install git &&
git clone https://github.com/l-vincent-l/flask-restful /tmp/flask-restful &&
cd /tmp/flask-restful &&
python setup.py install &&
cd - &&

apt-get $APT_OPTIONS install apache2 &&
apt-get $APT_OPTIONS install python-mod-pywebsocket &&

touch /etc/apache2/mods-enabled/python.conf &&
echo "<IfModule python_module>
    PythonPath \"sys.path\"
    PythonOption mod_pywebsocket.handler_root /var/www/pywebsocket/handlers
    PythonHeaderParserHandler mod_pywebsocket.headerparserhandler
</IfModule>" >> /etc/apache2/mods-enabled/python.conf &&

mkdir -p /var/www/pywebsocket/handlers
