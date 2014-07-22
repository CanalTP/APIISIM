import sys, os, unittest, Queue, logging, json
from apiisim import tests

os.environ["PLANNER_DB_URL"] = "postgresql+psycopg2://%s:%s@localhost/%s" % \
                               (tests.ADMIN_NAME, tests.ADMIN_PASS, tests.DB_NAME)
os.environ["PLANNER_LOG_FILE"] = "/tmp/test_planner_mis_stubs.log"

from apiisim.planner.planner import PlanTripCalculator, TraceStop, create_full_notification, \
                                    MisApi, Session
from apiisim.common.plan_trip import PlanTripRequestType, LocationStructure
from apiisim import metabase
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased
from apiisim.planner import planner


TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"


class _TestPlannerMisStubsBase(unittest.TestCase):

    MIS_TRANSLATOR_CONF_FILE = ""

    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=self.DB_POPULATE_SCRIPT)
        self._mis_translator_process = tests.launch_mis_translator(self.MIS_TRANSLATOR_CONF_FILE)
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
            notif = create_full_notification("test_id", "trace_id", full_trip, timedelta())
            logging.debug(json.dumps(notif.marshal()))

            # Basic consistency checks.
            for _, trip in full_trip:
                self.assertTrue(trip.Departure.DateTime <= trip.Arrival.DateTime)
                self.assertTrue(trip.Duration >= timedelta())
                self.assertTrue(trip.Distance >= 0)

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
    EXPECTED_TRACES = [[1, 3], [2, 3], [2, 1, 3]]

    def setUp(self):
        planner.MAX_TRACE_LENGTH = 3
        super(TestPlannerMisStubs3Mis, self).setUp()


class TestPlannerMisStubs4Mis(_TestPlannerMisStubsBase):
    DB_POPULATE_SCRIPT = TEST_DIR + "test_planner_mis_stubs_4_mis.sql"
    EXPECTED_TRACES = [[4], [1, 3], [1, 4], [1, 2, 3], [1, 2, 4],
                       [1, 2, 4, 3], [1, 4, 3], [1, 4, 2, 3],
                       [2, 3], [2, 4], [2, 1, 3], [2, 1, 4], [2, 1, 4, 3],
                       [2, 4, 3], [2, 4, 1, 3], [4, 3], [4, 1, 3],
                       [4, 1, 2, 3], [4, 2, 3], [4, 2, 1, 3]]

    def setUp(self):
        planner.MAX_TRACE_LENGTH = 4
        super(TestPlannerMisStubs4Mis, self).setUp()

class _TestPlannerMisStubs3MisLight(_TestPlannerMisStubsBase):
    DB_POPULATE_SCRIPT = TEST_DIR + "test_planner_mis_stubs_light.sql"

    def setUp(self):
        planner.MAX_TRACE_LENGTH = 3
        super(_TestPlannerMisStubs3MisLight, self).setUp()

class TestPlannerMisStubsEmptyTrips(TestPlannerMisStubs3Mis):
    def setUp(self):
        self.MIS_TRANSLATOR_CONF_FILE = "/tmp/TestPlannerMisStubsEmptyTrips.conf"
        with open(self.MIS_TRANSLATOR_CONF_FILE, "w+") as f:
            f.write("[Stub]\n" \
                    "stub_mis_api_class = _EmptyTripsMisApi")
        super(TestPlannerMisStubsEmptyTrips, self).setUp()



