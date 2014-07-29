import httplib2, json, logging

HTTP_OK = 200

class Stop(object):
    def __init__(self, code, name, lat, long):
        self.code = code
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return ("<Stop: code=%s, name=%s, lat=%s, long=%s>" % \
                (self.code, self.name , self.lat , self.long)).encode("utf-8")

class MisCapabilities(object):
    def __init__(self, multiple_starts_and_arrivals, geographic_position_compliant):
        self.multiple_starts_and_arrivals = multiple_starts_and_arrivals
        self.geographic_position_compliant = geographic_position_compliant

class MisApi(object):
    def __init__(self, api_url, api_key=""):
        self._api_url = api_url
        self._api_key = api_key

    def _http_request(self, resource):
        h = httplib2.Http(".cache")
        headers = {'Authorization' : self._api_key}
        url = self._api_url + resource

        logging.debug(url)
        resp, content = h.request(url, "GET", headers=headers)
        if resp.status != HTTP_OK:
            raise Exception("[FAIL]: GET %s: %s" % (url, resp.status))

        return resp, content

    # Return a list with all stop points from this mis
    def get_stops(self):
        resp, content = self._http_request("stops")
        stops = []
        content = json.loads(content)
        logging.debug(content)
        for s in content["StopsResponseType"]["stopPlaces"]:
            quay = s["quays"][0]
            stops.append(
                Stop(code=quay["PrivateCode"],
                     name=quay["Name"],
                     lat=float(quay["Centroid"]["Location"]["Latitude"]),
                     long=float(quay["Centroid"]["Location"]["Longitude"])))

        return stops

    def get_capabilties(self):
        resp, content = self._http_request("capabilities")
        content = json.loads(content)
        logging.debug(content)
        content = content["CapabilitiesResponseType"]

        return MisCapabilities(content["MultipleStartsAndArrivals"],
                               content["GeographicPositionCompliant"])
