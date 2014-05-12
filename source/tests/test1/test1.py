"""
This test uses 3 components (metabase, back_office and mis_translator).
It creates a database, retrieve stops from 2 stub MISes and launch the
back_office several times, each time with a different maximum distance between
stops (to calculate transfers). For each different setting, we generate a dump
of the resulting database and compare it to a reference dump. If they don't match,
we exit the test and consider it as failed.
"""
import os, tempfile, subprocess, time

TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"
CREATE_DB_SCRIPT = TEST_DIR + "../../metabase/sql_scripts/create_db.sh"
MIS_TRANSLATOR = TEST_DIR + "../../mis_translator/__init__.py"
BACK_OFFICE = TEST_DIR + "../../back_office/__init__.py"

DB_NAME = "test1_db"
USER_NAME = "test1_user"
ADMIN_NAME = "postgres"

CREATE_DB_CONF = \
"DB_NAME=%s\n" \
"USER_NAME=%s\n" \
"ADMIN_NAME=%s\n" \
"POPULATE_DB=true\n" \
"POPULATE_DB_SCRIPT=%s\n"


def process_and_check(conf_file, ref_dump_file):
    subprocess.call(['python', BACK_OFFICE, "--config_file", conf_file])

    _, dump_file = tempfile.mkstemp(text=True, prefix="test1", suffix=".dump")
    subprocess.call(['pg_dump', '-U', ADMIN_NAME, '-h', 'localhost', '-f',
                     dump_file, DB_NAME])
    if subprocess.call(['diff', dump_file, ref_dump_file]) == 0:
        return True
    else:
        return False


# Create and populate db
fd, create_db_conf_file = tempfile.mkstemp(text=True, prefix="test1", suffix=".conf")
os.write(fd, CREATE_DB_CONF % (DB_NAME, USER_NAME, ADMIN_NAME,
                               TEST_DIR + "test1_populate_db.sql"))
os.close(fd)

ret = subprocess.call(['bash', CREATE_DB_SCRIPT, create_db_conf_file])
if ret != 0:
    raise Exception("%s failed: %s" % (CREATE_DB_SCRIPT, ret))

# Launch mis_translator
mis_translator_process = subprocess.Popen(['python', MIS_TRANSLATOR])
time.sleep(3)

try:
    # Launch back_office several times, with different settings.
    # Each time, generate a dump of the resulting database and compare it to a
    # reference dump. If they don't match, exit the test and consider it as failed.
    for conf_file, ref_dump_file in \
        [('test1_1.conf', 'db_dump1'), ('test1_2.conf', 'db_dump2'),
         ('test1_3.conf', 'db_dump3'), ('test1_4.conf', 'db_dump4')]:
        if not process_and_check(TEST_DIR + conf_file, TEST_DIR + ref_dump_file):
            print ("*** FAIL ***")
            raise Exception("Database dump different than expected dump (%s)" \
                             % ref_dump_file)
finally:
    # Cleanup
    mis_translator_process.terminate()
    mis_translator_process.wait()
    subprocess.call(['psql', '-U', ADMIN_NAME, '-h', 'localhost',
                      '-c', 'DROP DATABASE %s' % DB_NAME])
    subprocess.call(['psql', '-U', ADMIN_NAME, '-h', 'localhost',
                     '-c', 'DROP USER %s' % USER_NAME])

print ("*** SUCCESS ***")
