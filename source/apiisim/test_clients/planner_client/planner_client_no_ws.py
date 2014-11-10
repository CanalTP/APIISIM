# -*- coding: utf8 -*-

import os
import json
import logging
from logging import config
import sys

from jsonschema import Draft4Validator

from apiisim.common import formats
from apiisim.common.plan_trip import StartingSearch, EndingSearch, PlanTripNotificationResponseType, \
    PlanTripCancellationRequest, PlanTripExistenceNotificationResponseType, PlanTripResponse

from apiisim.planner import Planner
from apiisim.planner.planner_process import PlannerProcessHandler
from apiisim.test_clients.planner_client import TripCollection as Trip


def init_logging():
    handler = None

    config_file = os.path.join(os.path.dirname(__file__), "logging.conf")
    if os.path.isfile(config_file):
        logging.config.fileConfig(config_file)
    else:
        handler = logging.StreamHandler(stream=sys.stdout)

    if handler:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)


def test(plan_trip_request):
    planner = Planner("postgresql+psycopg2://postgres:postgres@localhost/afimb_stubs_db")
    runner = PlannerProcessHandler(planner, plan_trip_request)
    runner.process()

    while True:
        notification = runner._notif_queue.get()
        logging.info("-- Notification received: %s" % json.dumps(notification.marshal()))
        runner._notif_queue.task_done()
        if isinstance(notification, EndingSearch):
            return


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

    test(Trip.orly_reims())
