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


class TestPlannerMisStubs(unittest.TestCase):

    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db(populate_script=TEST_DIR + "test_planner_mis_stubs.sql")
        self._mis_translator_process = tests.launch_mis_translator()
        tests.launch_back_office(TEST_DIR + "test_planner_mis_stubs.conf")
        return


    def test(self):
        # "stop_area:DUA:SA:8754528"
        departure_position = LocationStructure(Latitude=48.765177, Longitude=2.410013)
        # "stop_area:SCF:SA:SAOCE87753731"
        arrival_position = LocationStructure(Latitude=43.699998, Longitude=5.09131)
        request = PlanTripRequestType(clientRequestId="test_id")
        request.Departure = TraceStop(Position=departure_position,
                                      AccessTime=timedelta(seconds=60))
        request.Arrival = TraceStop(Position=arrival_position,
                                    AccessTime=timedelta(seconds=60))
        request.DepartureTime = datetime.now()
        calculator = PlanTripCalculator(request, Queue.Queue())
        traces = calculator.compute_traces()
        logging.debug("TRACES: %s", traces)
        self.assertEquals(traces, [[1, 3], [1, 2, 3], [2, 3], [2, 1, 3]])
        departure_mises = [MisApi(x).get_name() for x in \
                           calculator._get_surrounding_mises(departure_position, datetime.now())]
        arrival_mises = [MisApi(x).get_name() for x in \
                         calculator._get_surrounding_mises(arrival_position, datetime.now())]
        for t in traces:
            full_trip = calculator.compute_trip(t)
            notif = create_full_notification("test_id", full_trip, timedelta())
            logging.debug(json.dumps(notif.marshal()))

            # Check that returned departure/arrival points are the same as those
            # requested.
            self.assertEquals(full_trip[0][1].Departure.TripStopPlace.Position.Longitude, \
                              departure_position.Longitude)
            self.assertEquals(full_trip[0][1].Departure.TripStopPlace.Position.Latitude, \
                              departure_position.Latitude)
            self.assertEquals(full_trip[-1][1].Arrival.TripStopPlace.Position.Longitude, \
                              arrival_position.Longitude)
            self.assertEquals(full_trip[-1][1].Arrival.TripStopPlace.Position.Latitude, \
                              arrival_position.Latitude)

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

            # Check that distance is valid.
            for _, trip in full_trip:
                self.assertTrue(trip.Distance > 0)

            # Basic consistency checks regarding dates/durations
            for _, trip in full_trip:
                self.assertTrue(trip.Departure.DateTime < trip.Arrival.DateTime)
                self.assertTrue(trip.Duration > 0)


    def tearDown(self):
        tests.terminate_mis_translator(self._mis_translator_process)
        tests.drop_db()
        return

if __name__ == '__main__':
    unittest.main()