"""
    Check that planner responses match reference dump files.
"""
class TestPlannerMisStubsDumpMatch(TestPlannerMisStubs3Mis):
    EXPECTED_TRACES = [[3, 1], [3, 2], [3, 1, 2]]

    def _new_request(self):
        request = PlanTripRequestType(clientRequestId="test_id")
        # "stop_area:CBE:SA:gen00133"
        request.Departure = TraceStop(Position=LocationStructure(Latitude=47.026427,
                                                                 Longitude=4.828594),
                                      AccessTime=timedelta(seconds=20))
        # "stop_area:SCF:SA:SAOCE87276196"
        request.Arrival = TraceStop(Position=LocationStructure(Latitude=48.976663,
                                                               Longitude=2.390363),
                                    AccessTime=timedelta(seconds=80))

        return request

    def _check_trip(self, request, ref_files, max_transfers):
        calculator = PlanTripCalculator(request, Queue.Queue())
        calculator.MAX_TRANSFERS = max_transfers
        traces = calculator.compute_traces()
        logging.debug("TRACES: %s", traces)
        self.assertEquals(traces, self.EXPECTED_TRACES)

        for trace, ref_file in zip(traces, ref_files):
            full_trip = calculator.compute_trip(trace)
            notif = create_full_notification("test_id", "trace_id", full_trip, timedelta())
            with open(TEST_DIR + ref_file) as f:
                ref_content = f.read()
                self.assertEquals(ref_content.strip(), json.dumps(notif.marshal()).strip(),
                                  "MIS response doesn't match ref_file '%s'" % ref_file)

    def testDepartureAt(self):
        request = self._new_request()
        request.DepartureTime = datetime(year=2014, month=10, day=23, hour=11, minute=20)

        self._check_trip(request, ["departure_at_dump1_1.json",
                                   "departure_at_dump1_2.json",
                                   "departure_at_dump1_3.json"], 3)


    def testArrivalAt(self):
        request = self._new_request()
        request.ArrivalTime = datetime(year=2014, month=10, day=23, hour=11, minute=20) \
                              + timedelta(hours=10)

        self._check_trip(request, ["arrival_at_dump1_1.json",
                                   "arrival_at_dump1_2.json",
                                   "arrival_at_dump1_3.json"], 3)

    def testDepartureAt2(self):
        request = self._new_request()
        request.DepartureTime = datetime(year=2014, month=10, day=23, hour=11, minute=20)

        self._check_trip(request, ["departure_at_dump2_1.json",
                                   "departure_at_dump2_2.json",
                                   "departure_at_dump2_3.json"], 10)


    def testArrivalAt2(self):
        request = self._new_request()
        request.ArrivalTime = datetime(year=2014, month=10, day=23, hour=11, minute=20) \
                              + timedelta(hours=10)

        self._check_trip(request, ["arrival_at_dump2_1.json",
                                   "arrival_at_dump2_2.json",
                                   "arrival_at_dump2_3.json"], 10)


"""
    In this test, we ensure that the planner removes duplicated departure/arrival 
    points before sending request to MIS. Indeed, "stop_area:DUA:SA:8768217" has 
    2 transfers (with "stop_area:SNC:SA:SAOCE87590554" and "stop_area:SNC:SA:SAOCE87682179"),
    it would therefore lead to duplicated points if the planner didn't care 
    to remove them.
"""
class TestPlannerMisStubsDuplicatedPoints(_TestPlannerMisStubs3MisLight):
    EXPECTED_TRACES = [[1], [2], [3], [1, 2], [1, 3], [1, 2, 3], [1, 3, 2], [2, 1], 
                       [2, 3], [2, 1, 3], [2, 3, 1], [3, 1], [3, 2], [3, 1, 2], [3, 2, 1]]

    def setUp(self):
        self.MIS_TRANSLATOR_CONF_FILE = "/tmp/TestPlannerMisStubsConsistencyChecks.conf"
        with open(self.MIS_TRANSLATOR_CONF_FILE, "w+") as f:
            f.write("[Stub]\n" \
                    "stub_mis_api_class = _ConsistencyChecksMisApi")
        super(TestPlannerMisStubsDuplicatedPoints, self).setUp()

    def _new_request(self):
        request = PlanTripRequestType(clientRequestId="test_id")
        # "stop_area:DUA:SA:8768217"
        request.Departure = TraceStop(Position=LocationStructure(Latitude=48.540187,
                                                                 Longitude=2.624123),
                                      AccessTime=timedelta(seconds=60))
        # "stop_area:SNC:SA:SAOCE87682179"
        request.Arrival = TraceStop(Position=LocationStructure(Latitude=48.539939,
                                                               Longitude=2.624046),
                                    AccessTime=timedelta(seconds=60))

        return request


if __name__ == '__main__':
    test_classes_to_run = [TestPlannerMisStubs3Mis, TestPlannerMisStubs4Mis,
                           TestPlannerMisStubsEmptyTrips, TestPlannerMisStubsDumpMatch,
                           TestPlannerMisStubsDuplicatedPoints]

    loader = unittest.TestLoader()

    suites_list = []
    for test_class in test_classes_to_run:
        suite = loader.loadTestsFromTestCase(test_class)
        suites_list.append(suite)

    runner = unittest.TextTestRunner()
    runner.run(unittest.TestSuite(suites_list))
