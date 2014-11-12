#!/usr/bin/python
# -*- encoding: utf8 -*-
import os
import unittest
import json
from datetime import timedelta, datetime

from apiisim import tests
from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import LocationStructure
from apiisim.common.mis_plan_trip import ItineraryResponseType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType, LocationContextType
from apiisim.mis_translator.mis_api.stub import base as stub


TEST_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "")


class TestStub(unittest.TestCase):
    def setUp(self):
        STOPS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stub_transilien_stops.json")
        STOPS_FIELD = "stop_areas"
        self.stub_transilien = stub._CrowFliesMisApi(STOPS_FILE, STOPS_FIELD, tests.DB_NAME)

    def tearDown(self):
        del self.stub_transilien

    def _stop_orly(self, access_time=0):
        loc = LocationContextType()
        loc.Position = LocationStructure(Latitude=48.743411, Longitude=2.402955)
        loc.AccessTime = timedelta(minutes=access_time)
        loc.PlaceTypeId = "stop_area:DUA:SA:4:57"
        return loc

    def _stop_choisy(self, access_time=0):
        loc = LocationContextType()
        loc.Position = LocationStructure(Latitude=48.765177, Longitude=2.410013)
        loc.AccessTime = timedelta(minutes=access_time)
        loc.PlaceTypeId = "stop_area:DUA:SA:8754528"
        return loc

    def _stop_thiais(self, access_time=0):
        loc = LocationContextType()
        loc.Position = LocationStructure(Latitude=48.76577965, Longitude=2.392136794)
        loc.AccessTime = timedelta(minutes=access_time)
        loc.PlaceTypeId = "stop_area:DUA:SA:4:126"
        return loc

    def _stop_morillons(self, access_time=0):
        loc = LocationContextType()
        loc.Position = LocationStructure(Latitude=48.731742, Longitude=2.432025)
        loc.AccessTime = timedelta(minutes=access_time)
        loc.PlaceTypeId = "stop_area:DUA:SA:4:141"
        return loc

    def test_get_stops(self):
        stops = self.stub_transilien.get_stops()
        self.assertEquals(len(stops), 10000)

    def test_get_earliest_location(self):
        # geographic order
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(),
             [self._stop_morillons(), self._stop_orly(), self._stop_thiais()], 0)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:126')  #Thiais
        self.assertEqual(round(distance), 743.0)
        self.assertEqual(duration, timedelta())
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(),
             [self._stop_morillons(), self._stop_orly()], 0)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:57')  #Orly
        self.assertEqual(round(distance), 2476.0)
        self.assertEqual(duration, timedelta(minutes=2))
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(),
             [self._stop_morillons()], 0)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:141')  #Morillons
        self.assertEqual(round(distance), 4055.0)
        self.assertEqual(duration, timedelta(minutes=4))

        # test with inactive access_time
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(3),
             [self._stop_morillons(), self._stop_orly(), self._stop_thiais()], 0)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:126')  #Thiais
        self.assertEqual(round(distance), 743.0)
        self.assertEqual(duration, timedelta())

        # test with active access_time on departure
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(3),
             [self._stop_morillons(), self._stop_orly(), self._stop_thiais()], 1)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:126')  #Thiais
        self.assertEqual(round(distance), 743.0)
        self.assertEqual(duration, timedelta())

        # test with active access_time on arrival
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(3),
             [self._stop_morillons(), self._stop_orly(), self._stop_thiais(3)], 1)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:57')  #Orly
        self.assertEqual(round(distance), 2476.0)
        self.assertEqual(duration, timedelta(minutes=2))

        # test with active access_time on arrival in case of "arrival at"
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(3),
             [self._stop_morillons(), self._stop_orly(), self._stop_thiais(3)], -1)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:126')  #Thiais
        self.assertEqual(round(distance), 743.0)
        self.assertEqual(duration, timedelta())

        # test with active access_time on arrival in case of "arrival at"
        best_arrival, distance, duration = self.stub_transilien._get_earliest_location\
            (self._stop_choisy(3),
             [self._stop_morillons(3), self._stop_orly(3), self._stop_thiais()], -1)
        self.assertEqual(best_arrival.PlaceTypeId, 'stop_area:DUA:SA:4:57')  #Orly
        self.assertEqual(round(distance), 2476.0)
        self.assertEqual(duration, timedelta(minutes=2))

if __name__ == '__main__':
    tests.drop_db()
    unittest.main()
