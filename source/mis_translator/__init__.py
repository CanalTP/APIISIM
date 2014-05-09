# -*- coding: utf8 -*-

from mis_api import load_mis_apis
import httplib2, json
import resources
from flask import Flask
import flask_restful, logging, sys

def init_logging():
    # TODO add possibility to read logging config from a file/variable
    handler = logging.StreamHandler(stream=sys.stdout)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

init_logging()

load_mis_apis()

app = Flask(__name__)
api = flask_restful.Api(app)
api.add_resource(resources.Stop, '/<string:mis_name>/v0/stops/')

app.run(debug=True)
