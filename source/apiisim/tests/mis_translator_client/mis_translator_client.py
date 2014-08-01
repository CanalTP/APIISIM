# -*- coding: utf8 -*-

import json, httplib2, datetime
from datetime import timedelta
from apiisim.common import AlgorithmEnum, TransportModeEnum, StatusCodeEnum
from apiisim.common.marshalling import DATE_FORMAT
from apiisim.common.formats import summed_up_itineraries_response_format, \
                                   itinerary_response_format
from jsonschema import validate, Draft4Validator, ValidationError


def send_request(data):
    resp, content = h.request(url, "POST", headers=headers, body=json.dumps(data))
    if resp.status != 200:
        print ("POST <%s> FAILED: %s" % (url, resp.status))

    print resp
    print content

    content = json.loads(content)
    if "SummedUpItinerariesResponseType" in content:
        validate(content["SummedUpItinerariesResponseType"], summed_up_itineraries_response_format)
    elif "ItineraryResponseType" in content:
        validate(content["ItineraryResponseType"], itinerary_response_format)


h = httplib2.Http(".cache")
base_url = "http://127.0.0.1:5000/navitia/v0"

headers = {'Content-type': 'application/json',
           'Authorization' : '77bca947-ca67-4f17-92a3-92b716fc3d82'}

################################################################################
# Paris region ("http://api.navitia.io/v1/coverage/paris")
d1 = {"AccessTime" : "PT1M40S",
     "Position" : {"Latitude" : 48.84556,
                   "Longitude" : 2.373449},
     "PlaceTypeId" : "stop_area:RTP:SA:1955"}

d2 = {"AccessTime" : "PT50S",
     "Position" : {"Latitude" : 48.843414,
                   "Longitude" : 2.364188},
     "PlaceTypeId" : "stop_area:RTP:SA:1951"}

a1 = {"AccessTime" : "PT1M10S",
     "Position" : {"Latitude" : 48.883456,
                   "Longitude" : 2.327375},
     "PlaceTypeId" : "stop_area:RTP:SA:1795"}

a2 = {"AccessTime" : "PT2M",
      "Position" : {"Latitude" : 48.897512, "Longitude" : 2.329022},
      "PlaceTypeId" : "stop_area:RTP:SA:2426"}

departures = []
arrivals = []
departures.append(d1)
departures.append(d2)
arrivals.append(a1)
arrivals.append(a2)

departure_time = datetime.datetime.now().strftime(DATE_FORMAT)
arrival_time = (datetime.datetime.now() + timedelta(hours=24)).strftime(DATE_FORMAT)
arrival_time_out_of_scope = (datetime.datetime.now() + timedelta(days=20000)).strftime(DATE_FORMAT)

url = base_url + "/itineraries"
data1 = {"multiDepartures" : {"Departure" : departures,
                              "Arrival"   : a1},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL]}

data2 = {"multiArrivals" : {"Departure" : d1,
                            "Arrival"   : arrivals},
         "ArrivalTime" : arrival_time,
         "modes" : [TransportModeEnum.ALL]}

data2_error = {"multiArrivals" : {"Departure" : d1,
                                  "Arrival"   : arrivals},
         "ArrivalTime" : arrival_time_out_of_scope,
         "modes" : [TransportModeEnum.ALL]}

# send_request(data1)
# send_request(data2)
# send_request(data2_error)

url = base_url + "/summed_up_itineraries"
data3 = {"Departures" : departures,
         "Arrivals" : arrivals,
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL]}

data4 = {"Departures" : departures,
         "Arrivals" : arrivals,
         "ArrivalTime" : arrival_time,
         "modes" : [TransportModeEnum.ALL]}

# send_request(data3)
# send_request(data4)


