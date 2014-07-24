"""
This test uses 3 components (metabase, back_office and mis_translator).
It creates a database, retrieve stops from 2 stub MIS and launch the
back_office several times, each time with a different maximum distance between
stops (to calculate transfers). For each different setting, we generate a dump
of the resulting database and compare it to a reference dump. If they don't match,
we exit the test and consider it as failed.
"""
import sys, os, unittest
from apiisim import tests


TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"


class TestChangeTransferMaxDistance(unittest.TestCase):

    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=TEST_DIR + "test1_populate_db.sql")
        self._mis_translator_process = tests.launch_mis_translator()

    def test(self):
        for conf_file, ref_dump_file in \
            [('test1_1.conf', 'db_dump1'),
             ('test1_2.conf', 'db_dump2'),
             ('test1_3.conf', 'db_dump3'),
             ('test1_4.conf', 'db_dump4')]:
            self.assertTrue(
                tests.calculate_and_check(
                    TEST_DIR + conf_file, TEST_DIR + ref_dump_file),
                msg="Database dump different than reference dump (%s)" \
                     % (ref_dump_file))

    def tearDown(self):
        tests.terminate_mis_translator(self._mis_translator_process)
        tests.drop_db()

if __name__ == '__main__':
    unittest.main()
