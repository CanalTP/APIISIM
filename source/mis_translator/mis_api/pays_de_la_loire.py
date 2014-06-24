from navitia import MisApi as NavitiaApi

NAME = "pays_de_la_loire"

class MisApi(NavitiaApi):

    def __init__(self, api_key=""):
        super(MisApi, self).__init__(api_key)
        self._api_url = "http://navitia2-ws.ctp.dev.canaltp.fr//v1/coverage/paysdelaloire/"