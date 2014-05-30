# -*- coding: utf8 -*-

import json, httplib2, datetime
from mis_translator.fields import *
from mis_translator.mis_api.base import TransportModeEnum, AlgorithmEnum
from datetime import timedelta

def send_request(data):
    resp, content = h.request(url, "POST", headers=headers, body=json.dumps(data))
    if resp.status != 200:
        print ("POST <%s> FAILED: %s" % (url, resp.status))

    print resp
    print content

h = httplib2.Http(".cache")
base_url = "http://127.0.0.1:5000/navitia/v0/"

headers = {'Content-type': 'application/json'}

# Paris region
d1 = {ACCESS_DURATION : "10",
     POSITION : {LAT : 48.84556,
                 LONG : 2.373449},
     QUAY_ID : "stop_area:RTP:SA:1955"}

d2 = {ACCESS_DURATION : "5",
     POSITION : {LAT : 48.843414,
                 LONG : 2.364188},
     QUAY_ID : "stop_area:RTP:SA:1951"}

a1 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 48.883456,
                 LONG : 2.327375},
     QUAY_ID : "stop_area:RTP:SA:1795"}

a2 = {ACCESS_DURATION : "12",
      POSITION : {LAT : 48.897512, LONG : 2.329022},
      QUAY_ID : "stop_area:RTP:SA:2426"}

departures = []
arrivals = []
departures.append(d1)
departures.append(d2)
arrivals.append(a1)
arrivals.append(a2)

departure_time = datetime.datetime.now().strftime(TIME_FORMAT)
arrival_time = (datetime.datetime.now() + timedelta(hours=24)).strftime(TIME_FORMAT)
arrival_time_out_of_scope = (datetime.datetime.now() + timedelta(days=20000)).strftime(TIME_FORMAT)

url = base_url + "itineraries/"
data1 = {MULTI_DEPARTURES : {DEPARTURE : departures,
                            ARRIVAL   : a1},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.ALL]}

data2 = {MULTI_ARRIVALS : {DEPARTURE : d1,
                           ARRIVAL   : arrivals},
         ARRIVAL_TIME : arrival_time,
         "modes" : [TransportModeEnum.ALL]}

data2_error = {MULTI_ARRIVALS : {DEPARTURE : d1,
                           ARRIVAL   : arrivals},
         ARRIVAL_TIME : arrival_time_out_of_scope,
         "modes" : [TransportModeEnum.ALL]}

# send_request(data1)
# send_request(data2)
# send_request(data2_error)

url = base_url + "sumed_up_itineraries/"
data3 = {DEPARTURES : {DEPARTURE : departures},
         ARRIVALS : {ARRIVAL : arrivals},
         DEPARTURE_TIME : departure_time,
         "modes" : [TransportModeEnum.ALL]}

data4 = {DEPARTURES : {DEPARTURE : departures},
         ARRIVALS : {ARRIVAL : arrivals},
         ARRIVAL_TIME : arrival_time,
         "modes" : [TransportModeEnum.ALL]}

# send_request(data3)
# send_request(data4)

# gare SNCF et routière Angers-St-Laud
d3 = {ACCESS_DURATION : "10",
     POSITION : {LAT : 47.464722,
                 LONG : -0.558158},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87484006"}

# gare de Savenay
d4 = {ACCESS_DURATION : "10",
     POSITION : {LAT : 47.358562,
                 LONG : -1.951025},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87481838"}

# Camping de Bouchemaine
d5 = {ACCESS_DURATION : "10",
     POSITION : {LAT : 47.419306,
                 LONG : -0.611521},
     QUAY_ID : "stop_area:ANG:SA:1306"}

# Gare de rennes
a3 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 48.103516,
                 LONG : -1.67232},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87471003"}

# Parking Des Ecoles
a4 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 47.081555,
                 LONG : -1.337921},
     QUAY_ID : "stop_area:C44:SA:333"}

# gare de Bourgneuf-en-Retz
a5 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 47.046857,
                 LONG : -1.955269},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87481242"}

# gare de Nancy-Ville
a6 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 48.689786,
                 LONG : 6.174279},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87141002"}

# gare de Metz-Ville
a7 = {ACCESS_DURATION : "7",
     POSITION : {LAT : 49.109789,
                 LONG : 6.177203},
     QUAY_ID : "stop_area:SNC:SA:SAOCE87192039"}

# http://navitia2-ws.ctp.dev.canaltp.fr//v1/coverage/paysdelaloire/journeys?from=stop_area:SNC:SA:SAOCE87484006&to=stop_area:SNC:SA:SAOCE87471003&datetime=...
url = base_url + "itineraries/"
data5 = {MULTI_DEPARTURES : {DEPARTURE : [d3],
                            ARRIVAL   : a3},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.ALL]}

data6 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                            ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.ALL],
         "algorithm" : AlgorithmEnum.FASTEST}

data7 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                            ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.ALL],
         "algorithm" : AlgorithmEnum.SHORTEST}

data8 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                            ARRIVAL   : a4},
         ARRIVAL_TIME : arrival_time, 
         "modes" : [TransportModeEnum.ALL]}

data9 = {MULTI_ARRIVALS : {DEPARTURE : d4,
                            ARRIVAL   : [a3, a4, a5]},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.ALL]}

data10 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                              ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "algorithm" : AlgorithmEnum.MINCHANGES}

data11 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                              ARRIVAL   : a3},
         DEPARTURE_TIME : departure_time, 
         "selfDriveConditions" : [{"TripPart" : "DEPARTURE", "SelfDriveMode" : "BIKE"},
                                  {"TripPart" : "ARRIVAL", "SelfDriveMode" : "BIKE"}]
         }

data12 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                              ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.BUS]}


data13 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                              ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.BUS, TransportModeEnum.TRAM]}


data14 = {MULTI_DEPARTURES : {DEPARTURE : [d3, d4, d5],
                              ARRIVAL   : a4},
         DEPARTURE_TIME : departure_time, 
         "modes" : [TransportModeEnum.METRO]}

# send_request(data5)
# send_request(data6)
# send_request(data7)
# send_request(data8)
# send_request(data9)
# send_request(data10)
# send_request(data11)
send_request(data12)
send_request(data13)
send_request(data14)


url = base_url + "sumed_up_itineraries/"
data10 = {DEPARTURES : {DEPARTURE : [d3, d4, d5]},
          ARRIVALS : {ARRIVAL : [a3, a4, a5]},
          DEPARTURE_TIME : departure_time,
          "modes" : [TransportModeEnum.ALL]}

data11 = {DEPARTURES : {DEPARTURE : [d3, d4, d5]},
          ARRIVALS : {ARRIVAL : [a3, a4, a5]},
          ARRIVAL_TIME : arrival_time,
          "modes" : [TransportModeEnum.ALL]}

data12 = {DEPARTURES : {DEPARTURE : [d3, d4, d5]},
          ARRIVALS : {ARRIVAL : [a3, a4, a5]},
          DEPARTURE_TIME : departure_time,
          "modes" : [TransportModeEnum.ALL],
          "algorithm" : AlgorithmEnum.FASTEST}

data13 = {DEPARTURES : {DEPARTURE : [d3, d4, d5]},
          ARRIVALS : {ARRIVAL : [a3, a4, a5]},
          DEPARTURE_TIME : departure_time,
          "modes" : [TransportModeEnum.ALL],
          "algorithm" : AlgorithmEnum.MINCHANGES}

# send_request(data10)
# send_request(data11)
# send_request(data12)
# send_request(data13)
