import os
from stub_base import MisApi as StubApi

NAME = "stub_back_office_test2"

class MisApi(StubApi):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "stub_back_office_test2_stops.json"
    _STOPS_FIELD = "stop_points"
    _DB_NAME = "stub_back_office_test2_stops_db"
