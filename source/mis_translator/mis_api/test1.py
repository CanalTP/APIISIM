from base import MisApiBase, Stop
import json, os

NAME = "test1"

class MisApi(MisApiBase):
    _file_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

    def get_stops(self):
        stops = []
        with open(self._file_dir + "test1_stops.json", 'r') as f:
            content = f.read()
            content = json.loads(content[content.find('{"stop_points"'):])

            for s in  content["stop_points"]:
                stops.append(Stop(code=s["id"],
                                  name=s["name"],
                                  lat=s["coord"]["lat"],
                                  long=s["coord"]["lon"]))

        return stops
