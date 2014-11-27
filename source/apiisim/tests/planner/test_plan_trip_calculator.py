#!/usr/bin/python
# -*- encoding: utf8 -*-
import unittest

import datetime

from apiisim.common.plan_trip import PlanTripRequestType, \
    PlanTripExistenceNotificationResponseType, \
    PlanTripNotificationResponseType, \
    PlanTripResponse, EndingSearch, StartingSearch, \
    AbstractNotificationResponseType, StepEndPointType, \
    EndPointType, TripStopPlaceType, LocationStructure, \
    TripType, StepType, PTRideType, LegType, SectionType, \
    PartialTripType, ComposedTripType, ProviderType
from apiisim.common.mis_plan_summed_up_trip import LocationContextType, \
    SummedUpItinerariesResponseType, \
    StatusType, SummedUpTripType, \
    SummedUpItinerariesRequestType

from apiisim.planner.plan_trip_calculator import PlanTripCalculator
from apiisim.tests.planner import TripCollection


class DummyQueue():
    def __init__(self):
        self.queue = []

    def put(self, notification):
        self.queue.append(notification)


class DummyPlanner():
    def __init__(self):
        self.session = 0

    def create_db_session(self):
        self.session = 1
        return None


class TestPlanTripCalculator(unittest.TestCase):
    def setUp(self):
        self.queue = DummyQueue()
        self.planner = DummyPlanner()
        self.calculator = PlanTripCalculator(planner=self.planner, params=None, notif_queue=self.queue)

    def test_generate_trace_id(self):
        mis_trace = [2, 5, 4]
        trace_id = self.calculator._generate_trace_id(mis_trace)
        self.assertTrue(trace_id == "2_5_4")
        mis_trace = [3, 8]
        trace_id = self.calculator._generate_trace_id(mis_trace)
        self.assertTrue(trace_id == "3_8")
        mis_trace = [6]
        trace_id = self.calculator._generate_trace_id(mis_trace)
        self.assertTrue(trace_id == "6")

    def test_update_stop_times(self):
        trips = TripCollection._summed_up_from_paris_lyon_to_strasbourg_marseille()
        transition_stops = [TripCollection._stop_trace_orleans(None, None),
                            TripCollection._stop_trace_strasbourg(None, None),
                            TripCollection._stop_trace_marseille(None, None),
                            TripCollection._stop_trace_reims(None, None)]
        linked_stops = [TripCollection._stop_trace_orleans(None, None, True),
                        TripCollection._stop_trace_strasbourg(None, None, True),
                        TripCollection._stop_trace_marseille(None, None, True),
                        TripCollection._stop_trace_reims(None, None, True)]
        transition_durations = [datetime.timedelta(minutes=10),
                                datetime.timedelta(minutes=16),
                                datetime.timedelta(minutes=9),
                                datetime.timedelta(minutes=15)]
        self.calculator._update_stop_times(transition_stops, linked_stops, transition_durations,
                                           "arrival_time", trips.summedUpTrips, "Arrival")
        self.assertTrue(len(transition_stops) == 2)
        self.assertTrue(len(linked_stops) == 2)
        self.assertTrue(transition_stops[0].PlaceTypeId == "stop_area:SCF:SA:SAOCE87212027")
        self.assertTrue(transition_stops[0].arrival_time == datetime.datetime(2014, 10, 21, 15, 15))
        self.assertTrue(linked_stops[0].PlaceTypeId == "stop_area:SCF:SA:SAOCE87212027L")

    def test_update_linked_stop_times(self):
        trips = TripCollection._summed_up_from_paris_lyon_to_strasbourg_marseille()
        transition_stops = [TripCollection._stop_trace_orleans(None, None),
                            TripCollection._stop_trace_strasbourg(None, None),
                            TripCollection._stop_trace_marseille(None, None),
                            TripCollection._stop_trace_reims(None, None)]
        linked_stops = [TripCollection._stop_trace_orleans(None, None, True),
                        TripCollection._stop_trace_strasbourg(None, None, True),
                        TripCollection._stop_trace_marseille(None, None, True),
                        TripCollection._stop_trace_reims(None, None, True)]
        transition_durations = [datetime.timedelta(minutes=10),
                                datetime.timedelta(minutes=16),
                                datetime.timedelta(minutes=9),
                                datetime.timedelta(minutes=15)]
        self.calculator._update_stop_times(transition_stops, linked_stops, transition_durations,
                                           "arrival_time", trips.summedUpTrips, "Arrival")
        self.calculator._update_linked_stop_times(transition_stops, linked_stops, transition_durations, clockwise=True)
        self.assertTrue(len(transition_stops) == 2)
        self.assertTrue(len(linked_stops) == 2)
        self.assertTrue(transition_stops[0].PlaceTypeId == "stop_area:SCF:SA:SAOCE87212027")
        self.assertTrue(transition_stops[0].arrival_time == datetime.datetime(2014, 10, 21, 15, 15))
        self.assertTrue(linked_stops[0].PlaceTypeId == "stop_area:SCF:SA:SAOCE87212027L")
        self.assertTrue(linked_stops[0].arrival_time == datetime.datetime(2014, 10, 21, 15, 31))

    def test_filter_best_trip_response(self):
        trips = TripCollection._summed_up_from_paris_lyon_to_marseille()
        self.calculator._filter_best_trip_response(trips.summedUpTrips, True)
        self.assertTrue(len(trips.summedUpTrips) == 1)
        self.assertTrue(trips.summedUpTrips[0].Arrival.DateTime == datetime.datetime(2014, 10, 21, 15, 14))
        trips = TripCollection._summed_up_from_marseille_to_paris_strasbourg_lyon()
        self.calculator._filter_best_trip_response(trips.summedUpTrips, False)
        print len(trips.summedUpTrips)
        self.assertTrue(len(trips.summedUpTrips) == 1)
        self.assertTrue(trips.summedUpTrips[0].Departure.DateTime == datetime.datetime(2014, 10, 21, 12, 30))


if __name__ == '__main__':
    unittest.main()
