from base import MisApiBase, Stop
import json

NAME = "test2"

class MisApi(MisApiBase):
    def get_stops(self, city=""):
        stops = []
        with open("./mis_api/test2_stops.json", 'r') as f:
            content = f.read()
            content = json.loads(content[content.find('{"stop_points"'):])

            for s in  content["stop_points"]:
                stops.append(Stop(code=s["id"],
                                  name=s["name"],
                                  lat=s["coord"]["lat"],
                                  long=s["coord"]["lon"]))

        return stops
