import os
from _stub import MisApi as StubApi

NAME="stub_sncf_national"

class MisApi(StubApi):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "stub_sncf_national_stops.json"
    _DB_NAME = "stub_sncf_national_db"
    _initialized = False
