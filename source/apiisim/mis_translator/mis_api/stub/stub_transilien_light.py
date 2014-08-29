import os
from stub_base import MisApi as StubApi

NAME="stub_transilien_light"

class MisApi(StubApi):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "stub_transilien_light_stops.json"
    _DB_NAME = "stub_transilien_light_db"
