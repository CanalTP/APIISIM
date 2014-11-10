# -*- coding: utf8 -*-

import json
import logging
import sys

from jsonschema import validate, Draft4Validator

from websocket import create_connection
from apiisim.common.marshalling import marshal, plan_trip_request_type
from apiisim.common import formats
from apiisim.test_clients.planner_client import TripCollection as Trip


def init_logging():
    handler = logging.StreamHandler(stream=sys.stdout)
    if handler:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)


def receive_msg(connection):
    ret = connection.recv()
    logging.debug("Received: \n%s" % ret)
    ret = json.loads(ret)

    return ret


def test(plan_trip_request):
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

    test(Trip.paris_reims())
