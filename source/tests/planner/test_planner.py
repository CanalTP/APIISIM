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


    def testDepartureAtDetailedTrace(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(request, Queue.Queue())

        for i in [2, 3, 4]:
            res = calculator._departure_at_detailed_trace(range(1, i + 1))
            logging.debug(res)
            for j in range(0, i):
                k = j + 1
                self.assertEquals(res[j][0].get_name(), "mis%s" % k)
                if j == 0:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "departure")
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k + 1))
                elif j == (i - 1):
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "arrival")
                    self.assertEquals(res[j][3], None)
                else:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s1" % k)
                    self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k + 1))


    def testArrivalAtDetailedTrace(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(request, Queue.Queue())

        for i in [2, 3, 4]:
            res = calculator._arrival_at_detailed_trace(range(1, i + 1))
            logging.debug(res)
            k = i
            for j in range(0, i):
                self.assertEquals(res[j][0].get_name(), "mis%s" % k)
                if j == (i - 1):
                    self.assertEquals(res[j][1][0].PlaceTypeId, "departure")
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][3], None)
                elif j == 0:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "arrival")
                    if k <= 2:
                        self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k - 1))
                    else:
                        self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s1" % (k - 1))
                else:
                    self.assertEquals(res[j][1][0].PlaceTypeId, "stop_code%s0" % k)
                    self.assertEquals(res[j][2][0].PlaceTypeId, "stop_code%s1" % k)
                    if k <= 2:
                        self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s0" % (k - 1))
                    else:
                        self.assertEquals(res[j][3][0].PlaceTypeId, "stop_code%s1" % (k - 1))
                k -= 1

    def testFilterTraces(self):
        request = PlanTripRequestType()
        request.Departure = TraceStop(PlaceTypeId="departure")
        request.Arrival = TraceStop(PlaceTypeId="arrival")
        calculator = PlanTripCalculator(request, Queue.Queue())
        self.assertEquals(calculator._filter_traces([[1, 2, 3, 4], [1, 3, 4], [4, 3, 1],
                                                    [2, 1, 4], [3, 4, 2], [3, 2, 4],
                                                    [1, 4, 3, 2], [4, 3, 1, 2], [3, 2, 1, 4]]),
                          [[1, 3, 4], [4, 3, 1], [3, 4, 2], [1, 4, 3, 2]])

    def tearDown(self):
        from planner.planner import clean_db_engine
        # Reset SQLAlchemy connection pool. Otherwise, some connections can stay
        # open, which will prevent us from deleting the database.
        clean_db_engine()
        tests.drop_db()


if __name__ == '__main__':
    unittest.main()
