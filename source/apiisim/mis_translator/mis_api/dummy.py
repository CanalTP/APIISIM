from base import MisApiBase, Stop

NAME = "dummy"

class MisApi(MisApiBase):
    def get_stops(self):
        return [Stop("stop_code1", "stop1", 123.3, 360.33),
                Stop("stop_code2", "stop2", 423.3, 3688.33)]
