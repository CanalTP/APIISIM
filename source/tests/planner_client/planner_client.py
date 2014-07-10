from websocket import create_connection
from common import AlgorithmEnum, TransportModeEnum, SelfDriveModeEnum
from common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
                             PlanTripCancellationRequest
from common.marshalling import *
from random import randint
import datetime, json, logging, sys
from datetime import timedelta
from time import sleep
from jsonschema import validate, Draft4Validator, ValidationError

datetime_pattern = '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'
duration_pattern = 'P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?' \
                   '(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?' \
                   '(?:(?P<seconds>\d+)S)?)?'

ending_search_format = {'type': 'object',
        'properties': {
            'RequestId': {'type': 'string'},
            'Status': {'enum': ['0', '1', '2']},
            'MaxComposedTripSearched': {'type': 'integer'},
            'ExistenceNotificationsSent': {'type': 'integer'},
            'NotificationsSent': {'type': 'integer'},
            'Runtime': {'type': 'string', 'pattern': duration_pattern},
        },
        'required': ['RequestId', 'Status', 'MaxComposedTripSearched',
                     'ExistenceNotificationsSent', 'NotificationsSent', 'Runtime']
}

starting_search_format = {'type': 'object',
        'properties': {
            'RequestId': {'type': 'string'},
            'Status': {'enum': ['0', '1', '2']},
            'MaxComposedTripSearched': {'type': 'integer'},
        },
        'required': ['RequestId', 'MaxComposedTripSearched'],
}

error_format =  {'type': 'object',
        'properties': {
            'Field': {'type': 'string'},
            'Message': {'type': 'string'},
        },
        'required': ['Field', 'Message']
}

plan_trip_response_format = {'type': 'object',
        'properties': {
            'RequestId': {'type': 'string'},
            'Status': {'enum': ['0', '1', '2']},
            'errors': {'type' : 'array',
                       'items':[error_format]}
        },
        'required': ['RequestId', 'Status'],
}

location_structure_format = {'type': 'object',
        'properties': {
            'Longitude': {'type': 'number'},
            'Latitude': {'type': 'number'},
        },
        'required': ['Longitude', 'Latitude'],
}

location_point_format = {'type': 'object',
        'properties': {
            'PlaceTypeId': {'type': 'string'},
            'Position': location_structure_format,
        },
}

trip_stop_place_format = {'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'Position': location_structure_format,
            'Name': {'type': 'string'},
            'CityCode': {'type': 'string'},
            'CityName': {'type': 'string'},
            'POITypeName': {'type': 'string'},
            'TypeOfPlaceRef': {'type': 'string'},
        },
        'required': ['id', 'TypeOfPlaceRef'],
}

end_point_format = {'type': 'object',
        'properties': {
            'TripStopPlace': trip_stop_place_format,
            'DateTime': {'type': 'string', 'pattern': datetime_pattern},
        },
        'required': ['TripStopPlace', 'DateTime'],
}

provider_format = {'type': 'object',
        'properties': {
            'Name': {'type': 'string'},
            'Url': {'type': 'string'},
        },
        'required': ['Name'],
}

plan_trip_existence_notification_format = {'type': 'object',
        'properties': {
            'RequestId': {'type': 'string'},
            'Status': {'enum': ['0', '1', '2']},
            'RuntimeDuration': {'type': 'string', 'pattern': duration_pattern},
            'ComposedTripId': {'type': 'string'},
            'DepartureTime': {'type': 'string', 'pattern': datetime_pattern},
            'ArrivalTime': {'type': 'string', 'pattern': datetime_pattern},
            'Duration': {'type': 'string', 'pattern': duration_pattern},
            'Departure': location_point_format,
            'Arrival': location_point_format,
            'providers': {'type' : 'array',
                          'items':[provider_format]},
        },
        'required': ['RequestId', 'DepartureTime', 'ArrivalTime',
                     'Duration', 'Departure', 'Arrival', 'providers'],
}

step_end_point_format = {'type': 'object',
        'properties': {
            'TripStopPlace': trip_stop_place_format,
            'DateTime': {'type': 'string', 'pattern': datetime_pattern},
            'PassThrough': {'type': 'boolean'}
        },
        'required': ['TripStopPlace', 'DateTime'],
}

step_format = {'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'Departure': step_end_point_format,
            'Arrival': step_end_point_format,
            'Duration': {'type': 'string', 'pattern': duration_pattern},
            'Distance': {'type': 'integer'},
        },
        'required': ['id', 'Departure', 'Arrival', 'Duration'],
}

pt_ride_format = {'type': 'object',
        'properties': {
            'ptNetworkRef': {'type': 'string'},
            'lineRef': {'type': 'string'},
            'PublicTransportMode': {'enum': [x for x in TransportModeEnum.values()]},
            'Departure': end_point_format,
            'Arrival': end_point_format,
            'Duration': {'type': 'string', 'pattern': duration_pattern},
            'Distance': {'type': 'integer'},
            'steps': {'type' : 'array',
                      'items':[step_format]},
        },
        'required': ['ptNetworkRef', 'lineRef', 'PublicTransportMode', 'Departure'
                     'Arrival', 'Duration', 'steps'],
}

