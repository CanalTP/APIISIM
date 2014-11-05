# -*- coding: utf8 -*-

from websocket import create_connection
from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
    PlanTripCancellationRequest, EndingSearch, PlanTripNotificationResponseType, \
    PlanTripExistenceNotificationResponseType, PlanTripResponse, StartingSearch
from apiisim.common.marshalling import marshal, plan_trip_request_type
from apiisim.common import formats
from apiisim.common.mis_plan_trip import LocationContextType
from apiisim.planner import Planner
from apiisim.planner.planner_process import PlannerProcessHandler
from random import randint
import datetime
import json
import logging
import sys

from datetime import timedelta
from jsonschema import validate, Draft4Validator


def init_logging():
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)


def new_location(place_id, longitude, latitude):
    ret = LocationContextType()
    ret.PlaceTypeId = place_id
    l = LocationStructure()
    l.Longitude = longitude
    l.Latitude = latitude
    ret.Position = l

    return ret


def new_request(departure, arrival):
    ret = PlanTripRequestType()

    ret.clientRequestId = "request_" + str(randint(0, 60000))
    # ret.DepartureTime = datetime.datetime(year=2014, month=8, day=22, hour=18) - timedelta(days=50)
    ret.DepartureTime = datetime.datetime.now() - timedelta(days=10)
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


# Below are some examples of itinerary requests.

def test_paris_reims():
    return new_request(new_location(None, 2.348294, 48.858108),  # Chatelet
                       new_location(None, 4.034720, 49.262780))  # Reims


def receive_msg(connection):
    ret = connection.recv()
    logging.debug("Received: \n%s" % ret)
    ret = json.loads(ret)

    return ret


def test_using_ws(plan_trip_request):
    logging.info("Starting test")
    logging.info("Opening connection")
    ws = create_connection("ws://localhost/planner")

    data = json.dumps({"PlanTripRequestType": marshal(plan_trip_request, plan_trip_request_type)})
    logging.info("Send: %s" % data)
    ws.send(data)

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

    logging.info("End of test: success")


def test_offline(plan_trip_request):
    planner = Planner("postgresql+psycopg2://postgres:postgres@localhost/afimb_navitia_db")
    runner = PlannerProcessHandler(planner, plan_trip_request)
    runner.process()

    print
    print "Notifications received:"
    while True:
        print
        notification = runner._notif_queue.get()
        print json.dumps(notification.marshal())
        runner._notif_queue.task_done()
        if isinstance(notification, EndingSearch):
            return
    print


if __name__ == '__main__':
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

    #test_using_ws(test_paris_reims())
    test_offline(test_paris_reims())
