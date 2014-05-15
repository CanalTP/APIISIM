class Stop():
    def __init__(self, code, name, lat, long):
        self.code = code
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return ("<Stop: code=%s, name=%s, lat=%s, long=%s>" % \
               (self.code, self.name , self.lat , self.long)).encode("utf-8")

class MisApiBase():
    def __init__(self, api_key=""):
        self._api_key = api_key

    # Return a list with all stop points from this mis
    def get_stops(self):
        return []
