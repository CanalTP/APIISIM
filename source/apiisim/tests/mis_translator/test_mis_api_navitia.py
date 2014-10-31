#!/usr/bin/python
# -*- encoding: utf8 -*-
import os, unittest
import json
from datetime import timedelta, datetime
from apiisim.common import TransportModeEnum
from apiisim.mis_translator.mis_api import navitia

TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"

class TestNavitia(unittest.TestCase):

    def setUp(self):
        dummy = 1

    def tearDown(self):
        dummy = 0

    def _json_from_file(self, filename):
        f = open(TEST_DIR + filename, "r")
        content = "".join(f.readlines())
        js = json.loads(content)
        f.close()
        return js

    def testParseEndPoint(self):
        endpoint = navitia.parse_end_point(self._json_from_file("endpoint1.json"))
        self.assertEquals(endpoint.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(endpoint.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(endpoint.TripStopPlace.CityCode, "admin:7444")
        self.assertEquals(endpoint.TripStopPlace.CityName, "Paris")
        self.assertEquals(endpoint.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(endpoint.TripStopPlace.Position.Longitude, "2.3468313805225653")

    def testParseStopTimes(self):
        steps = navitia.parse_stop_times(self._json_from_file("stoptimes1.json"))

        #print len(steps)
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

    def testJourneyToSummedUpTrip(self):
        trip = navitia.journey_to_summed_up_trip(self._json_from_file("journey1.json"))

        #print trip.InterchangeCount
        #print trip.Departure.TripStopPlace.id
        #print trip.Departure.TripStopPlace.Name
        #print trip.Departure.TripStopPlace.Position.Latitude
        #print trip.Departure.TripStopPlace.Position.Longitude
        #print trip.Arrival.TripStopPlace.id
        #print trip.Arrival.TripStopPlace.Name
        #print trip.Arrival.TripStopPlace.Position.Latitude
        #print trip.Arrival.TripStopPlace.Position.Longitude
        #print trip.Departure.DateTime
        #print trip.Arrival.DateTime
        #print trip.InterchangeDuration

        self.assertEquals(trip.InterchangeCount, 3)
        self.assertEquals(trip.Departure.TripStopPlace.id, "2.3468313805225653;48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Name, "9 Rue des Halles (Paris)")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Latitude, "48.859484964845606")
        self.assertEquals(trip.Departure.TripStopPlace.Position.Longitude, "2.3468313805225653")
        self.assertEquals(trip.Arrival.TripStopPlace.id, "stop_area:DUA:SA:8738664")
        self.assertEquals(trip.Arrival.TripStopPlace.Name, "VILLENNES SUR SEINE (Villennes-sur-Seine)")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Latitude, "48.939491")
        self.assertEquals(trip.Arrival.TripStopPlace.Position.Longitude, "1.999496")
        self.assertEquals(trip.Departure.DateTime, datetime(2014, 9, 30, 3, 49, 53))
        self.assertEquals(trip.Arrival.DateTime, datetime(2014, 9, 30, 6, 47))
        self.assertEquals(trip.InterchangeDuration, 1886)

    def testJourneyToStr(self):
        txt = navitia.journey_to_str(self._json_from_file("journey1.json"))
        self.assertEquals(txt, "<Journey> Departure: 20140930T034953 | Arrival: 20140930T064600 | Duration: 10567 | Nb_transfers: 3 | Type: best")

    def testJourneyToDetailedTrip(self):
        trip = navitia.journey_to_detailed_trip(self._json_from_file("journey1.json"))

        #print trip.Duration
        #print trip.Distance
        #print trip.Disrupted
        #print trip.InterchangeNumber
        #print trip.CarFootprint
        #print len(trip.sections)
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

        self.assertEquals(trip.Duration, timedelta(0, 2*3600+56*60+7))
        self.assertEquals(trip.Distance, 0)
        self.assertEquals(trip.Disrupted, False)
        self.assertEquals(trip.InterchangeNumber, 3)
        self.assertEquals(trip.CarFootprint, None)
        self.assertEquals(len(trip.sections), 7)

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
        self.assertEquals(trip.sections[0].Leg.Duration, timedelta(0, 2*60+26))
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
        self.assertEquals(trip.sections[2].Leg.Duration, timedelta(0, 2*60))
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
        self.assertEquals(trip.sections[5].PTRide.Duration, timedelta(0, 25*60))
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

    def _send_request(self, url, json_data = None):
        self.last_url = url
        self.last_json_data = json_data
        self.urls.append(url)
        self.json_data.append(json_data)
        dump_filename = "navidump" + str(hash(url)) + str(hash(json_data)) + ".json"
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

    def testCapabilities(self):
        capabilities = self.mis_api.get_capabilities()
        self.assertTrue(capabilities.multiple_starts_and_arrivals)
        self.assertTrue(capabilities.geographic_position_compliant)
        self.assertTrue(capabilities.public_transport_modes == [TransportModeEnum.ALL])

    def testJourneysRequest(self):
        params = {}
        params['from'] = "EXT:FROM:CODE"
        params['datetime_represents'] = "departure"
        params['datetime'] = datetime(2014, 10, 15, 12, 13)
        self.mis_api._journeys_request(params)
        self.assertEquals(self.mis_api.last_url, "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//journeys?datetime_represents=departure&from=EXT%3AFROM%3ACODE&datetime=2014-10-15+12%3A13%3A00")
        self.assertTrue(not self.mis_api.last_json_data)

    def testGetStopsByMode(self):
        stops = self.mis_api._get_stops_by_mode("physical_mode:Train")
        self.assertEquals(len(self.mis_api.urls), 2)
        self.assertEquals(self.mis_api.urls[0], "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/test//physical_modes/physical_mode:Train/stop_areas?count=1000")
        self.assertEquals(self.mis_api.urls[1], "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/transilien/stop_areas?start_page=1&count=1000")
        self.assertEquals(len(stops), 42)

        #print stops[41].id
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


if __name__ == '__main__':
    unittest.main()