leg_format = {'type': 'object',
        'properties': {
            'SelfDriveMode': {'enum': [x for x in SelfDriveModeEnum.values()]},
            'Departure': end_point_format,
            'Arrival': end_point_format,
            'Duration': {'type': 'string', 'pattern': duration_pattern},
        },
        'required': ['SelfDriveMode', 'Departure', 'Arrival', 'Duration'],
}

section_format = {'type': 'object',
        'properties': {
            'PartialTripId': {'type': 'string'},
            'PTRide': pt_ride_format,
            'Leg': leg_format,
        },
        'required': ['PTRide', 'Leg'],
}

partial_trip_format = {'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'Provider': provider_format,
            'Distance': {'type': 'integer'},
            'Departure': end_point_format,
            'Arrival': end_point_format,
            'Duration': {'type': 'string', 'pattern': duration_pattern},
        },
        'required': ['id', 'Departure', 'Arrival', 'Duration', 'Provider'],
}

composed_trip_format = {'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'Departure': end_point_format,
            'Arrival': end_point_format,
            'Duration': {'type': 'string', 'pattern': duration_pattern},
            'Distance': {'type': 'integer'},
            'InterchangeNumber': {'type': 'integer'},
            'sections': {'type' : 'array',
                         'items':[section_format]},
            'partialTrips': {'type' : 'array',
                             'items':[partial_trip_format]},
        },
        'required': ['id', 'Departure', 'Arrival', 'Duration', 'sections',
                     'partialTrips'],
}

plan_trip_notification_response_format = {'type': 'object',
        'properties': {
            'RequestId': {'type': 'string'},
            'Status': {'enum': ['0', '1', '2']},
            'RuntimeDuration': {'type': 'string', 'pattern': duration_pattern},
            'ComposedTrip': {'type' : 'array',
                             'items':[composed_trip_format]},
        },
        'required': ['RequestId'],
}


def init_logging():
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)


def new_location(place_id, longitude, latitude):
    ret = LocationPointType()
    ret.AccessTime = timedelta(seconds=100)
    ret.PlaceTypeId = place_id
    l = LocationStructure()
    l.Longitude = longitude
    l.Latitude  = latitude
    ret.Position = l

    return ret


def new_request(departure, arrival):
    ret = PlanTripRequestType()

    ret.clientRequestId = "request_" + str(randint(0, 60000))
    ret.DepartureTime = datetime.datetime.now()
    ret.ArrivalTime = None
    ret.Departure = departure
    ret.Arrival = arrival

    ret.MaxTrips = 10
    ret.Algorithm = AlgorithmEnum.CLASSIC
    ret.modes = [TransportModeEnum.ALL]
    ret.selfDriveConditions = []
    ret.AccessibilityConstraint = False
    ret.Language = ""

    return ret


init_logging()

Draft4Validator.check_schema(ending_search_format)
Draft4Validator.check_schema(starting_search_format)
Draft4Validator.check_schema(error_format)
Draft4Validator.check_schema(plan_trip_response_format)
Draft4Validator.check_schema(location_structure_format)
Draft4Validator.check_schema(location_point_format)
Draft4Validator.check_schema(trip_stop_place_format)
Draft4Validator.check_schema(end_point_format)
Draft4Validator.check_schema(provider_format)
Draft4Validator.check_schema(plan_trip_existence_notification_format)
Draft4Validator.check_schema(step_end_point_format)
Draft4Validator.check_schema(step_format)
Draft4Validator.check_schema(pt_ride_format)
Draft4Validator.check_schema(leg_format)
Draft4Validator.check_schema(section_format)
Draft4Validator.check_schema(partial_trip_format)
Draft4Validator.check_schema(composed_trip_format)
Draft4Validator.check_schema(plan_trip_notification_response_format)

ws = create_connection("ws://localhost/planner")
req = new_request(
        # SAINT-MICHEL NOTRE DAME - transilien
        # "stop_area:DUA:SA:8778543"
        new_location(None, 2.345354, 48.853513),
        # Hulletteries - paysdelaloire
        # "stop_area:ANG:SA:1205"
        new_location(None, -0.721072, 47.465466))
ws.send(json.dumps({"PlanTripRequestType" : marshal(req, plan_trip_request_type)}))

# ws.send(json.dumps(
#             {"PlanTripCancellationRequest" :
#                     marshal(PlanTripCancellationRequest(RequestId=req.id),
#                             plan_trip_cancellation_request_type)}))
# logging.debug("Sent cancellation request")

while True:
    result =  ws.recv()
    logging.debug("Received: \n%s" % result)
    result = json.loads(result)
    if "EndingSearch" in result:
        validate(result["EndingSearch"], ending_search_format)
    elif "StartingSearch" in result:
        validate(result["StartingSearch"], starting_search_format)
    elif "PlanTripResponse" in result:
        validate(result["PlanTripResponse"], plan_trip_response_format)
    elif "PlanTripExistenceNotificationResponseType" in result:
        validate(result["PlanTripExistenceNotificationResponseType"],
                 plan_trip_existence_notification_format)
    elif "PlanTripNotificationResponseType" in result:
        validate(result["PlanTripNotificationResponseType"],
                 plan_trip_notification_response_format)


ws.close()
