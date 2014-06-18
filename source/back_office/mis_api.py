import httplib2, json, logging

HTTP_OK = 200

class Stop():
    def __init__(self, code, name, lat, long):
        self.code = code
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return ("<Stop: code=%s, name=%s, lat=%s, long=%s>" % \
                (self.code, self.name , self.lat , self.long)).encode("utf-8")

class MisApi():
    def __init__(self, api_url, api_key=""):
        self._api_url = api_url
        self._api_key = api_key

    # Return a list with all stop points from this mis
    def get_stops(self):
        h = httplib2.Http(".cache")
        headers = {'Authorization' : self._api_key}
        base_url = self._api_url + "stops/"
        params = ""
        stops = []
        if params:
            url = base_url + ("&" if "?" in base_url else "?") + params
        else:
            url = base_url
        logging.debug(url)
        resp, content = h.request(url, "GET", headers=headers)
        if resp.status != HTTP_OK:
            raise Exception("[FAIL]: GET %s: %s" % (url, resp.status))

        content = json.loads(content)
        logging.debug(content)
        for s in content["stops"]:
            logging.debug(s)
            stops.append(Stop(code=s["code"],
                              name=s["name"],
                              lat=float(s["lat"]),
                              long=float(s["long"])))

        return stops
