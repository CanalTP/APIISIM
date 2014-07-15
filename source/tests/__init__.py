import random, os, tempfile, subprocess
import unittest, time
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import logging, sys, argparse, ConfigParser

CREATE_DB_SCRIPT = os.path.dirname(os.path.realpath(__file__)) + "/../metabase/sql_scripts/create_db.sh"
MIS_TRANSLATOR = os.path.dirname(os.path.realpath(__file__)) + "/../mis_translator/run.py"
BACK_OFFICE = os.path.dirname(os.path.realpath(__file__)) + "/../back_office/__init__.py"

DB_NAME = "test_db"
USER_NAME = "test_user"
ADMIN_NAME = "postgres"
USER_PASS = "test_user"
ADMIN_PASS = "postgres"

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
    fd, create_db_conf_file = tempfile.mkstemp(text=True, prefix="test", suffix=".conf")
    if populate_script:
        populate = "true"
    else:
        populate = "false"
    os.write(fd, CREATE_DB_CONF % (db_name, user_name, admin_name, user_pass, admin_pass,
                                   populate, populate_script))
    os.close(fd)

    ret = subprocess.call(['bash', CREATE_DB_SCRIPT, create_db_conf_file])
    if ret != 0:
        raise Exception("%s failed: %s" % (CREATE_DB_SCRIPT, ret))


"""
Delete given database and user. No connection to the database must be
active (use disconnect_db() if needed before calling drop_db()).
"""
def drop_db(db_name=DB_NAME, user_name=USER_NAME, admin_name=ADMIN_NAME):
        subprocess.call(['psql', '-U', admin_name, '-h', 'localhost',
                         '-c', 'DROP DATABASE %s' % db_name])
        subprocess.call(['psql', '-U', admin_name, '-h', 'localhost',
                         '-c', 'DROP USER %s' % user_name])


def connect_db(db_name=DB_NAME, user_name=ADMIN_NAME, user_password=ADMIN_PASS):
    db_engine = create_engine("postgresql+psycopg2://%s:%s@localhost/%s" \
                              % (user_name, user_password, db_name), echo=False)
    return Session(bind=db_engine, expire_on_commit=False)


def disconnect_db(db_session):
    db_session.close()
    db_session.bind.dispose()


def launch_mis_translator():
    process = subprocess.Popen(['python', MIS_TRANSLATOR])
    time.sleep(3)
    return process

# !!! IMPORTANT !!!
# This doesn't work if mis_translator is launched in debug mode as Flask
# forks when running in debug mode.
def terminate_mis_translator(process):
    process.terminate()
    process.wait()


def launch_back_office(conf_file):
    return subprocess.call(['python', BACK_OFFICE, "--config_file", conf_file])

"""
Launch back_office with given configuration and compare resulting database to given
reference dump file. If database matches, return True, if it doesn't match, return False.
"""
def calculate_and_check(conf_file, ref_dump_file, db_name=DB_NAME, admin_name=ADMIN_NAME):
    launch_back_office(conf_file)

    _, dump_file = tempfile.mkstemp(text=True, prefix="test1", suffix=".dump")
    subprocess.call(['pg_dump', '-U', admin_name, '-h', 'localhost', '-f',
                     dump_file, db_name])
    if subprocess.call(['diff', dump_file, ref_dump_file]) == 0:
        return True
    else:
        return False


# TODO add possibility to read logging config from a file/variable
handler = logging.StreamHandler(stream=sys.stdout)
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(handler)
