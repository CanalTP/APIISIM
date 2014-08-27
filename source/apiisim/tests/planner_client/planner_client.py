# -*- coding: utf8 -*-

from websocket import create_connection
from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
                                     PlanTripCancellationRequest, modesType, \
                                     selfDriveConditionsType, SelfDriveConditionType
from apiisim.common.marshalling import marshal, plan_trip_request_type
from apiisim.common import formats
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
    ret.modes = modesType(Mode=[TransportModeEnum.ALL])
    ret.selfDriveConditions = None
    # ret.selfDriveConditions = selfDriveConditionsType(SelfDriveCondition= \
    #     [SelfDriveConditionType(TripPart="DEPARTURE",
    #                             SelfDriveMode="foot")])
    ret.AccessibilityConstraint = False
    ret.Language = ""

    return ret


def receive_msg(connection):
    ret =  connection.recv()
    logging.debug("Received: \n%s" % ret)
    ret = json.loads(ret)

    return ret


init_logging()

Draft4Validator.check_schema(formats.ending_search_format)
Draft4Validator.check_schema(formats.starting_search_format)
Draft4Validator.check_schema(formats.error_format)
Draft4Validator.check_schema(formats.plan_trip_response_format)
Draft4Validator.check_schema(formats.location_structure_format)
Draft4Validator.check_schema(formats.location_point_format)
Draft4Validator.check_schema(formats.trip_stop_place_format)
Draft4Validator.check_schema(formats.end_point_format)
Draft4Validator.check_schema(formats.provider_format)
Draft4Validator.check_schema(formats.plan_trip_existence_notification_format)
Draft4Validator.check_schema(formats.step_end_point_format)
Draft4Validator.check_schema(formats.step_format)
Draft4Validator.check_schema(formats.pt_ride_format)
Draft4Validator.check_schema(formats.leg_format)
Draft4Validator.check_schema(formats.section_format)
Draft4Validator.check_schema(formats.partial_trip_format)
Draft4Validator.check_schema(formats.composed_trip_format)
Draft4Validator.check_schema(formats.plan_trip_notification_response_format)

ws = create_connection("ws://localhost/planner")

req = new_request(
        # SAINT-MICHEL NOTRE DAME - transilien
        # "stop_area:DUA:SA:8778543"
        new_location(None, 2.345354, 48.853513),
        # Hulletteries - paysdelaloire
        # "stop_area:ANG:SA:1205"
        new_location(None, -0.721072, 47.465466))
ws.send(json.dumps({"PlanTripRequestType" : marshal(req, plan_trip_request_type)}))

msg = receive_msg(ws)
validate(msg["PlanTripResponse"], formats.plan_trip_response_format)
msg = receive_msg(ws)
validate(msg["StartingSearch"], formats.starting_search_format)
while True:
    msg = receive_msg(ws)
    if "PlanTripExistenceNotificationResponseType" in msg:
        validate(msg["PlanTripExistenceNotificationResponseType"],
                 formats.plan_trip_existence_notification_format)
    elif "PlanTripNotificationResponseType" in msg:
        validate(msg["PlanTripNotificationResponseType"],
                 formats.plan_trip_notification_response_format)
    elif "EndingSearch" in msg:
        validate(msg["EndingSearch"], formats.ending_search_format)
        ws.close()
        break
    else:
        raise Exception("FAIL: Unexpected message: %s" % msg)

logging.info("SUCCESS")
