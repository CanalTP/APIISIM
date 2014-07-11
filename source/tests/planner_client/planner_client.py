from websocket import create_connection
from common import AlgorithmEnum, TransportModeEnum
from common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
                             PlanTripCancellationRequest
from common.marshalling import *
from common.formats import *
from random import randint
import datetime, json, logging, sys
from datetime import timedelta
from time import sleep
from jsonschema import validate, Draft4Validator, ValidationError


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
