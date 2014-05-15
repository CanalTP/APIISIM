from base import MisApiBase, Stop
import json, httplib2, logging

NAME = "navitia"
HTTP_OK = 200
COUNT="count=10" # Items per page


class MisApi(MisApiBase):
    _api_url = "http://api.navitia.io/v1/coverage/paris/stop_points"

    def get_stops(self):
        h = httplib2.Http(".cache")
        base_url = self._api_url
        params = unicode(COUNT)
        stops = []
        # TODO delete that, just here for testing purposes
        max_pages = 10
        pages_read = 0
        while True:
            if params:
                url = base_url + ("&" if "?" in base_url else "?") + params
            else:
                url = base_url
            logging.debug("URL %s", url)

            resp, content = h.request(url, "GET")
            if resp.status != HTTP_OK:
                raise Exception("GET <%s> FAILED: %s" % (url, resp.status))

            content = json.loads(content)
            for s in  content["stop_points"]:
                stops.append(Stop(code=s["id"],
                                        name=s["name"],
                                        lat=s["coord"]["lat"],
                                        long=s["coord"]["lon"]))

            for s in  content["links"]:
                if "type" in s and s['type'] == "next":
                    next_base_url = s["href"]

            if base_url == next_base_url:
                # We have read all pages, quit
                break
            else:
                # Read next page
                base_url = next_base_url

            # TODO delete that, just here for testing purposes
            pages_read = pages_read  + 1
            if pages_read > max_pages:
                break

        return stops
