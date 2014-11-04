import json
import logging

import httplib2
# from inspect import getmembers
#from pprint import pprint

HTTP_OK = 200


class Stop(object):
    def __init__(self, code, name, lat, long):
        self.code = code
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return ("<Stop: code=%s, name=%s, lat=%s, long=%s>" %
                (self.code, self.name, self.lat, self.long)).encode("utf-8")


class MisCapabilities(object):
    def __init__(self, multiple_starts_and_arrivals, geographic_position_compliant):
        self.multiple_starts_and_arrivals = multiple_starts_and_arrivals
        self.geographic_position_compliant = geographic_position_compliant


class MisApi(object):
    def __init__(self, api_url, api_key=""):
        self._api_url = api_url
        self._api_key = api_key

    def _http_request(self, resource):
        h = httplib2.Http()
        headers = {'Authorization': self._api_key}
        url = self._api_url + resource

        logging.debug(url)
        if self._api_key:
            resp, content = h.request(url, "GET", headers=headers)
        else:
            resp, content = h.request(url, "GET")
        if resp.status != HTTP_OK:
            raise Exception("[FAIL]: GET %s: %s" % (url, resp.status))

        return resp, content

    # Return a list with all stop points from this mis
    def get_stops(self):
        resp, content = self._http_request("stops.json")
        stops = []
        content = json.loads(content)
        logging.debug(content)
        for s in \
                content["StopsResponse"]["PublicationDelivery"]["dataObjects"]["CompositeFrame"]["frames"]["SiteFrame"][
                    "stopPlaces"]:
            quay = s["quays"][0]
            # skip empty Centroid
            if "Latitude" in quay["Centroid"]["Location"]:
                stops.append(
                    Stop(code=quay["PrivateCode"],
                         name=quay["Name"],
                         lat=float(quay["Centroid"]["Location"]["Latitude"]),
                         long=float(quay["Centroid"]["Location"]["Longitude"])))

        return stops

    def get_capabilties(self):
        resp, content = self._http_request("capabilities.json")
        content = json.loads(content)
        logging.debug(content)
        content = content["CapabilitiesResponse"]

        return MisCapabilities(content["MultipleStartsAndArrivals"],
                               content["GeographicPositionCompliant"])

    # Should not be hard-coded but it will do the job for now.
    def get_shape(self, name):
        if name == "paysdelaloire":
            return "POLYGON((-2.557442956 46.26975161,-2.557442956 48.56805252," \
                   "0.915342221 48.56805252,0.915342221 46.26975161,-2.557442956 46.26975161))"
        elif name == "transilien":
            return "POLYGON((1.447406441 48.12237262,1.447406441 " \
                   "49.2334534,3.54286966 49.2334534,3.54286966 48.12237262,1.447406441 48.12237262))"
        elif name == "bretagne":
            return "POLYGON((-5.139900401 47.27952014,-5.139900401 48.87967361," \
                   "-1.013521807 48.87967361,-1.013521807 47.27952014,-5.139900401 47.27952014))"
        else:
            return None
