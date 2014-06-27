from flask_restful import abort, Resource
import logging, datetime, json
from flask import request, Response
from common.mis_plan_trip import LocationContextType, LocationStructure, \
                                  ItineraryResponseType, StatusType, \
                                  SelfDriveConditionType
from common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType
from common import AlgorithmEnum, StatusCodeEnum, SelfDriveModeEnum, TripPartEnum, \
                   TransportModeEnum, PlanSearchOptions, string_to_bool
from common.marshalling import *
from mis_api.base import MisApiException, MisApiDateOutOfScopeException, \
                         MisApiBadRequestException, MisApiInternalErrorException
from traceback import format_exc


# List of enabled Mis APIs modules
MIS_APIS_AVAILABLE = frozenset(["dummy", "navitia", "test1", "test2", 
                                "pays_de_la_loire", "bretagne", "bourgogne",
                                "transilien", "sncf_national", "stub_transilien", 
                                "stub_pays_de_la_loire", "stub_bourgogne"])
mis_api_mapping = {} # Mis name : MisApi Class

"""
Load all available Mis APIs modules and populate mis_api_mapping dict so that
we can easily instanciate a MisApi object based on the Mis name.
"""
def load_mis_apis():
    for m in MIS_APIS_AVAILABLE:
        mis_module = "%s_module" % m
        exec ("import mis_api.%s as %s" % (m, mis_module))
        mis_name = eval("%s.NAME" % mis_module)
        mis_api_mapping[mis_name] = eval("%s.MisApi" % mis_module)
        logging.info("Loaded Mis API <%s> ", m)

"""
Return new MisApi object based on given mis_name.
"""
def get_mis_api(mis_name, api_key=""):
    if mis_api_mapping.has_key(mis_name):
        return mis_api_mapping[mis_name](api_key)
    else:
        return None

def get_mis_or_abort(mis_name, api_key=""):
    mis = get_mis_api(mis_name, api_key)
    if not mis:
        abort(404, message="Mis <%s> not supported" % mis_name)

    return mis

class _ItineraryRequestParams:
    def __init__(self):
        self.departures = []
        self.arrivals = []
        self.departure_time = ""
        self.arrival_time = ""
        self.algorithm = AlgorithmEnum.CLASSIC
        self.modes = []
        self.self_drive_conditions = []
        self.accessibility_constraint = False
        self.language = ""
        self.options = []


def parse_request(request, summed_up_itineraries=False):
    # TODO do all validators
    params = _ItineraryRequestParams()

    # Required
    # TODO send error if no ID given
    params.id = request.json.get("id", "default_id")
    departure_time = request.json.get("DepartureTime", "")
    arrival_time = request.json.get("ArrivalTime", "")
    try:
        if departure_time:
            params.departure_time = datetime.datetime.strptime(departure_time, DATE_FORMAT)
        if arrival_time:
            params.arrival_time = datetime.datetime.strptime(arrival_time, DATE_FORMAT)
    except ValueError as exc:
        logging.error("DateTime format error: %s", exc)
        abort(400)

    departures = []
    arrivals = []
    if summed_up_itineraries:
        for d in request.json["departures"]:
            departures.append(LocationContextType(
                                    Position=LocationStructure(
                                                Latitude=d["Position"]["Latitude"],
                                                Longitude=d["Position"]["Longitude"]),
                                                AccessTime=d["AccessTime"],
                                    PlaceTypeId=d["PlaceTypeId"]))
        for a in request.json["arrivals"]:
            arrivals.append(LocationContextType(
                                    Position=LocationStructure(
                                                Latitude=a["Position"]["Latitude"],
                                                Longitude=a["Position"]["Longitude"]),
                                                AccessTime=a["AccessTime"],
                                    PlaceTypeId=a["PlaceTypeId"]))
    else:
        if "multiDepartures" in request.json:
            for d in request.json["multiDepartures"]["Departure"]:
                departures.append(LocationContextType(
                                        Position=LocationStructure(
                                                    Latitude=d["Position"]["Latitude"],
                                                    Longitude=d["Position"]["Longitude"]),
                                                    AccessTime=d["AccessTime"],
                                        PlaceTypeId=d["PlaceTypeId"]))
            a = request.json["multiDepartures"]["Arrival"]
            arrivals.append(LocationContextType(
                                    Position=LocationStructure(
                                                Latitude=a["Position"]["Latitude"],
                                                Longitude=a["Position"]["Longitude"]),
                                                AccessTime=a["AccessTime"],
                                    PlaceTypeId=a["PlaceTypeId"]))

        if "multiArrivals" in request.json:
            for a in request.json["multiArrivals"]["Arrival"]:
                arrivals.append(LocationContextType(
                                    Position=LocationStructure(
                                                Latitude=a["Position"]["Latitude"],
                                                Longitude=a["Position"]["Longitude"]),
                                                AccessTime=a["AccessTime"],
                                    PlaceTypeId=a["PlaceTypeId"]))
            d = request.json["multiArrivals"]["Departure"]
            departures.append(LocationContextType(
                                    Position=LocationStructure(
                                                Latitude=d["Position"]["Latitude"],
                                                Longitude=d["Position"]["Longitude"]),
                                                AccessTime=d["AccessTime"],
                                    PlaceTypeId=d["PlaceTypeId"]))
    params.departures = departures
    params.arrivals = arrivals

    # Optional
    params.algorithm = request.json.get('Algorithm', AlgorithmEnum.CLASSIC)
    if not AlgorithmEnum.validate(params.algorithm):
        logging.error("Invalid algorithm")
        abort(400)

    params.modes = request.json.get('modes', [TransportModeEnum.ALL])
    for m in params.modes:
        if not TransportModeEnum.validate(m):
            logging.error("Invalid transport mode")
            abort(400)

    params.self_drive_conditions = []
    for c in request.json.get('selfDriveConditions', []):
        condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                SelfDriveMode=c.get("SelfDriveMode", ""))
        if not TripPartEnum.validate(condition.TripPart) or \
           not SelfDriveModeEnum.validate(condition.SelfDriveMode):
           logging.error("Invalid self drive condition")
           abort(400)
        params.self_drive_conditions.append(condition)

    params.accessibility_constraint = string_to_bool(request.json.get('AccessibilityConstraint', "False"))
    params.language = request.json.get('Language', "")
    params.options = request.json.get("options", [])
    if PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED in params.options \
        and len(departures) > 1 and len(arrivals) > 1:
        logging.error("DEPARTURE_ARRIVAL_OPTIMIZED option only available with 1-n itineraries")
        abort(400)

    return params


