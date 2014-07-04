import sys, os, unittest, Queue, logging
TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"
# A bit dirty but we need this to ensure that when importing "tests", we import
# our "tests" module, not "tests" module from another package.
sys.path = [TEST_DIR + "../../"] + sys.path

import tests

os.environ["PLANNER_DB_URL"] = "postgresql+psycopg2://%s:%s@localhost/%s" % \
                               (tests.ADMIN_NAME, tests.ADMIN_PASS, tests.DB_NAME)
os.environ["PLANNER_LOG_FILE"] = "/tmp/test_planner.log"

from planner.planner import PlanTripCalculator, TraceStop
from common.plan_trip import PlanTripRequestType


class TestPlanner(unittest.TestCase):

    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=TEST_DIR + "test_planner.sql")

    def testDetailedTrace(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(request, Queue.Queue())

        for i in [2, 3, 4]:
            res = calculator._get_detailed_trace(range(1, i + 1))
            logging.debug(res)
            for j in range(1, i + 1):
                k = j - 1
                self.assertEquals(res[k][0].get_name(), "mis%s" % j)
                if j == 1:
                    self.assertEquals(res[k][1][0].PlaceTypeId, "departure")
                    self.assertEquals(res[k][2][0].PlaceTypeId, "stop_code%s0" % j)
                    self.assertEquals(res[k][3][0].PlaceTypeId, "stop_code%s0" % (j + 1))
                elif j == i:
                    self.assertEquals(res[k][1][0].PlaceTypeId, "stop_code%s0" % j)
                    self.assertEquals(res[k][2][0].PlaceTypeId, "arrival")
                    self.assertEquals(res[k][3], None)
                else:
                    self.assertEquals(res[k][1][0].PlaceTypeId, "stop_code%s0" % j)
                    self.assertEquals(res[k][2][0].PlaceTypeId, "stop_code%s1" % j)
                    self.assertEquals(res[k][3][0].PlaceTypeId, "stop_code%s0" % (j + 1))

    def tearDown(self):
        tests.drop_db()

if __name__ == '__main__':
    unittest.main()
