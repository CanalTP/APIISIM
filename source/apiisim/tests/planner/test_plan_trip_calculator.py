#!/usr/bin/python
# -*- encoding: utf8 -*-
import unittest

from datetime import datetime

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

    def get_summed_up_itineraries_response_type_sample(self):
        trips = SummedUpItinerariesResponseType()
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "Paris"
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime(2014, 10, 21, 13, 14)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "Marseille"
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime(2014, 10, 21, 11, 20)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "Strasbourg"
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime(2014, 10, 21, 17, 14)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "Marseille"
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime(2014, 10, 21, 14, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "Lyon"
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime(2014, 10, 21, 15, 30)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "Marseille"
        trips.summedUpTrips.append(trip)
        return trips

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

    def test_filter_best_trip_response(self):
        trips = self.get_summed_up_itineraries_response_type_sample()
        self.calculator._filter_best_trip_response(trips, True)
        self.assertTrue(len(trips.summedUpTrips) == 1)
        self.assertTrue(trips.summedUpTrips[0].Arrival.DateTime == datetime(2014, 10, 21, 13, 14))
        trips = self.get_summed_up_itineraries_response_type_sample()
        self.calculator._filter_best_trip_response(trips, False)
        self.assertTrue(len(trips.summedUpTrips) == 1)
        self.assertTrue(trips.summedUpTrips[0].Departure.DateTime == datetime(2014, 10, 21, 14, 30))


if __name__ == '__main__':
    unittest.main()
