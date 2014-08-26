# -*- coding: utf8 -*-

import resources
from flask import Flask
import flask_restful, logging, sys
from logging.handlers import RotatingFileHandler
import argparse, os, ConfigParser

def get_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file")
    parser.add_argument("-l", "--log", help="Log file")

    return parser.parse_args()

def get_config(args):
    if args.config:
        config_file = args.config
        if not os.path.isabs(config_file):
            config_file = os.getcwd() + "/" + config_file
        if not os.path.isfile(config_file):
            logging.error("Configuration file <%s> does not exist", config_file)
            exit(1)
    else:
        config_file = os.path.dirname(os.path.realpath(__file__)) + "/" + "default.conf"

    logging.info("Configuration retrieved from '%s':", config_file)
    config = ConfigParser.RawConfigParser()
    config.read(config_file)

    return config

def init_logging(log_file):
    # TODO add possibility to read logging config from a file/variable
    if log_file:
        handler = RotatingFileHandler(log_file, maxBytes=4*1024*1024, backupCount=3)
    else:
        handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    logging.info("Logging to '%s':", log_file or "stdout")


args = get_cmd_args()
init_logging(args.log)
config = get_config(args)

resources.load_mis_apis(config)

app = Flask(__name__)
api = flask_restful.Api(app)
api.add_resource(resources.Stops, '/<string:mis_name>/v0/stops')
api.add_resource(resources.Capabilities, '/<string:mis_name>/v0/capabilities')
api.add_resource(resources.Itineraries, '/<string:mis_name>/v0/itineraries')
api.add_resource(resources.SummedUpItineraries, '/<string:mis_name>/v0/summed_up_itineraries')

app.run(debug=False)
