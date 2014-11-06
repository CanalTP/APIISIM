# -*- coding: utf8 -*-

import logging
import logging.config

import sys
from logging.handlers import RotatingFileHandler
import argparse
import os
import ConfigParser

from flask import Flask
import flask_restful

import resources


def get_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file")
    parser.add_argument("-l", "--log", help="Log file")

    return parser.parse_args()


def get_config(cmd_args):
    if cmd_args.config:
        config_file = cmd_args.config
        if not os.path.isabs(config_file):
            config_file = os.path.join(os.path.dirname(__file__), config_file)
        if not os.path.isfile(config_file):
            logging.error("Configuration file <%s> does not exist", config_file)
            exit(1)
    else:
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "default.conf")

    logging.info("Configuration retrieved from '%s':", config_file)
    conf = ConfigParser.RawConfigParser()
    conf.read(config_file)

    return conf


def init_logging(log_file):
    handler = None

    config_file = os.path.join(os.path.dirname(__file__), "logging.conf")
    if log_file:
        if not os.path.isabs(log_file):
            log_file = os.path.join(os.path.dirname(__file__), log_file)
        handler = RotatingFileHandler(log_file, maxBytes=4 * 1024 * 1024, backupCount=3)
    elif os.path.isfile(config_file):
        logging.config.fileConfig(config_file)
    else:
        handler = logging.StreamHandler(stream=sys.stdout)

    if handler:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)


if __name__ == '__main__':
    args = get_cmd_args()
    init_logging(args.log)
    config = get_config(args)

    resources.load_mis_apis(config)

    app = Flask(__name__)
    api = flask_restful.Api(app)
    api.add_resource(resources.Stops, '/<string:mis_name>/v0/stops.json')
    api.add_resource(resources.Capabilities, '/<string:mis_name>/v0/capabilities.json')
    api.add_resource(resources.Itineraries, '/<string:mis_name>/v0/itineraries.json')
    api.add_resource(resources.SummedUpItineraries, '/<string:mis_name>/v0/summed_up_itineraries.json')

    app.run(debug=False)