################################################################################
# http://navitia2-ws.ctp.dev.canaltp.fr//v1/coverage/paysdelaloire/
# gare SNCF et routière Angers-St-Laud
d1 = {"AccessTime" : "PT2M",
      "Position" : {"Latitude" : 47.464722,
                    "Longitude" : -0.558158},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87484006"}

# gare de Savenay
d2 = {"AccessTime" : "PT5M",
      "Position" : {"Latitude" : 47.358562,
                    "Longitude" : -1.951025},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87481838"}

# Camping de Bouchemaine
d3 = {"AccessTime" : "PT1M30S",
      "Position" : {"Latitude" : 47.419306,
                    "Longitude" : -0.611521},
      "PlaceTypeId" : "stop_area:ANG:SA:1306"}

# Gare de rennes
a1 = {"AccessTime" : "PT6M40S",
      "Position" : {"Latitude" : 48.103516,
                    "Longitude" : -1.67232},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87471003"}

# Parking Des Ecoles
a2 = {"AccessTime" : "PT10M",
      "Position" : {"Latitude" : 47.081555,
                    "Longitude" : -1.337921},
      "PlaceTypeId" : "stop_area:C44:SA:333"}

# gare de Bourgneuf-en-Retz
a3 = {"AccessTime" : "PT4M",
      "Position" : {"Latitude" : 47.046857,
                    "Longitude" : -1.955269},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87481242"}

# gare de Nancy-Ville
a4 = {"AccessTime" : "PT5M20S",
      "Position" : {"Latitude" : 48.689786,
                    "Longitude" : 6.174279},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87141002"}

# gare de Metz-Ville
a5 = {"AccessTime" : "PT10S",
      "Position" : {"Latitude" : 49.109789,
                    "Longitude" : 6.177203},
      "PlaceTypeId" : "stop_area:SNC:SA:SAOCE87192039"}

# http://navitia2-ws.ctp.dev.canaltp.fr//v1/coverage/paysdelaloire/
# journeys?from=stop_area:SNC:SA:SAOCE87484006&to=stop_area:SNC:SA:SAOCE87471003
# &datetime=...
url = base_url + "/itineraries"
data1 = {"multiDepartures" : {"Departure" : [d1],
                              "Arrival"   : a1},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL]}

data2 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL],
         "Algorithm" : AlgorithmEnum.FASTEST}

data3 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL],
         "Algorithm" : AlgorithmEnum.SHORTEST}

data4 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "ArrivalTime" : arrival_time,
         "modes" : [TransportModeEnum.ALL]}

data5 = {"multiArrivals" : {"Departure" : d2,
                            "Arrival"   : [a1, a2, a3]},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.ALL]}

data6 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "Algorithm" : AlgorithmEnum.MINCHANGES}

data7 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a1},
         "DepartureTime" : departure_time,
         "selfDriveConditions" : [{"TripPart" : "DEPARTURE", "SelfDriveMode" : "BIKE"},
                                  {"TripPart" : "ARRIVAL", "SelfDriveMode" : "BIKE"}]
         }

data8 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.BUS]}


data9 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                              "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.BUS, TransportModeEnum.TRAM]}


data10 = {"multiDepartures" : {"Departure" : [d1, d2, d3],
                               "Arrival"   : a2},
         "DepartureTime" : departure_time,
         "modes" : [TransportModeEnum.METRO]}

send_request(data1)
send_request(data2)
send_request(data3)
send_request(data4)
send_request(data5)
send_request(data6)
send_request(data7)
send_request(data8)
send_request(data9)
send_request(data10)


url = base_url + "/summed_up_itineraries"
data11 = {"departures" : [d1, d2, d3],
          "arrivals" : [a1, a4, a3],
          "DepartureTime" : departure_time,
          "modes" : [TransportModeEnum.ALL]}

data12 = {"departures" : [d1, d2, d3],
          "arrivals" : [a1, a4, a3],
          "ArrivalTime" : arrival_time,
          "modes" : [TransportModeEnum.ALL]}

data13 = {"departures" : [d1, d2, d3],
          "arrivals" : [a1, a4, a3],
          "DepartureTime" : departure_time,
          "modes" : [TransportModeEnum.ALL],
          "Algorithm" : AlgorithmEnum.FASTEST}

data14 = {"departures" : [d1, d2, d3],
          "arrivals" : [a1, a4, a3],
          "DepartureTime" : departure_time,
          "modes" : [TransportModeEnum.ALL],
          "Algorithm" : AlgorithmEnum.MINCHANGES}

data15 = {"departures" : [d1, d2, d3],
          "arrivals" :   [a2],
          "DepartureTime" : departure_time,
          "modes" : [TransportModeEnum.BUS]}

data16 = {"departures" : [d1, d2, d3],
          "arrivals" :   [a2, a3],
          "DepartureTime" : departure_time,
          "modes" : [TransportModeEnum.BUS]}

data17 = {"departures" : [d1, d2, d3],
          "arrivals" :   [a2],
          "DepartureTime" : departure_time,
          "options" : ["DEPARTURE_ARRIVAL_OPTIMIZED"]
          }

send_request(data11)
send_request(data12)
send_request(data13)
send_request(data14)
send_request(data15)
send_request(data16)
send_request(data17)