""" 
Send itinerary request to given MIS.
If summed_up_itineraries is True, we'll request summed up itineraries 
(i.e. non-detailed itineraries), otherwise we'll request "standard" 
itineraries (i.e. more detailed itineraries).
"""
def _itinerary_request(mis_name, request, summed_up_itineraries=False):
    request_start_date = datetime.datetime.now()

    if not request.json:
        logging.error("No JSON in request")
        abort(400)


    mis = get_mis_or_abort(mis_name, request.headers.get("Authorization", ""))

    logging.debug("MIS NAME %s", mis_name)
    logging.debug("URL: %s\nREQUEST.JSON: %s", request.url, request.json)

    if summed_up_itineraries:
        if ("DepartureTime" not in request.json) and ("ArrivalTime" not in request.json):
            logging.error("No departure/arrival time given")
            abort(400)
    else:
        if ("DepartureTime" not in request.json and "ArrivalTime" not in request.json) \
            or ("multiDepartures" not in request.json and "multiArrivals" not in request.json) \
            or ("multiDepartures" in request.json and "multiArrivals" in request.json):
            logging.error("Invalid itinerary request")
            abort(400)

    params = parse_request(request, summed_up_itineraries)

    resp_code = 200

    if summed_up_itineraries:
        func = mis.get_summed_up_itineraries
        ret = SummedUpItinerariesResponseType()
    else:
        func = mis.get_itinerary
        ret = ItineraryResponseType()
    try:
        ret = func(
                params.departures, 
                params.arrivals, 
                params.departure_time,
                params.arrival_time, 
                algorithm=params.algorithm, 
                modes=params.modes, 
                self_drive_conditions=params.self_drive_conditions,
                accessibility_constraint=params.accessibility_constraint,
                language=params.language,
                options=params.options)
        ret.Status = StatusType(Code=StatusCodeEnum.OK)
    except MisApiException as exc:
        resp_code = 500
        ret.Status = StatusType(Code=exc.error_code)
    except:
        logging.error(format_exc())
        resp_code = 500
        ret.Status = StatusType(Code=StatusCodeEnum.INTERNAL_ERROR)

    request_duration = datetime.datetime.now() - request_start_date
    ret.Status.RuntimeDuration = request_duration.total_seconds()
    ret.RequestId = params.id
    if summed_up_itineraries:
        resp_data = {'SummedUpItinerariesResponseType' : \
                     marshal(ret, summed_up_itineraries_response_type)}
    else:
        resp_data = {'ItineraryResponseType' : marshal(ret, itinerary_response_type)}

    # TODO handle all errors (TOO_MANY_END_POINT...)
    return Response(json.dumps(resp_data),
                    status=resp_code, mimetype='application/json')


class Stops(Resource):

    def get(self, mis_name=""):
        mis = get_mis_or_abort(mis_name, request.headers.get("Authorization", ""))

        stops = mis.get_stops()

        resp_data = {"stops" : marshal(stops, stop_fields)}
        return Response(json.dumps(resp_data),
                        status=200, mimetype='application/json')

class Itineraries(Resource):

    def post(self, mis_name=""):
        return _itinerary_request(mis_name, request)

class SummedUpItineraries(Resource):

    def post(self, mis_name=""):
        return _itinerary_request(mis_name, request, summed_up_itineraries=True)
