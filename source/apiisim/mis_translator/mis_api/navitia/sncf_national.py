from base import MisApi as NavitiaApi

NAME = "sncf_national"


class MisApi(NavitiaApi):
    def __init__(self, config, api_key=""):
        super(MisApi, self).__init__(config, api_key)
        self._api_url = "http://navitia2-ws.ctp.dev.canaltp.fr/v1/coverage/sncfnational/"
        self._geographic_position_compliant = False
