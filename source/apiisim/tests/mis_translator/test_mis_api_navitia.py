#!/usr/bin/python
# -*- encoding: utf8 -*-
import os
import unittest
import json
from datetime import timedelta, datetime

from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import LocationStructure
from apiisim.common.mis_plan_trip import ItineraryResponseType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType, LocationContextType
from apiisim.mis_translator.mis_api.navitia import base as navitia


TEST_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "")


class TestNavitia(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _json_from_file(self, filename):
        f = open(TEST_DIR + filename, "r")
        content = "".join(f.readlines())
        js = json.loads(content)
        f.close()
        return js

    def test_parse_endpoint(self):
        endpoint = navitia.parse_end_point(self._json_from_file("endpoint1.json"))
        self.assertEquals(endpoint.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(endpoint.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(endpoint.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(endpoint.TripStopPlace.CityName, "Paris")
        self.assertEquals(endpoint.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(endpoint.TripStopPlace.Position.Longitude, "2.3468313805225653")

    def test_parse_stop_times(self):
        steps = navitia.parse_stop_times(self._json_from_file("stoptimes1.json"))

        # print len(steps)
        #step = steps[8]
        #print step.id
        #print step.Departure.TripStopPlace.id
        #print step.Departure.TripStopPlace.Name
        #print step.Departure.TripStopPlace.Position.Latitude
        #print step.Departure.TripStopPlace.Position.Longitude
        #print step.Arrival.TripStopPlace.id
        #print step.Arrival.TripStopPlace.Name
        #print step.Arrival.TripStopPlace.Position.Latitude
        #print step.Arrival.TripStopPlace.Position.Longitude
        #print step.Departure.DateTime
        #print step.Arrival.DateTime
        #print step.Duration

        self.assertEquals(len(steps), 17)
        self.assertEquals(steps[0].id, "stop_point:DUA:SP:8797807:stop_point:DUA:SP:8759114")
        self.assertEquals(steps[0].Departure.TripStopPlace.id, "stop_point:DUA:SP:8797807")
        self.assertEquals(steps[0].Departure.TripStopPlace.Name, "CHATELET")
        self.assertEquals(steps[0].Departure.TripStopPlace.Position.Latitude, "48.858285")
        self.assertEquals(steps[0].Departure.TripStopPlace.Position.Longitude, "2.348755")
        self.assertEquals(steps[0].Arrival.TripStopPlace.id, "stop_point:DUA:SP:8759114")
        self.assertEquals(steps[0].Arrival.TripStopPlace.Name, "ST MICHEL NOTRE DAME NOCTILIEN")
        self.assertEquals(steps[0].Arrival.TripStopPlace.Position.Latitude, "48.85345")
        self.assertEquals(steps[0].Arrival.TripStopPlace.Position.Longitude, "2.343838")
        self.assertEquals(steps[0].Departure.DateTime, datetime(2014, 9, 30, 3, 53))
        self.assertEquals(steps[0].Arrival.DateTime, datetime(2014, 9, 30, 3, 56))
        self.assertEquals(steps[0].Duration, timedelta(0, 180))

        self.assertEquals(steps[8].id, "stop_point:DUA:SP:8759178:stop_point:DUA:SP:8741460")
        self.assertEquals(steps[8].Departure.TripStopPlace.id, "stop_point:DUA:SP:8759178")
        self.assertEquals(steps[8].Departure.TripStopPlace.Name, "CHAVILLE RIVE GAUCHE NOCTILIEN")
        self.assertEquals(steps[8].Departure.TripStopPlace.Position.Latitude, "48.804788")
        self.assertEquals(steps[8].Departure.TripStopPlace.Position.Longitude, "2.188484")
        self.assertEquals(steps[8].Arrival.TripStopPlace.id, "stop_point:DUA:SP:8741460")
        self.assertEquals(steps[8].Arrival.TripStopPlace.Name, "GRACE DE DIEU")
        self.assertEquals(steps[8].Arrival.TripStopPlace.Position.Latitude, "48.804135")
        self.assertEquals(steps[8].Arrival.TripStopPlace.Position.Longitude, "2.176798")
        self.assertEquals(steps[8].Departure.DateTime, datetime(2014, 9, 30, 4, 37))
        self.assertEquals(steps[8].Arrival.DateTime, datetime(2014, 9, 30, 4, 39))
        self.assertEquals(steps[8].Duration, timedelta(0, 120))

        self.assertEquals(steps[16].id, "stop_point:DUA:SP:8759183:stop_point:DUA:SP:8759185")
        self.assertEquals(steps[16].Departure.TripStopPlace.id, "stop_point:DUA:SP:8759183")
        self.assertEquals(steps[16].Departure.TripStopPlace.Name, "ST CYR NOCTILIEN")
        self.assertEquals(steps[16].Departure.TripStopPlace.Position.Latitude, "48.798926")
        self.assertEquals(steps[16].Departure.TripStopPlace.Position.Longitude, "2.07298")
        self.assertEquals(steps[16].Arrival.TripStopPlace.id, "stop_point:DUA:SP:8759185")
        self.assertEquals(steps[16].Arrival.TripStopPlace.Name, "ST QUENTIN EN YVELINES NOCTILIEN")
        self.assertEquals(steps[16].Arrival.TripStopPlace.Position.Latitude, "48.787966")
        self.assertEquals(steps[16].Arrival.TripStopPlace.Position.Longitude, "2.044703")
        self.assertEquals(steps[16].Departure.DateTime, datetime(2014, 9, 30, 5, 2))
        self.assertEquals(steps[16].Arrival.DateTime, datetime(2014, 9, 30, 5, 8))
        self.assertEquals(steps[16].Duration, timedelta(0, 360))

    def test_journey2summed_up_trip(self):
        trip = navitia.journey_to_summed_up_trip(self._json_from_file("journey1.json"))

        # print trip.InterchangeCount
        #print trip.InterchangeDuration

        #print trip.Departure.DateTime
        #print trip.Departure.TripStopPlace.id
        #print trip.Departure.TripStopPlace.Name
        #print trip.Departure.TripStopPlace.Position.Latitude
        #print trip.Departure.TripStopPlace.Position.Longitude

        #print trip.Arrival.DateTime
        #print trip.Arrival.TripStopPlace.id
        #print trip.Arrival.TripStopPlace.Name
        #print trip.Arrival.TripStopPlace.Position.Latitude
        #print trip.Arrival.TripStopPlace.Position.Longitude

        self.assertEquals(trip.InterchangeCount, 3)
        self.assertEquals(trip.InterchangeDuration, 1886)

        self.assertEquals(trip.Departure.DateTime, datetime(2014, 9, 30, 3, 49, 53))
        self.assertEquals(trip.Departure.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Longitude, "2.3468313805225653")

        self.assertEquals(trip.Arrival.DateTime, datetime(2014, 9, 30, 6, 47))
        self.assertEquals(trip.Arrival.TripStopPlace.id, "stop_area:DUA:SA:8738664")
        self.assertEquals(trip.Arrival.TripStopPlace.Name, "VILLENNES SUR SEINE (Villennes-sur-Seine)")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Latitude, "48.939491")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Longitude, "1.999496")

    def test_journey2str(self):
        txt = navitia.journey_to_str(self._json_from_file("journey1.json"))
        self.assertEquals(txt,
                          "From: 2.3468313805225653;48.859484964845606 | To: stop_area:DUA:SA:8738664 "
                          "| Departure: 20140930T034953 | Arrival: 20140930T064600 | Duration: 10567 "
                          "| Nb_transfers: 3 | Type: best")

    def test_journey2detailed_trip(self):
        trip = navitia.journey_to_detailed_trip(self._json_from_file("journey1.json"))

        print trip.Departure

        # print trip.Duration
        #print trip.Distance
        #print trip.Disrupted
        #print trip.InterchangeNumber
        #print trip.CarFootprint
        #print len(trip.sections)

        #print trip.Departure.DateTime
        #print trip.Departure.TripStopPlace.id
        #print trip.Departure.TripStopPlace.Name
        #print trip.Departure.TripStopPlace.Position.Latitude
        #print trip.Departure.TripStopPlace.Position.Longitude

        #print trip.Arrival.DateTime
        #print trip.Arrival.TripStopPlace.id
        #print trip.Arrival.TripStopPlace.Name
        #print trip.Arrival.TripStopPlace.Position.Latitude
        #print trip.Arrival.TripStopPlace.Position.Longitude

        #section = trip.sections[5]
        #print section.PartialTripId

        #print section.PTRide.Line.Name
        #print section.PTRide.Line.Number
        #print section.PTRide.Line.PublishedName
        #print section.PTRide.Line.RegistrationNumber
        #print section.PTRide.PTNetwork.id
        #print section.PTRide.PTNetwork.Name
        #print section.PTRide.PTNetwork.RegistrationNumber
        #print section.PTRide.PublicTransportMode
        #print section.PTRide.Departure.TripStopPlace.id
        #print section.PTRide.Departure.TripStopPlace.Name
        #print section.PTRide.Departure.TripStopPlace.Position.Latitude
        #print section.PTRide.Departure.TripStopPlace.Position.Longitude
        #print section.PTRide.Arrival.TripStopPlace.id
        #print section.PTRide.Arrival.TripStopPlace.Name
        #print section.PTRide.Arrival.TripStopPlace.Position.Latitude
        #print section.PTRide.Arrival.TripStopPlace.Position.Longitude
        #print section.PTRide.Duration
        #print section.PTRide.StopHeadSign
        #print len(section.PTRide.steps)

        #print section.Leg.Departure.TripStopPlace.id
        #print section.Leg.Departure.TripStopPlace.Name
        #print section.Leg.Departure.TripStopPlace.Position.Latitude
        #print section.Leg.Departure.TripStopPlace.Position.Longitude
        #print section.Leg.Arrival.TripStopPlace.id
        #print section.Leg.Arrival.TripStopPlace.Name
        #print section.Leg.Arrival.TripStopPlace.Position.Latitude
        #print section.Leg.Arrival.TripStopPlace.Position.Longitude
        #print section.Leg.Duration
        #print section.Leg.SelfDriveMode

        self.assertEquals(trip.Duration, timedelta(0, 2 * 3600 + 56 * 60 + 7))
        self.assertEquals(trip.Distance, 0)
        self.assertEquals(trip.Disrupted, False)
        self.assertEquals(trip.InterchangeNumber, 3)
        self.assertEquals(trip.CarFootprint, None)
        self.assertEquals(len(trip.sections), 7)

        self.assertEquals(trip.Departure.DateTime, datetime(2014, 9, 30, 3, 49, 53))
        self.assertEquals(trip.Departure.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Longitude, "2.3468313805225653")

        self.assertEquals(trip.Arrival.DateTime, datetime(2014, 9, 30, 6, 47))
        self.assertEquals(trip.Arrival.TripStopPlace.id, "stop_area:DUA:SA:8738664")
        self.assertEquals(trip.Arrival.TripStopPlace.Name, "VILLENNES SUR SEINE (Villennes-sur-Seine)")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Latitude, "48.939491")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Longitude, "1.999496")

        self.assertEquals(trip.sections[0].PartialTripId, "section_8_0")
        self.assertEquals(trip.sections[0].PTRide, None)
        self.assertEquals(trip.sections[0].Leg.Departure.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(trip.sections[0].Leg.Departure.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(trip.sections[0].Leg.Departure.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(trip.sections[0].Leg.Departure.TripStopPlace.Position.Longitude, "2.3468313805225653")
        self.assertEquals(trip.sections[0].Leg.Arrival.TripStopPlace.id, "stop_point:DUA:SP:8797807")
        self.assertEquals(trip.sections[0].Leg.Arrival.TripStopPlace.Name, "CHATELET")
        self.assertEquals(trip.sections[0].Leg.Arrival.TripStopPlace.Position.Latitude, "48.858285")
        self.assertEquals(trip.sections[0].Leg.Arrival.TripStopPlace.Position.Longitude, "2.348755")
        self.assertEquals(trip.sections[0].Leg.Duration, timedelta(0, 2 * 60 + 26))
        self.assertEquals(trip.sections[0].Leg.SelfDriveMode, "foot")

        self.assertEquals(trip.sections[2].PartialTripId, "section_10_0")
        self.assertEquals(trip.sections[2].PTRide, None)
        self.assertEquals(trip.sections[2].Leg.Departure.TripStopPlace.id, "stop_point:DUA:SP:8759185")
        self.assertEquals(trip.sections[2].Leg.Departure.TripStopPlace.Name, "ST QUENTIN EN YVELINES NOCTILIEN")
        self.assertEquals(trip.sections[2].Leg.Departure.TripStopPlace.Position.Latitude, "48.787966")
        self.assertEquals(trip.sections[2].Leg.Departure.TripStopPlace.Position.Longitude, "2.044703")
        self.assertEquals(trip.sections[2].Leg.Arrival.TripStopPlace.id, "stop_point:DUA:SP:8739384")
        self.assertEquals(trip.sections[2].Leg.Arrival.TripStopPlace.Name, "SAINT-QUENTIN EN YVELINES")
        self.assertEquals(trip.sections[2].Leg.Arrival.TripStopPlace.Position.Latitude, "48.78739")
        self.assertEquals(trip.sections[2].Leg.Arrival.TripStopPlace.Position.Longitude, "2.044622")
        self.assertEquals(trip.sections[2].Leg.Duration, timedelta(0, 2 * 60))
        self.assertEquals(trip.sections[2].Leg.SelfDriveMode, "foot")

        self.assertEquals(trip.sections[5].PartialTripId, "section_16_0")
        self.assertEquals(trip.sections[5].PTRide.Line.Name, "J")
        self.assertEquals(trip.sections[5].PTRide.Line.Number, "J")
        self.assertEquals(trip.sections[5].PTRide.Line.PublishedName, "J")
        self.assertEquals(trip.sections[5].PTRide.Line.RegistrationNumber, "line:DUA:800854041")
        self.assertEquals(trip.sections[5].PTRide.PTNetwork.id, "network:DUA854")
        self.assertEquals(trip.sections[5].PTRide.PTNetwork.Name, "Paris St Lazare")
        self.assertEquals(trip.sections[5].PTRide.PTNetwork.RegistrationNumber, "network:DUA854")
        self.assertEquals(trip.sections[5].PTRide.PublicTransportMode, "URBANRAIL")
        self.assertEquals(trip.sections[5].PTRide.Departure.TripStopPlace.id, "stop_point:DUA:SP:8738400")
        self.assertEquals(trip.sections[5].PTRide.Departure.TripStopPlace.Name, "PARIS SAINT-LAZARE")
        self.assertEquals(trip.sections[5].PTRide.Departure.TripStopPlace.Position.Latitude, "48.875442")
        self.assertEquals(trip.sections[5].PTRide.Departure.TripStopPlace.Position.Longitude, "2.324806")
        self.assertEquals(trip.sections[5].PTRide.Arrival.TripStopPlace.id, "stop_point:DUA:SP:8738664")
        self.assertEquals(trip.sections[5].PTRide.Arrival.TripStopPlace.Name, "VILLENNES SUR SEINE")
        self.assertEquals(trip.sections[5].PTRide.Arrival.TripStopPlace.Position.Latitude, "48.939487")
        self.assertEquals(trip.sections[5].PTRide.Arrival.TripStopPlace.Position.Longitude, "1.999604")
        self.assertEquals(trip.sections[5].PTRide.Duration, timedelta(0, 25 * 60))
        self.assertEquals(trip.sections[5].PTRide.StopHeadSign, "MALA")
        self.assertEquals(len(trip.sections[5].PTRide.steps), 2)

        self.assertEquals(trip.sections[6].PartialTripId, "section_17_0")
        self.assertEquals(trip.sections[6].PTRide, None)
        self.assertEquals(trip.sections[6].Leg.Departure.TripStopPlace.id, "stop_point:DUA:SP:8738664")
        self.assertEquals(trip.sections[6].Leg.Departure.TripStopPlace.Name, "VILLENNES SUR SEINE")
        self.assertEquals(trip.sections[6].Leg.Departure.TripStopPlace.Position.Latitude, "48.939487")
        self.assertEquals(trip.sections[6].Leg.Departure.TripStopPlace.Position.Longitude, "1.999604")
        self.assertEquals(trip.sections[6].Leg.Arrival.TripStopPlace.id, "stop_area:DUA:SA:8738664")
        self.assertEquals(trip.sections[6].Leg.Arrival.TripStopPlace.Name, "VILLENNES SUR SEINE (Villennes-sur-Seine)")
        self.assertEquals(trip.sections[6].Leg.Arrival.TripStopPlace.Position.Latitude, "48.939491")
        self.assertEquals(trip.sections[6].Leg.Arrival.TripStopPlace.Position.Longitude, "1.999496")
        self.assertEquals(trip.sections[6].Leg.Duration, timedelta(0, 0))
        self.assertEquals(trip.sections[6].Leg.SelfDriveMode, "foot")


class VirtualMisApi(navitia.MisApi):
    def __init__(self):
        super(VirtualMisApi, self).__init__(None)
        self._api_url = "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test/"
        self.urls = []
        self.json_data = []

    def _send_request(self, url, json_data=None):
        self.last_url = url
        self.last_json_data = json.dumps(json_data) if json_data else None
        self.urls.append(url)
        self.json_data.append(self.last_json_data)
        dump_filename = "navidump" + str(hash(url)) + \
                        ("8570956" if json_data is None else str(hash(json.dumps(json_data)))) + ".json"
        print dump_filename
        f = open(TEST_DIR + dump_filename)
        content = "".join(f.readlines())
        f.close()
        return None, content


class TestNavitiaMisApi(unittest.TestCase):
    def setUp(self):
        self.mis_api = VirtualMisApi()

    def tearDown(self):
        self.mis_api = None

    def test_capabilities(self):
        capabilities = self.mis_api.get_capabilities()
        self.assertTrue(capabilities.multiple_starts_and_arrivals)
        self.assertTrue(capabilities.geographic_position_compliant)
        self.assertTrue(capabilities.public_transport_modes == [TransportModeEnum.ALL])

    def test_journeys_request(self):
        params = {'from': "EXT:FROM:CODE", 'datetime_represents': "departure",
                  'datetime': datetime(2014, 10, 15, 12, 13)}
        self.mis_api._journeys_request(params)
        self.assertEquals(self.mis_api.last_url,
                          "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//journeys?"
                          "datetime_represents=departure&from=EXT%3AFROM%3ACODE&datetime=2014-10-15+12%3A13%3A00")
        self.assertTrue(not self.mis_api.last_json_data)

    def test_get_stops_by_mode(self):
        stops = self.mis_api._get_stops_by_mode("physical_mode:Train")
        self.assertEquals(len(self.mis_api.urls), 2)
        self.assertEquals(self.mis_api.urls[0],
                          "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//physical_modes"
                          "/physical_mode:Train/stop_areas?count=1000")
        self.assertEquals(self.mis_api.urls[1],
                          "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/transilien/stop_areas?"
                          "start_page=1&count=1000")
        self.assertEquals(len(stops), 42)

        # print stops[41].id
        #print len(stops[0].quays)
        #print stops[41].quays[0].id
        #print stops[41].quays[0].Name
        #print stops[41].quays[0].PrivateCode
        #print stops[41].quays[0].Centroid.Location.Longitude
        #print stops[41].quays[0].Centroid.Location.Latitude

        self.assertEquals(stops[0].id, "stop_area:DUA:SA:8798336")
        self.assertEquals(len(stops[0].quays), 1)
        self.assertEquals(stops[0].quays[0].id, "stop_area:DUA:SA:8798336")
        self.assertEquals(stops[0].quays[0].Name, "PLACE GOUNOT")
        self.assertEquals(stops[0].quays[0].PrivateCode, "stop_area:DUA:SA:8798336")
        self.assertEquals(stops[0].quays[0].Centroid.Location.Longitude, "2.411291")
        self.assertEquals(stops[0].quays[0].Centroid.Location.Latitude, "48.73715")

        self.assertEquals(stops[41].id, "stop_area:DUA:SA:59837")
        self.assertEquals(len(stops[0].quays), 1)
        self.assertEquals(stops[41].quays[0].id, "stop_area:DUA:SA:59837")
        self.assertEquals(stops[41].quays[0].Name, "CAROLINE AIGLE (ORLYFRET)")
        self.assertEquals(stops[41].quays[0].PrivateCode, "stop_area:DUA:SA:59837")
        self.assertEquals(stops[41].quays[0].Centroid.Location.Longitude, "2.36971")
        self.assertEquals(stops[41].quays[0].Centroid.Location.Latitude, "48.738854")

    def test_clean_up_trip_response(self):
        # clean_up_trip_response (should be tested but redundant with tests below)
        pass

    def test_get_itinerary(self):
        departure_time = datetime(2014, 11, 13, 15, 12, 35)
        arrival_time = ""
        departures = []
        departure = LocationContextType()
        departure.Position = LocationStructure(Latitude="48.858108", Longitude="2.348294")
        departure.AccessTime = timedelta(minutes=15)
        departure.PlaceTypeId = None
        departures.append(departure)
        arrivals = []
        arrival = LocationContextType()
        arrival.Position = None
        arrival.AccessTime = timedelta(minutes=15)
        arrival.PlaceTypeId = "stop_area:DUA:SA:8768666"
        arrivals.append(arrival)
        algorithm = AlgorithmEnum.CLASSIC
        modes = [TransportModeEnum.ALL]
        self_drive_conditions = []
        accessibility_constraint = False
        language = ""
        options = []
        response = ItineraryResponseType()
        response.DetailedTrip = self.mis_api.get_itinerary(
            departures,
            arrivals,
            departure_time,
            arrival_time,
            algorithm,
            modes,
            self_drive_conditions,
            accessibility_constraint,
            language,
            options)

        # print self.mis_api.urls
        self.assertEquals(len(self.mis_api.urls), 1)
        self.assertEquals(self.mis_api.urls[0],
                          "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//journeys?"
                          "from=2.348294%3B48.858108&to=stop_area%3ADUA%3ASA%3A8768666&datetime=20141113T152735"
                          "&last_section_mode%5B%5D=walking&datetime_represents=departure"
                          "&first_section_mode%5B%5D=walking")

        self.assertEquals(response.DetailedTrip.Departure.DateTime, datetime(2014, 11, 13, 16, 17, 40))
        self.assertEquals(response.DetailedTrip.Arrival.DateTime, datetime(2014, 11, 13, 19, 22, 00))
        self.assertEquals(response.DetailedTrip.Duration, timedelta(0, 3 * 3600 + 4 * 60 + 20))
        self.assertEquals(response.DetailedTrip.InterchangeNumber, 2)

        self.assertEquals(len(response.DetailedTrip.sections), 6)
        self.assertEquals(response.DetailedTrip.sections[0].PartialTripId, "section_6_0")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.Name, "CHATELET LES HALLES")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.Position.Latitude, "48.861822")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.Position.Longitude, "2.347013")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.TypeOfPlaceRef, "STOP_PLACE")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.TripStopPlace.id, "stop_point:DUA:SP:8775860")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Arrival.DateTime, datetime(2014, 11, 13, 16, 25, 46))
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.Name, " (Paris)")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.Position.Latitude,
                          "48.85807101538462")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.Position.Longitude,
                          "2.3483587230769243")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.TypeOfPlaceRef, "ADDRESS")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.TripStopPlace.id,
                          "2.3483587230769243;48.85807101538462")
        self.assertEquals(response.DetailedTrip.sections[0].Leg.Departure.DateTime, datetime(2014, 11, 13, 16, 17, 40))
        self.assertEquals(response.DetailedTrip.sections[1].PartialTripId, "section_7_0")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.Name, "PARIS GARE DE LYON")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.Position.Latitude, "48.844139")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.Position.Longitude, "2.37326")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.TypeOfPlaceRef, "STOP_PLACE")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.TripStopPlace.id,
                          "stop_point:DUA:SP:8775858")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Arrival.DateTime, datetime(2014, 11, 13, 16, 29))
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.Name, "CHATELET LES HALLES")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.Position.Latitude,
                          "48.861822")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.Position.Longitude,
                          "2.347013")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.TypeOfPlaceRef, "STOP_PLACE")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.TripStopPlace.id,
                          "stop_point:DUA:SP:8775860")
        self.assertEquals(response.DetailedTrip.sections[1].PTRide.Departure.DateTime, datetime(2014, 11, 13, 16, 26))
        self.assertEquals(response.DetailedTrip.sections[5].PartialTripId, "section_13_0")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.Name, "PARIS BERCY (Paris)")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.Position.Latitude, "48.838388")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.Position.Longitude, "2.38232")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.TypeOfPlaceRef, "STOP_PLACE")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.TripStopPlace.id, "stop_area:DUA:SA:8768666")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Arrival.DateTime, datetime(2014, 11, 13, 19, 22))
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.Name, "GARE DE BERCY")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.Position.Latitude, "48.839081")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.Position.Longitude, "2.383028")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.TypeOfPlaceRef, "STOP_PLACE")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.CityName, "Paris")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.TripStopPlace.id, "stop_point:DUA:SP:8768666")
        self.assertEquals(response.DetailedTrip.sections[5].Leg.Departure.DateTime, datetime(2014, 11, 13, 19, 22))
        # print json.dumps(marshal(response, itinerary_response_type))

    def test_get_emulated_summed_up_itineraries(self):
        # get_emulated_summed_up_itineraries (should be tested)
        pass

    def test_get_hardcoded_summed_up_itineraries(self):
        departure_time = datetime(2014, 10, 18, 11, 20, 16)
        arrival_time = ""
        departures = []
        departure = LocationContextType()
        departure.Position = LocationStructure(Latitude="48.8594808", Longitude="2.3467106")
        departure.AccessTime = timedelta(minutes=0)
        departure.PlaceTypeId = None
        departures.append(departure)
        arrivals = []
        uris = ["stop_area:DUA:SA:8768666",
                "stop_area:DUA:SA:8768603",
                "stop_area:DUA:SA:8711300",
                "stop_area:DUA:SA:8738400",
                "stop_area:DUA:SA:8739300",
                "stop_area:DUA:SA:8754702",
                "stop_area:DUA:SA:8738162",
                "stop_area:DUA:SA:8711613",
                "stop_area:DUA:SA:8768412",
                "stop_area:DUA:SA:8798650",
                "stop_area:DUA:SA:8738150",
                "stop_area:DUA:SA:8727103",
                "stop_area:DUA:SA:8741560"]
        for uri in uris:
            arrival = LocationContextType()
            arrival.Position = None
            arrival.AccessTime = timedelta(minutes=0)
            arrival.PlaceTypeId = uri
            arrivals.append(arrival)
        algorithm = AlgorithmEnum.CLASSIC
        modes = [TransportModeEnum.ALL]
        self_drive_conditions = []
        accessibility_constraint = False
        language = ""
        options = []
        response = SummedUpItinerariesResponseType()
        response.summedUpTrips = self.mis_api.get_hardcoded_summed_up_itineraries(
            departures,
            arrivals,
            departure_time,
            arrival_time,
            algorithm,
            modes,
            self_drive_conditions,
            accessibility_constraint,
            language,
            options)

        # print self.mis_api.urls
        # print self.mis_api.json_data
        self.assertEquals(len(self.mis_api.urls), 1)
        self.assertEquals(self.mis_api.urls[0], "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//journeys")
        d = "{\"from\": [{\"uri\": \"2.3467106;48.8594808\", \"access_duration\": 0}]" \
            ", \"to\": [{\"uri\": \"stop_area:DUA:SA:8768666\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8768603\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8711300\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8738400\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8739300\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8754702\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8738162\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8711613\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8768412\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8798650\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8738150\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8727103\", \"access_duration\": 0}" \
            ", {\"uri\": \"stop_area:DUA:SA:8741560\", \"access_duration\": 0}]" \
            ", \"datetime\": \"20141018T112016\", \"last_section_mode[]\": \"walking\"" \
            ", \"datetime_represents\": \"departure\", \"details\": \"false\"" \
            ", \"forbidden_uris[]\": [], \"first_section_mode[]\": \"walking\"}"
        self.assertEquals(self.mis_api.json_data[0], d)

        self.assertEquals(len(response.summedUpTrips), 13)
        self.assertEquals(response.summedUpTrips[0].Departure.TripStopPlace.id, "stop_point:DUA:SP:59410")
        self.assertEquals(response.summedUpTrips[0].Departure.DateTime, datetime(2014, 10, 18, 11, 23))
        self.assertEquals(response.summedUpTrips[0].Arrival.TripStopPlace.id, "stop_area:DUA:SA:8768666")
        self.assertEquals(response.summedUpTrips[0].Arrival.DateTime, datetime(2014, 10, 18, 11, 28))
        self.assertEquals(response.summedUpTrips[1].Departure.TripStopPlace.id, "stop_point:DUA:SP:59644")
        self.assertEquals(response.summedUpTrips[1].Departure.DateTime, datetime(2014, 10, 18, 11, 23))
        self.assertEquals(response.summedUpTrips[1].Arrival.TripStopPlace.id, "stop_area:DUA:SA:8768603")
        self.assertEquals(response.summedUpTrips[1].Arrival.DateTime, datetime(2014, 10, 18, 11, 26))
        self.assertEquals(response.summedUpTrips[11].Departure.TripStopPlace.id, "stop_point:DUA:SP:59627")
        self.assertEquals(response.summedUpTrips[11].Departure.DateTime, datetime(2014, 10, 18, 11, 25))
        self.assertEquals(response.summedUpTrips[11].Arrival.TripStopPlace.id, "stop_area:DUA:SA:8727103")
        self.assertEquals(response.summedUpTrips[11].Arrival.DateTime, datetime(2014, 10, 18, 11, 33))
        self.assertEquals(response.summedUpTrips[12].Departure.TripStopPlace.id, "stop_point:DUA:SP:59644")
        self.assertEquals(response.summedUpTrips[12].Departure.DateTime, datetime(2014, 10, 18, 11, 23))
        self.assertEquals(response.summedUpTrips[12].Arrival.TripStopPlace.id, "stop_area:DUA:SA:8741560")
        self.assertEquals(response.summedUpTrips[12].Arrival.DateTime, datetime(2014, 10, 18, 13, 9))
        # print json.dumps(marshal(response, summed_up_itineraries_response_type))


if __name__ == '__main__':
    unittest.main()
