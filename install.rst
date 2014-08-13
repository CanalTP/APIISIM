*********************************************
How to build APIISIM components and run them
*********************************************

Dependencies
============

#. Python

   * psycopg2
   * sqlalchemy
   * flask
   * geoalchemy2
   * python-mod-pywebsocket
   * flask-restful (https://github.com/l-vincent-l/flask-restful) **patched version**
   * websocket-client (only needed by test client)
   * jsonschema (only needed by planner_client example)

#. Other

   * apache2
   * postgresql (9.1+)
   * postgis (1.5+)

You can use the given *install_deps.sh* script that will install all required
dependencies (tested on Debian 7 only).

Build & Install
===============

#. Get the source from git

   ``git clone https://github.com/CanalTP/APIISIM/ -b dev /tmp/apiisim``

#. Build and install the package

   ``cd /tmp/apiisim/source``

   ``./install.sh``

Launching components
==================

In this example, we'll setup APIISIM components using the default configuration,
which only uses Navitia MISes. To customize the setup to your liking, you can
edit the following configuration files:

   * apiisim/metabase/sql_scripts/navitia.conf
   * apiisim/metabase/sql_scripts/populate_db_mis_only_navitia.sql
   * apiisim/back_office/navitia.conf
   * /etc/apache2/mods-enabled/python.conf

You may certainly have to change Postgresql username and password in those files 
to match your setup.


#. Creating the metabase

   The first step is to create the database that will store data shared by all components.
   In this step, we'll also populate the database with every MIS that will be used
   to calculate itineraries.
   To do so, we execute the provided *create_db.sh* script. Here, we only use
   Navitia MISes, to add other MIS APIs, just edit the SQL script that populates
   the database (*apiisim/metabase/sql_scripts/populate_db_mis_only_navitia.sql*).

   ``cd apiisim/metabase/sql_scripts/``

   ``./create_db.sh navitia.conf``

#. Launch mis_translator

   The mis_translator is a Web service that acts as an abstraction layer for
   both the back_office and the planner to allow them to communicate with different MISes
   via a unique API. Therefore, it must always be up and running so that the
   back office and the planner can work properly.

   ``cd /usr/local/lib/python2.7/dist-packages/apiisim-0.1-py2.7.egg/apiisim/mis_translator/``

   ``nohup python run.py &``

#. Launch back_office

   It will retrieve stops from all MISes configured in the database,
   calculate transfers between those stops and deduce connections between
   MISes. This will provide to APIISIM components what is needed to compute
   trips.

   ``cd /usr/local/lib/python2.7/dist-packages/apiisim-0.1-py2.7.egg/apiisim/back_office/``

   ``python run.py --config navitia.conf``

   The back_office does some pretty heavy calculations so this step can last more
   than 10 minutes.

#. Launch the planner web socket service

   This is the most important component, the one that actually calculates "meta-trips".
   As it is an Apache module, not a standalone program, it should already be running
   but in doubt, you can restart Apache.

   ``/etc/init.d/apache2 restart``

#. Check with planner_client

   Run planner_client example to check that all components are up and working properly.

   ``cd /tmp/apiisim/source/apiisim/tests/planner_client/``

   ``python planner_client.py``
