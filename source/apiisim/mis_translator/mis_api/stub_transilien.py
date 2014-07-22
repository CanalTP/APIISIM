import os
from _stub import MisApi as StubApi

NAME="stub_transilien"

class MisApi(StubApi):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "stub_transilien_stops.json"
    _DB_NAME = "stub_transilien_db"
    _initialized = False
