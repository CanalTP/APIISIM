import flask_restful
from flask_restful import fields, marshal, abort
from mis_api import get_mis_api


stop_fields = {'code': fields.String, 'name': fields.String,
               'lat': fields.Float, 'long': fields.Float}

class Stop(flask_restful.Resource):

    def get(self, mis_name=""):
        mis = get_mis_api(mis_name)
        if not mis:
            abort(404, message="Mis <%s> not supported" % mis_name)

        stops = []
        for s in mis.get_stops():
            stops.append(s)

        return {"stops" : marshal(stops, stop_fields)}

