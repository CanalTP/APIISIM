from base import MisApiBase
from apiisim.common.mis_collect_stops import StopPlaceType, QuayType, \
                                             CentroidType, LocationStructure
import json, os

NAME = "test2"

class MisApi(MisApiBase):

    _file_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

    def get_stops(self):
        stops = []
        with open(self._file_dir + "test2_stops.json", 'r') as f:
            content = f.read()
            content = json.loads(content[content.find('{"stop_points"'):])

            for s in  content["stop_points"]:
                stops.append(
                    StopPlaceType(
                        id=s["id"],
                        quays=[QuayType(
                                id=s["id"],
                                Name=s["name"],
                                PrivateCode=s["id"],
                                Centroid=CentroidType(
                                            Location=LocationStructure(
                                                        Longitude=s["coord"]["lon"],
                                                        Latitude=s["coord"]["lat"])))]))

        return stops
