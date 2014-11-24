# -*- coding: utf8 -*-

import json
import datetime
from datetime import timedelta

import httplib2
from jsonschema import validate

from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.marshalling import DATE_FORMAT
from apiisim.common.formats import summed_up_itineraries_response_format, \
    itinerary_response_format


class MisTranslatorClient:
    def __init__(self, uri, token):
        self.uri = uri
        self.token = token
        self.h = httplib2.Http()
        self.headers = {'Content-type': 'application/json', 'Authorization': self.token}

    def send_request(self, api, data):
        url = self.uri + "/" + api
        resp, content = self.h.request(url, "POST", headers=self.headers, body=json.dumps(data))
        if resp.status != 200:
            print ("POST <%s> FAILED: %s" % (url, resp.status))

        print resp
        print content

        content = json.loads(content)
        if "SummedUpItinerariesResponseType" in content:
            validate(content["SummedUpItinerariesResponseType"], summed_up_itineraries_response_format)
        elif "ItineraryResponseType" in content:
            validate(content["ItineraryResponseType"], itinerary_response_format)


def no_code(gare):
    gare["PlaceTypeId"] = ""

    return gare


def gare_paris_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 49.108501,
                                                  "Longitude": 2.232531}, PlaceTypeId="stop_area:DUA:SA:51:641")


def gare_reims_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 49.256602,
                                                  "Longitude": 4.033091}, PlaceTypeId="stop_area:TAD:SA:51454")


def gare_juvisy_national(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.689470,
                                                  "Longitude": 2.383211}, PlaceTypeId="stop_area:SCF:SA:SAOCE87545244")


def gare_marseille_national(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 43.302734,
                                                  "Longitude": 5.380651}, PlaceTypeId="stop_area:SCF:SA:SAOCE87751008")


def gare_rennes_national(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.103516,
                                                  "Longitude": -1.672320}, PlaceTypeId="stop_area:SCF:SA:SAOCE87471003")


def gare_chartres_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.695623,
                                                  "Longitude": 2.179481}, PlaceTypeId="stop_area:DUA:SA:57:940")


def gare_chartres_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.448162,
                                                  "Longitude": 1.481009}, PlaceTypeId="stop_area:SNC:SA:SAOCE87394007")


def gare_etampes_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.436606,
                                                  "Longitude": 2.159388}, PlaceTypeId="stop_area:DUA:SA:8754513")


def gare_etampes_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.436587,
                                                  "Longitude": 2.159495}, PlaceTypeId="stop_area:SNC:SA:SAOCE87545137")


def gare_dourdan_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.533588,
                                                  "Longitude": 2.008998}, PlaceTypeId="stop_area:DUA:SA:8754552")


def gare_dourdan_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.533612,
                                                  "Longitude": 2.009701}, PlaceTypeId="stop_area:SNC:SA:SAOCE87545525")


def gare_limay_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.985849,
                                                  "Longitude": 1.750574}, PlaceTypeId="stop_area:DUA:SA:81:6594")


def gare_limay_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.984161,
                                                  "Longitude": 1.747123}, PlaceTypeId="stop_area:SNC:SA:SAOCE87381582")


def gare_melun_transilien(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.529989,
                                                  "Longitude": 2.651388}, PlaceTypeId="stop_area:DUA:SA:27:105")


def gare_melun_champagne(access_time="PT0S"):
    return dict(AccessTime=access_time, Position={"Latitude": 48.527597,
                                                  "Longitude": 2.655392}, PlaceTypeId="stop_area:SNC:SA:SAOCE87682005")


def test_journeys(client, req_time):
    time_field = (datetime.datetime.now() if not req_time else req_time).strftime(DATE_FORMAT)

    data = {"ItineraryRequest": {"multiDepartures": {"Departure": [gare_melun_transilien(), gare_paris_transilien(),
                                                                   gare_etampes_transilien()],
                                                     "Arrival": gare_chartres_transilien()},
                                 "DepartureTime": time_field,
                                 "modes": [TransportModeEnum.ALL]}}

    client.send_request("itineraries.json", data)

    data = {"ItineraryRequest": {"multiDepartures": {"Departure": [gare_dourdan_transilien(), gare_limay_transilien()],
                                                     "Arrival": no_code(gare_melun_transilien())},
                                 "DepartureTime": time_field,
                                 "Algorithm": AlgorithmEnum.MINCHANGES}}

    client.send_request("itineraries.json", data)

    data = {"ItineraryRequest": {"multiArrivals": {"Departure": gare_melun_transilien(),
                                                   "Arrival": [gare_dourdan_transilien(), gare_limay_transilien()]},
                                 "ArrivalTime": time_field,
                                 "Algorithm": AlgorithmEnum.MINCHANGES}}

    client.send_request("itineraries.json", data)


def test_nm_journeys(client, req_time=None):
    time_field = (datetime.datetime.now() if not req_time else req_time).strftime(DATE_FORMAT)

    data = {"SummedUpItinerariesRequest": {"departures": [gare_melun_transilien(), gare_limay_transilien()],
                                           "arrivals": [gare_chartres_transilien(), gare_etampes_transilien()],
                                           "DepartureTime": time_field,
                                           "modes": [TransportModeEnum.ALL]}}

    client.send_request("summed_up_itineraries.json", data)

    data = {"SummedUpItinerariesRequest": {"departures": [gare_melun_transilien(), gare_limay_transilien()],
                                           "arrivals": [gare_chartres_transilien(), gare_etampes_transilien()],
                                           "ArrivalTime": time_field,
                                           "modes": [TransportModeEnum.ALL]}}

    client.send_request("summed_up_itineraries.json", data)

    data = {"SummedUpItinerariesRequest": {"departures": [no_code(gare_melun_transilien())],
                                           "arrivals": [gare_chartres_transilien(), gare_etampes_transilien()],
                                           "DepartureTime": time_field,
                                           "modes": [TransportModeEnum.ALL]}}

    client.send_request("summed_up_itineraries.json", data)

    data = {"SummedUpItinerariesRequest": {"departures": [gare_melun_transilien(), gare_limay_transilien()],
                                           "arrivals": [no_code(gare_etampes_transilien())],
                                           "ArrivalTime": time_field,
                                           "modes": [TransportModeEnum.ALL]}}

    client.send_request("summed_up_itineraries.json", data)


if __name__ == '__main__':
    mis_client = MisTranslatorClient("http://127.0.0.1:5000/stub_transilien/v0",
                                     "f8a9befb-6bd9-4620-b942-b6b69a07487d")

    test_journeys(mis_client, datetime.datetime(2014, 11, 02, 12, 30))
    test_nm_journeys(mis_client, datetime.datetime(2014, 11, 02, 12, 30))
