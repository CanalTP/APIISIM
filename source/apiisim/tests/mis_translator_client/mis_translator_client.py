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
    def __init__(self):
        self.url = None
        self.h = httplib2.Http()
        self.headers = {'Content-type': 'application/json', 'Authorization': '77bca947-ca67-4f17-92a3-92b716fc3d82'}

    def send_request(self, data):
        resp, content = self.h.request(self.url, "POST", headers=self.headers, body=json.dumps(data))
        if resp.status != 200:
            print ("POST <%s> FAILED: %s" % (self.url, resp.status))

        print resp
        print content

        content = json.loads(content)
        if "SummedUpItinerariesResponseType" in content:
            validate(content["SummedUpItinerariesResponseType"], summed_up_itineraries_response_format)
        elif "ItineraryResponseType" in content:
            validate(content["ItineraryResponseType"], itinerary_response_format)


if __name__ == '__main__':
    client = MisTranslatorClient()

    base_url = "http://127.0.0.1:5000/pays_de_la_loire/v0"
    departure_time = datetime.datetime.now().strftime(DATE_FORMAT)
    arrival_time = (datetime.datetime.now() + timedelta(hours=24)).strftime(DATE_FORMAT)

    # gare SNCF et routière Angers-St-Laud
    d1 = {"AccessTime": "PT2M",
          "Position": {"Latitude": 47.464722,
                       "Longitude": -0.558158},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87484006"}

    # gare de Savenay
    d2 = {"AccessTime": "PT5M",
          "Position": {"Latitude": 47.358562,
                       "Longitude": -1.951025},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87481838"}

    # Camping de Bouchemaine
    d3 = {"AccessTime": "PT1M30S",
          "Position": {"Latitude": 47.419306,
                       "Longitude": -0.611521},
          "PlaceTypeId": "stop_area:ANG:SA:1306"}

    # Gare de rennes
    a1 = {"AccessTime": "PT6M40S",
          "Position": {"Latitude": 48.103516,
                       "Longitude": -1.67232},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87471003"}

    # Parking Des Ecoles
    a2 = {"AccessTime": "PT10M",
          "Position": {"Latitude": 47.081555,
                       "Longitude": -1.337921},
          "PlaceTypeId": "stop_area:C44:SA:333"}

    # gare de Bourgneuf-en-Retz
    a3 = {"AccessTime": "PT4M",
          "Position": {"Latitude": 47.046857,
                       "Longitude": -1.955269},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87481242"}

    # gare de Nancy-Ville
    a4 = {"AccessTime": "PT5M20S",
          "Position": {"Latitude": 48.689786,
                       "Longitude": 6.174279},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87141002"}

    # gare de Metz-Ville
    a5 = {"AccessTime": "PT10S",
          "Position": {"Latitude": 49.109789,
                       "Longitude": 6.177203},
          "PlaceTypeId": "stop_area:SNC:SA:SAOCE87192039"}

    client.url = base_url + "/itineraries.json"

    data1 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1],
                                                      "Arrival": a1},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.ALL]}}

    data2 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.ALL],
                                  "Algorithm": AlgorithmEnum.FASTEST}}

    data3 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.ALL],
                                  "Algorithm": AlgorithmEnum.SHORTEST}}

    data4 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "ArrivalTime": arrival_time,
                                  "modes": [TransportModeEnum.ALL]}}

    data5 = {"ItineraryRequest": {"multiArrivals": {"Departure": d2,
                                                    "Arrival": [a1, a2, a3]},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.ALL]}}

    data6 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "DepartureTime": departure_time,
                                  "Algorithm": AlgorithmEnum.MINCHANGES}}

    data7 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a1},
                                  "DepartureTime": departure_time,
                                  "selfDriveConditions": [{"TripPart": "DEPARTURE", "SelfDriveMode": "bicycle"},
                                                          {"TripPart": "ARRIVAL", "SelfDriveMode": "bicycle"}]
    }}

    data8 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.BUS]}}

    data9 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                      "Arrival": a2},
                                  "DepartureTime": departure_time,
                                  "modes": [TransportModeEnum.BUS, TransportModeEnum.TRAM]}}

    data10 = {"ItineraryRequest": {"multiDepartures": {"Departure": [d1, d2, d3],
                                                       "Arrival": a2},
                                   "DepartureTime": departure_time,
                                   "modes": [TransportModeEnum.METRO]}}

    client.send_request(data1)
    client.send_request(data2)
    client.send_request(data3)
    client.send_request(data4)
    client.send_request(data5)
    client.send_request(data6)
    client.send_request(data7)
    client.send_request(data8)
    client.send_request(data9)
    client.send_request(data10)

    client.url = base_url + "/summed_up_itineraries.json"

    data11 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a1, a4, a3],
                                             "DepartureTime": departure_time,
                                             "modes": [TransportModeEnum.ALL]}}

    data12 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a1, a4, a3],
                                             "ArrivalTime": arrival_time,
                                             "modes": [TransportModeEnum.ALL]}}

    data13 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a1, a4, a3],
                                             "DepartureTime": departure_time,
                                             "modes": [TransportModeEnum.ALL],
                                             "Algorithm": AlgorithmEnum.FASTEST}}

    data14 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a1, a4, a3],
                                             "DepartureTime": departure_time,
                                             "modes": [TransportModeEnum.ALL],
                                             "Algorithm": AlgorithmEnum.MINCHANGES}}

    data15 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a2],
                                             "DepartureTime": departure_time,
                                             "modes": [TransportModeEnum.BUS]}}

    data16 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a2, a3],
                                             "DepartureTime": departure_time,
                                             "modes": [TransportModeEnum.BUS]}}

    data17 = {"SummedUpItinerariesRequest": {"departures": [d1, d2, d3],
                                             "arrivals": [a2],
                                             "DepartureTime": departure_time,
                                             "options": ["DEPARTURE_ARRIVAL_OPTIMIZED"]}}

    client.send_request(data11)
    client.send_request(data12)
    client.send_request(data13)
    client.send_request(data14)
    client.send_request(data15)
    client.send_request(data16)
    client.send_request(data17)
