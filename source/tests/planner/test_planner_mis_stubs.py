import sys, os, unittest, Queue, logging, json
TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"
# A bit dirty but we need this to ensure that when importing "tests", we import
# our "tests" module, not "tests" module from another package.
sys.path = [TEST_DIR + "../../"] + sys.path

import tests

os.environ["PLANNER_DB_URL"] = "postgresql+psycopg2://%s:%s@localhost/%s" % \
                               (tests.ADMIN_NAME, tests.ADMIN_PASS, tests.DB_NAME)
os.environ["PLANNER_LOG_FILE"] = "/tmp/test_planner_mis_stubs.log"

from planner.planner import PlanTripCalculator, TraceStop, create_full_notification, \
                            MisApi, Session
from common.plan_trip import PlanTripRequestType, LocationStructure
import metabase
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased
from planner import planner


class _TestPlannerMisStubsBase(unittest.TestCase):

    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=self.DB_POPULATE_SCRIPT)
        self._mis_translator_process = tests.launch_mis_translator()
        tests.launch_back_office(TEST_DIR + "test_planner_mis_stubs.conf")


    def _check_trip(self, request):
        calculator = PlanTripCalculator(request, Queue.Queue())
        traces = calculator.compute_traces()
        logging.debug("TRACES: %s", traces)
        self.assertEquals(traces, self.EXPECTED_TRACES)
        departure_mises = [MisApi(x).get_name() for x in \
                           calculator._get_surrounding_mises(request.Departure.Position, datetime.now())]
        arrival_mises = [MisApi(x).get_name() for x in \
                         calculator._get_surrounding_mises(request.Arrival.Position, datetime.now())]
        for t in traces:
            full_trip = calculator.compute_trip(t)
            notif = create_full_notification("test_id", full_trip, timedelta())
            logging.debug(json.dumps(notif.marshal()))

            # Basic consistency checks.
            for _, trip in full_trip:
                self.assertTrue(trip.Departure.DateTime < trip.Arrival.DateTime)
                self.assertTrue(trip.Duration > 0)
                self.assertTrue(trip.Distance > 0)

            # We should have one trip per MIS
            self.assertTrue(len(full_trip) == len(t))

            # Check that returned departure/arrival points are the same as those
            # requested.
            self.assertEquals(full_trip[0][1].Departure.TripStopPlace.Position.Longitude, \
                              request.Departure.Position.Longitude)
            self.assertEquals(full_trip[0][1].Departure.TripStopPlace.Position.Latitude, \
                              request.Departure.Position.Latitude)
            self.assertEquals(full_trip[-1][1].Arrival.TripStopPlace.Position.Longitude, \
                              request.Arrival.Position.Longitude)
            self.assertEquals(full_trip[-1][1].Arrival.TripStopPlace.Position.Latitude, \
                              request.Arrival.Position.Latitude)

            # Check that departure/arrival MISes are correct.
            self.assertTrue(full_trip[0][0].get_name() in departure_mises)
            self.assertTrue(full_trip[-1][0].get_name() in arrival_mises)

            # For all partial trips, check that arrival stop point is connected to
            # the departure stop point of the next trip (via a transfer).
            db_session = Session()
            departures = [x[1].Departure.TripStopPlace.id for x in full_trip]
            arrivals = [x[1].Arrival.TripStopPlace.id for x in full_trip]
            for i in range(0, len(departures) - 1):
                a = arrivals[i]
                d = departures[i + 1]
                s1 = db_session.query(metabase.Stop) \
                               .filter_by(code=d) \
                               .subquery()
                s2 = db_session.query(metabase.Stop) \
                               .filter_by(code=a) \
                               .subquery()
                self.assertTrue(
                    db_session.query(metabase.Transfer) \
                              .filter(or_(and_(metabase.Transfer.stop1_id == s1.c.id,
                                               metabase.Transfer.stop2_id == s2.c.id),
                                          and_(metabase.Transfer.stop1_id == s2.c.id,
                                               metabase.Transfer.stop2_id == s1.c.id))) \
                              .count() > 0)

            db_session.close()
            Session.remove()


    def _new_request(self):
        request = PlanTripRequestType(clientRequestId="test_id")
        # "stop_area:DUA:SA:8754528"
        request.Departure = TraceStop(Position=LocationStructure(Latitude=48.765177,
                                                                 Longitude=2.410013),
                                      AccessTime=timedelta(seconds=60))
        # "stop_area:SCF:SA:SAOCE87753731"
        request.Arrival = TraceStop(Position=LocationStructure(Latitude=43.699998,
                                                               Longitude=5.09131),
                                    AccessTime=timedelta(seconds=60))

        return request



    def testDepartureAt(self):
        request = self._new_request()
        request.DepartureTime = datetime.now()

        self._check_trip(request)


    def testArrivalAt(self):
        request = self._new_request()
        request.ArrivalTime = datetime.now() + timedelta(hours=10)

        self._check_trip(request)


    def tearDown(self):
        tests.terminate_mis_translator(self._mis_translator_process)
        # Reset SQLAlchemy connection pool. Otherwise, some connections can stay
        # open, which will prevent us from deleting the database.
        planner.clean_db_engine()
        tests.drop_db()


class TestPlannerMisStubs3Mis(_TestPlannerMisStubsBase):
    DB_POPULATE_SCRIPT = TEST_DIR + "test_planner_mis_stubs.sql"
    EXPECTED_TRACES = [[1, 3], [1, 2, 3], [2, 3], [2, 1, 3]]

    def setUp(self):
        planner.MAX_TRACE_LENGTH = 3
        super(TestPlannerMisStubs3Mis, self).setUp()


class TestPlannerMisStubs4Mis(_TestPlannerMisStubsBase):
    DB_POPULATE_SCRIPT = TEST_DIR + "test_planner_mis_stubs_4_mis.sql"
    EXPECTED_TRACES = [[4], [1, 3], [1, 4], [1, 2, 3], [1, 2, 4], [1, 2, 3, 4],
                       [1, 2, 4, 3], [1, 3, 4], [1, 3, 2, 4], [1, 4, 3], [1, 4, 2, 3],
                       [2, 3], [2, 4], [2, 1, 3], [2, 1, 4], [2, 1, 3, 4], [2, 1, 4, 3],
                       [2, 3, 4], [2, 3, 1, 4], [2, 4, 3], [2, 4, 1, 3], [4, 3], [4, 1, 3],
                       [4, 1, 2, 3], [4, 2, 3], [4, 2, 1, 3]]

    def setUp(self):
        planner.MAX_TRACE_LENGTH = 4
        super(TestPlannerMisStubs4Mis, self).setUp()


if __name__ == '__main__':
    test_classes_to_run = [TestPlannerMisStubs3Mis, TestPlannerMisStubs4Mis]

    loader = unittest.TestLoader()

    suites_list = []
    for test_class in test_classes_to_run:
        suite = loader.loadTestsFromTestCase(test_class)
        suites_list.append(suite)

    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(suites_list))
