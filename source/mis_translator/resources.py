from flask_restful import fields, marshal, abort, Resource
import logging, datetime, json
from flask import request, Response
from mis_api.mis_plan_trip import LocationContextType, LocationStructure, \
                                  ItineraryResponseType, StatusType, \
                                  SelfDriveConditionType
from mis_api.mis_plan_summed_up_trip import SummedUpItinerariesResponseType
from mis_api.base import MisApiException, MisApiDateOutOfScopeException, \
                         MisApiBadRequestException, MisApiInternalErrorException, \
                         StatusCodeEnum, AlgorithmEnum, TripPartEnum, \
                         SelfDriveModeEnum, TransportModeEnum
from traceback import format_exc


# List of enabled Mis APIs modules
MIS_APIS_AVAILABLE = frozenset(["dummy", "navitia", "test1", "test2"])
mis_api_mapping = {} # Mis name : MisApi Class

DATE_FORMAT="%Y-%m-%dT%H:%M:%S"

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

"""
Return new MisApi object based on given mis_name.
"""
def get_mis_api(mis_name, api_key=""):
    if mis_api_mapping.has_key(mis_name):
        return mis_api_mapping[mis_name](api_key)
    else:
        return None

"""
Ignore null elements when marshalling.
Note that it only works when using our customized flask library. When using stock
flask library, this is equivalent to fields.Nested (null elements will 
therefore still be there after marshalling).
"""
class NonNullNested(fields.Nested):

    def __init__(self, *args, **kwargs):
        super(NonNullNested, self).__init__(*args, **kwargs)
        self.display_null = False

"""
Ignore null elements when marshalling.
Note that it only works when using our customized flask library. When using stock
flask library, this is equivalent to fields.List (null elements will 
therefore still be there after marshalling).
"""
class NonNullList(fields.List):

    def __init__(self, *args, **kwargs):
        super(NonNullList, self).__init__(*args, **kwargs)
        self.display_empty = False


stop_fields = {'code': fields.String, 'name': fields.String,
               'lat': fields.Float, 'long': fields.Float}

location_structure_type = {
    'Latitude' : fields.Float,
    'Longitude' : fields.Float
}

place_type = {
    'id' : fields.String,
    'Position' : fields.Nested(location_structure_type),
    'Name' : fields.String,
    'CityCode' : fields.String,
    'CityName' : fields.String,
    'TypeOfPlaceRef' : fields.String,
}

trip_stop_place_type = place_type.copy()
# Parent attribute is currently not implemented and is therefore
# always empty, so ignore it for now.
# trip_stop_place_type['Parent'] = NonNullNested(place_type)

end_point_type = {
    'TripStopPlace' : fields.Nested(trip_stop_place_type),
    'DateTime' : fields.DateTime
}

step_end_point_type = {
    'TripStopPlace' : fields.Nested(trip_stop_place_type),
    'DateTime' : fields.DateTime,
    'PassThrough' : fields.String
}

step_type = {
    'id' : fields.String,
    'Departure' : fields.Nested(step_end_point_type),
    'Arrival' : fields.Nested(step_end_point_type),
    'Duration' : fields.Integer
}

pt_ride_type = {
    'ptNetworkRef' : fields.String,
    'lineRef' : fields.String,
    'PublicTransportMode' : fields.String,
    'Departure' :  fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'steps' : NonNullList(NonNullNested(step_type))
}

leg_type = {
    'SelfDriveMode' : fields.String,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer
}

section_type = {
    'PartialTripId' : fields.String,
    'PTRide' : fields.Nested(pt_ride_type, allow_null=True),
    'Leg' : fields.Nested(leg_type, allow_null=True)
}

trip_type = {
    'id' : fields.Integer,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'InterchangeNumber' : fields.Integer,
    'sections' : NonNullList(NonNullNested(section_type))
}

status_type = {
    'Code' : fields.String,
    'RuntimeDuration' : fields.Float
}

itinerary_response_type = {
    'Status' : fields.Nested(status_type),
    'DetailedTrip' : fields.Nested(trip_type, allow_null=True)
}

summed_up_trip_type = {
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'InterchangeCount' : fields.Integer,
    'InterchangeDuration' : fields.Integer
}

summed_up_itineraries_response_type = {
    'Status' : fields.Nested(status_type),
    'summedUpTrips' : NonNullList(NonNullNested(summed_up_trip_type))
}

def string_to_bool(string):
    if string in ["True", "true", "TRUE"]:
        return True
    else:
        return False

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


def get_params(request, summed_up_itineraries=False):
    # TODO do all validators
    params = _ItineraryRequestParams()

    # Required
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
        abort(400)

    params.modes = request.json.get('modes', [TransportModeEnum.ALL])
    for m in params.modes:
        if not TransportModeEnum.validate(m):
            abort(400)

    params.self_drive_conditions = []
    for c in request.json.get('selfDriveConditions', []):
        condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                SelfDriveMode=c.get("SelfDriveMode", ""))
        if not TripPartEnum.validate(condition.TripPart) or \
           not SelfDriveModeEnum.validate(condition.SelfDriveMode):
           abort(400)
        params.self_drive_conditions.append(condition)

    params.accessibility_constraint = string_to_bool(request.json.get('AccessibilityConstraint', "False"))
    params.language = request.json.get('Language', "")
    params.options = request.json.get("options", [])

    return params


""" 
Send itinerary request to given MIS.
If summed_up_itineraries is True, we'll request summed up itineraries 
(i.e. non-detailed itineraries), otherwise we'll request "standard" 
itineraries (i.e. more detailed itineraries).
"""
def _itinerary_request(mis_name, request, summed_up_itineraries=False):
    request_start_date = datetime.datetime.now()

    mis = get_mis_or_abort(mis_name, request.headers.get("Authorization", ""))
    if not request.json:
        abort(400)

    logging.debug("MIS NAME %s", mis_name)
    logging.debug("URL: %s\nREQUEST.JSON: %s", request.url, request.json)

    if summed_up_itineraries:
        if ("DepartureTime" not in request.json and "ArrivalTime" not in request.json):
            abort(400)
    else:
        if ("DepartureTime" not in request.json and "ArrivalTime" not in request.json) \
            or ("multiDepartures" not in request.json and "multiArrivals" not in request.json) \
            or ("multiDepartures" in request.json and "multiArrivals" in request.json):
            abort(400)

    params = get_params(request, summed_up_itineraries)
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

        stops = []
        for s in mis.get_stops():
            stops.append(s)

        resp_data = {"stops" : marshal(stops, stop_fields)}
        return Response(json.dumps(resp_data),
                        status=200, mimetype='application/json')

class Itineraries(Resource):

    def post(self, mis_name=""):
        return _itinerary_request(mis_name, request)

class SummedUpItineraries(Resource):

    def post(self, mis_name=""):
        return _itinerary_request(mis_name, request, summed_up_itineraries=True)
