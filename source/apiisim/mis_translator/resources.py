from flask_restful import abort, Resource
import logging, datetime, json
from flask import request, Response
from apiisim.common.mis_plan_trip import LocationContextType, LocationStructure, \
                                  ItineraryResponseType, StatusType, \
                                  SelfDriveConditionType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType
from apiisim.common import AlgorithmEnum, StatusCodeEnum, SelfDriveModeEnum, TripPartEnum, \
                   TransportModeEnum, PlanSearchOptions, string_to_bool, \
                   xsd_duration_to_timedelta, parse_location_context
from apiisim.common.marshalling import DATE_FORMAT, marshal, itinerary_response_type, \
                                       summed_up_itineraries_response_type, \
                                       stops_response_type, capabilities_response_type
from apiisim.common.mis_collect_stops import StopsResponseType
from apiisim.common.mis_capabilities import CapabilitiesResponseType
from mis_api.base import MisApiException, MisApiDateOutOfScopeException, \
                         MisApiBadRequestException, MisApiInternalErrorException
from traceback import format_exc


# Lists of enabled Mis APIs modules
MIS_APIS_AVAILABLE = frozenset(["navitia", "test1", "test2",
                                "pays_de_la_loire", "bretagne", "bourgogne",
                                "transilien", "sncf_national"])

STUB_MIS_APIS_AVAILABLE = frozenset(["stub_transilien",
                                     "stub_pays_de_la_loire", "stub_bourgogne",
                                     "stub_sncf_national","stub_transilien_light",
                                     "stub_pays_de_la_loire_light", "stub_bourgogne_light"])
mis_api_mapping = {} # Mis name : MisApi Class

"""
Load all available Mis APIs modules and populate mis_api_mapping dict so that
we can easily instanciate a MisApi object based on the Mis name.
"""
def load_mis_apis():
    for package, mis_apis in [("mis_api", MIS_APIS_AVAILABLE),
                              ("mis_api.stub", STUB_MIS_APIS_AVAILABLE)]:
        try:
            exec ("import %s" % (package))
        except ImportError as e:
            logging.warning("Could not load MIS API package <%s>: %s", package, e)
            continue

        for m in mis_apis:
            mis_module = "%s_module" % m
            try:
                exec ("from %s import %s as %s" % (package, m, mis_module))
            except Exception as e:
                logging.warning("Could not load MIS API <%s>: %s", m, e)
                continue
            mis_name = eval("%s.NAME" % mis_module)
            mis_api_mapping[mis_name] = eval("%s.MisApi" % mis_module)
            logging.info("Loaded Mis API <%s> ", mis_name)

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

""" 
Parse given itinerary request.
To parse a summed_up_itineraries request (i.e. non-detailed itineraries), 
set summed_up_itineraries to True. To parse a "standard" itinerary request
(i.e. more detailed itineraries), set summed_up_itineraries to False.
"""
def parse_itinerary_request(request, summed_up_itineraries=False):
    # TODO do all validators
    params = _ItineraryRequestParams()

    if not request.json:
        logging.error("No JSON in request")
        abort(400)

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
            departures.append(parse_location_context(d))
        for a in request.json["arrivals"]:
            arrivals.append(parse_location_context(a))
    else:
        if "multiDepartures" in request.json:
            for d in request.json["multiDepartures"]["Departure"]:
                departures.append(parse_location_context(d))
            a = request.json["multiDepartures"]["Arrival"]
            arrivals.append(parse_location_context(a))
        if "multiArrivals" in request.json:
            for a in request.json["multiArrivals"]["Arrival"]:
                arrivals.append(parse_location_context(a))
            d = request.json["multiArrivals"]["Departure"]
            departures.append(parse_location_context(d))
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


class RequestProcessor(object):
    def __init__(self, mis_name, request):
        self._mis_name = mis_name
        self._request = request
        self._start_date = datetime.datetime.now()
        self._mis = get_mis_or_abort(mis_name, request.headers.get("Authorization", ""))

        logging.debug("MIS NAME %s", mis_name)
        logging.debug("URL: %s", request.url)
        if request.json:
            logging.debug("REQUEST.JSON: \n%s", request.json)

    def _parse_request(self):
        return None

    def process(self):
        params = self._parse_request()
        self._resp = self._new_response()

        resp_code = 200
        try:
            self._mis_request(params)
            self._resp.Status = StatusType(Code=StatusCodeEnum.OK)
        except MisApiException as exc:
            resp_code = 500
            self._resp.Status = StatusType(Code=exc.error_code)
        except:
            logging.error(format_exc())
            resp_code = 500
            self._resp.Status = StatusType(Code=StatusCodeEnum.INTERNAL_ERROR)

        if params:
            self._resp.RequestId = params.id
        self._resp.Status.RuntimeDuration = datetime.datetime.now() - self._start_date

        # TODO handle all errors (TOO_MANY_END_POINT...)
        return Response(json.dumps(self._marshal_response()),
                        status=resp_code, mimetype='application/json')


class ItineraryRequestProcessor(RequestProcessor):
    def _parse_request(self):
        return parse_itinerary_request(self._request)

    def _new_response(self):
        return ItineraryResponseType()

    def _mis_request(self, params):
        self._resp.DetailedTrip = \
                self._mis.get_itinerary(
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

    def _marshal_response(self):
        return {'ItineraryResponseType' : marshal(self._resp, itinerary_response_type)}


class SummedUpItinerariesRequestProcessor(RequestProcessor):
    def _parse_request(self):
        return parse_itinerary_request(self._request, summed_up_itineraries=True)

    def _new_response(self):
        return SummedUpItinerariesResponseType()

    def _mis_request(self, params):
        self._resp.summedUpTrips = \
                self._mis.get_summed_up_itineraries(
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

    def _marshal_response(self):
        return {'SummedUpItinerariesResponseType' : \
                marshal(self._resp, summed_up_itineraries_response_type)}


class StopsRequestProcessor(RequestProcessor):
    def _mis_request(self, params):
        self._resp.stopPlaces = self._mis.get_stops()

    def _new_response(self):
        return StopsResponseType()

    def _marshal_response(self):
        return {'StopsResponseType' : marshal(self._resp, stops_response_type)}

class CapabilitiesRequestProcessor(RequestProcessor):
    def _mis_request(self, params):
        capabilities = self._mis.get_capabilities()
        self._resp.MultipleStartsAndArrivals = capabilities.multiple_starts_and_arrivals
        self._resp.GeographicPositionCompliant = capabilities.geographic_position_compliant

    def _new_response(self):
        return CapabilitiesResponseType()

    def _marshal_response(self):
        return {'CapabilitiesResponseType' : marshal(self._resp, capabilities_response_type)}


class Stops(Resource):
    def get(self, mis_name=""):
        return StopsRequestProcessor(mis_name, request).process()

class Capabilities(Resource):
    def get(self, mis_name=""):
        return CapabilitiesRequestProcessor(mis_name, request).process()

class Itineraries(Resource):
    def post(self, mis_name=""):
        return ItineraryRequestProcessor(mis_name, request).process()

class SummedUpItineraries(Resource):
    def post(self, mis_name=""):
        return SummedUpItinerariesRequestProcessor(mis_name, request).process()
