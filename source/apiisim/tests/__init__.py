import os
import tempfile
import subprocess
from datetime import datetime
import logging
import sys
import platform

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apiisim import metabase


if platform.system() == "Windows":
    CREATE_DB_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "metabase", "sql_scripts",
                                    "create_db.cmd")
else:
    CREATE_DB_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "metabase", "sql_scripts",
                                    "create_db.sh")

MIS_TRANSLATOR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "mis_translator", "run.py")
BACK_OFFICE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "back_office", "run.py")

DB_NAME = "test_db"
USER_NAME = "test_user"
ADMIN_NAME = "postgres"
USER_PASS = "test_user"
ADMIN_PASS = "postgres"

if platform.system() == "Windows":
    CREATE_DB_CONF = \
        "SET DB_NAME=%s\n" \
        "SET USER_NAME=%s\n" \
        "SET ADMIN_NAME=%s\n" \
        "SET USER_PASS=%s\n" \
        "SET ADMIN_PASS=%s\n" \
        "SET POPULATE_DB=%s\n" \
        "SET POPULATE_DB_SCRIPT=%s\n"
else:
    CREATE_DB_CONF = \
        "DB_NAME=%s\n" \
        "USER_NAME=%s\n" \
        "ADMIN_NAME=%s\n" \
        "USER_PASS=%s\n" \
        "ADMIN_PASS=%s\n" \
        "POPULATE_DB=%s\n" \
        "POPULATE_DB_SCRIPT=%s\n"

"""
Create db with its associated owner and populate it (if a populate_script is given).
"""


def create_db(db_name=DB_NAME, user_name=USER_NAME, admin_name=ADMIN_NAME,
              user_pass=USER_PASS, admin_pass=ADMIN_PASS, populate_script=""):
    if platform.system() == "Windows":
        fd, create_db_conf_file = tempfile.mkstemp(text=True, prefix="test", suffix=".conf.cmd")
    else:
        fd, create_db_conf_file = tempfile.mkstemp(text=True, prefix="test", suffix=".conf")
    if populate_script:
        populate = "true"
    else:
        populate = "false"
    os.write(fd, CREATE_DB_CONF % (db_name, user_name, admin_name, user_pass, admin_pass,
                                   populate, populate_script))
    os.close(fd)

    if platform.system() == "Windows":
        ret = subprocess.call([CREATE_DB_SCRIPT, create_db_conf_file])
    else:
        ret = subprocess.call(['bash', CREATE_DB_SCRIPT, create_db_conf_file])
    if ret != 0:
        raise Exception("%s failed: %s" % (CREATE_DB_SCRIPT, ret))


"""
Delete given database and user. No connection to the database must be
active (use disconnect_db() if needed before calling drop_db()).
"""


def drop_db(db_name=DB_NAME, user_name=USER_NAME, admin_name=ADMIN_NAME,
            admin_password=ADMIN_PASS):
    os.environ["PGPASSWORD"] = admin_password
    subprocess.call(['psql', '-U', admin_name, '-h', 'localhost',
                     '-c', 'DROP DATABASE IF EXISTS %s' % db_name])
    subprocess.call(['psql', '-U', admin_name, '-h', 'localhost',
                     '-c', 'DROP USER IF EXISTS %s' % user_name])


def connect_db(db_name=DB_NAME, user_name=ADMIN_NAME, user_password=ADMIN_PASS):
    db_engine = create_engine("postgresql+psycopg2://%s:%s@localhost/%s"
                              % (user_name, user_password, db_name), echo=False)
    return Session(bind=db_engine, expire_on_commit=False)


def disconnect_db(db_session):
    db_session.close()
    db_session.bind.dispose()


"""
    Set all creation/update dates of rows to minimal datetime.
    Also set start/end dates in back_office_import table to minimal datetime.
"""


def reset_dates(db_name=DB_NAME, user_name=ADMIN_NAME, user_password=ADMIN_PASS):
    db_session = connect_db(db_name, user_name, user_password)
    tables = [metabase.Mis, metabase.Stop, metabase.Transfer, metabase.Mode]
    for table in tables:
        conn = db_session.connection()
        conn.execute("ALTER TABLE %s DISABLE TRIGGER ALL;" % table.__tablename__)
        for row in db_session.query(table).all():
            row.created_at = datetime.min
            row.updated_at = datetime.min
        db_session.commit()

    for table in tables:
        conn = db_session.connection()
        conn.execute("ALTER TABLE %s ENABLE TRIGGER ALL;" % table.__tablename__)
        db_session.commit()

    for row in db_session.query(metabase.BackOfficeImport).all():
        row.start_date = datetime.min
        row.end_date = datetime.min
        db_session.commit()

    disconnect_db(db_session)

# TODO add possibility to read logging config from a file/variable
handler = logging.StreamHandler(stream=sys.stdout)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(handler)
