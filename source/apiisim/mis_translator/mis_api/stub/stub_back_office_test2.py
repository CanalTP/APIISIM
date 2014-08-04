import os
from stub_base import StopPointsMisApi

NAME = "stub_back_office_test2"

class MisApi(StopPointsMisApi):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "stub_back_office_test2_stops.json"
    _DB_NAME = "stub_back_office_test2_stops_db"
    _initialized = False
