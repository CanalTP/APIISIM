import os
from stub_base import MisApi as StubApi

NAME = "stub_pays_de_la_loire"


class MisApi(StubApi):
    _STOPS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stub_pays_de_la_loire_stops.json")
    _DB_NAME = "stub_pays_de_la_loire_db"
