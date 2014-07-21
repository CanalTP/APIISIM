# -*- coding: utf8 -*-

import resources
from flask import Flask
import flask_restful, logging, sys


def init_logging():
    # TODO add possibility to read logging config from a file/variable
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

init_logging()

resources.load_mis_apis()

app = Flask(__name__)
api = flask_restful.Api(app)
api.add_resource(resources.Stops, '/<string:mis_name>/v0/stops')
api.add_resource(resources.Itineraries, '/<string:mis_name>/v0/itineraries')
api.add_resource(resources.SummedUpItineraries, '/<string:mis_name>/v0/summed_up_itineraries')

app.run(debug=False)
