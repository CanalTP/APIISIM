from flask_restful import fields, marshal, abort, Resource
import mis_translator
import logging, datetime, json
from flask import request, Response
from fields import *
from mis_api.sim_plan_trip import LocationContextType, PositionType, \
                                  ItineraryResponseType, ResponseStatusType, \
                                  SelfDriveConditionType
from mis_api.sim_plan_sumed_up_trip import SumedUpItinerariesResponseType
from mis_api.base import MisApiException, MisApiDateOutOfScopeException, \
                         MisApiBadRequestException, MisApiInternalErrorException, \
                         StatusCodeEnum, AlgorithmEnum, TripPartEnum, \
                         SelfDriveModeEnum, TransportModeEnum
from traceback import format_exc

class NonNullNested(fields.Nested):

    def __init__(self, *args, **kwargs):
        super(NonNullNested, self).__init__(*args, **kwargs)
        self.display_null = False

class NonNullList(fields.List):

    def __init__(self, *args, **kwargs):
        super(NonNullList, self).__init__(*args, **kwargs)
        self.display_empty = False


stop_fields = {'code': fields.String, 'name': fields.String,
               'lat': fields.Float, 'long': fields.Float}

position_type = {
    'Lat' : fields.Float,
    'Long' : fields.Float
}

site_type_type = {
    'id' : fields.String,
    'Position' : fields.Nested(position_type),
    'Name' : fields.String,
    'CityCode' : fields.String,
    'CityName' : fields.String,
    'SiteType' : fields.String,
    'Time' : fields.DateTime,
}

stop_place_type = {
    'Parent' : fields.Nested(site_type_type)
}

end_point_type = {
    'Site' : fields.Nested(stop_place_type)
}

step_end_point_type = {
    'StopPlace' : fields.Nested(stop_place_type),
    'Time' : fields.DateTime,
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
    'DepartureTime' : fields.DateTime,
    'ArrivalTime' : fields.DateTime,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'InterchangeNumber' : fields.Integer,
    'sections' : NonNullList(NonNullNested(section_type))
}

response_status_type = {
    'Code' : fields.String,
    'RuntimeDuration' : fields.Float
}

itinerary_response_type = {
    'Status' : fields.Nested(response_status_type),
    'DetailedTrip' : fields.Nested(trip_type, allow_null=True)
}

sumed_up_trip_type = {
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'InterchangeCount' : fields.Integer,
    'InterchangeDuration' : fields.Integer
}

sumed_up_itineraries_response_type = {
    'Status' : fields.Nested(response_status_type),
    'sumedUpTrips' : NonNullList(NonNullNested(sumed_up_trip_type))
}

def string_to_bool(string):
    if string in ["True", "true"]:
        return True
    else:
        return False

def get_mis_or_abort(mis_name):
    mis = mis_translator.get_mis_api(mis_name)
    if not mis:
        abort(404, message="Mis <%s> not supported" % mis_name)

    return mis

class Stops(Resource):

    def get(self, mis_name=""):
        mis = get_mis_or_abort(mis_name)

        stops = []
        for s in mis.get_stops():
            stops.append(s)

        resp_data = {"stops" : marshal(stops, stop_fields)}
        return Response(json.dumps(resp_data),
                        status=200, mimetype='application/json')

# TODO make a decorator that catches KeyError and sends HTTP error 400)
class Itineraries(Resource):

    def post(self, mis_name=""):
        request_start_date = datetime.datetime.now()

        mis = get_mis_or_abort(mis_name)
        if not request.json:
            abort(400)

        logging.debug("MIS NAME %s", mis_name)
        logging.debug("request.json: %s", request.json)

        if (DEPARTURE_TIME not in request.json and ARRIVAL_TIME not in request.json) \
            or (MULTI_DEPARTURES not in request.json and MULTI_ARRIVALS not in request.json) \
            or (MULTI_DEPARTURES in request.json and MULTI_ARRIVALS in request.json):
            abort(400)

        # Required
        departure_time = request.json.get(DEPARTURE_TIME, "")
        arrival_time = request.json.get(ARRIVAL_TIME, "")
        departures = []
        arrivals = []
        if MULTI_DEPARTURES in request.json:
            for d in request.json[MULTI_DEPARTURES][DEPARTURE]:
                departures.append(LocationContextType(
                                        Position=PositionType(
                                            Lat=d[POSITION][LAT],
                                            Long=d[POSITION][LONG]),
                                        AccessDuration=d[ACCESS_DURATION],
                                        QuayId=d[QUAY_ID]))
            a = request.json[MULTI_DEPARTURES][ARRIVAL]
            arrivals.append(LocationContextType(
                                    Position=PositionType(
                                        Lat=a[POSITION][LAT],
                                        Long=a[POSITION][LONG]),
                                    AccessDuration=a[ACCESS_DURATION],
                                    QuayId=a[QUAY_ID]))

        if MULTI_ARRIVALS in request.json:
            for a in request.json[MULTI_ARRIVALS][ARRIVAL]:
                arrivals.append(LocationContextType(
                                        Position=PositionType(
                                            Lat=a[POSITION][LAT],
                                            Long=a[POSITION][LONG]),
                                        AccessDuration=a[ACCESS_DURATION],
                                        QuayId=a[QUAY_ID]))
            d = request.json[MULTI_ARRIVALS][DEPARTURE]
            departures.append(LocationContextType(
                                    Position=PositionType(
                                        Lat=d[POSITION][LAT],
                                        Long=d[POSITION][LONG]),
                                    AccessDuration=d[ACCESS_DURATION],
                                    QuayId=d[QUAY_ID]))


        # Optional
        
        # TODO do all validators
        algorithm = request.json.get('algorithm', AlgorithmEnum.CLASSIC)
        if not AlgorithmEnum.validate(algorithm):
            abort(400)
        modes = request.json.get('modes', TransportModeEnum.ALL)
        self_drive_conditions = []
        for c in request.json.get('selfDriveConditions', []):
            condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                    SelfDriveMode=c.get("SelfDriveMode", ""))
            if not TripPartEnum.validate(condition.TripPart) or \
               not SelfDriveModeEnum.validate(condition.SelfDriveMode):
               abort(400)
            self_drive_conditions.append(condition)

        accessibility_constraint = string_to_bool(request.json.get('accessibilityConstraint', "False"))
        language = request.json.get('language', "")
        options = request.json.get("options", [])

        if departure_time:
            departure_time = datetime.datetime.strptime(departure_time, TIME_FORMAT)
        if arrival_time:
            arrival_time = datetime.datetime.strptime(arrival_time, TIME_FORMAT)

        resp_code = 200
        try:
            best_itinerary = mis.get_itinerary(departures, arrivals, departure_time,
                                               arrival_time, algorithm=algorithm, 
                                               modes=modes, self_drive_conditions=self_drive_conditions,
                                               accessibility_constraint=accessibility_constraint,
                                               language=language)
            best_itinerary.Status = ResponseStatusType(Code=StatusCodeEnum.OK)
        except MisApiException as exc:
            resp_code = 500
            best_itinerary = ItineraryResponseType(
                                    Status=ResponseStatusType(Code=exc.error_code))
        except:
            logging.error(format_exc())
            resp_code = 500
            best_itinerary = ItineraryResponseType(
                                    Status=ResponseStatusType(Code=StatusCodeEnum.INTERNAL_ERROR))

        request_duration = datetime.datetime.now() - request_start_date
        best_itinerary.Status.RuntimeDuration = request_duration.total_seconds()
        resp_data = {'ItineraryResponseType' : marshal(best_itinerary, itinerary_response_type)}
        # logging.debug(resp_data)

        # TODO handle all errors (TOO_MANY_END_POINT...)
        return Response(json.dumps(resp_data),
                        status=resp_code, mimetype='application/json')


class SumedUpItineraries(Resource):

    def post(self, mis_name=""):
        request_start_date = datetime.datetime.now()

        mis = get_mis_or_abort(mis_name)
        if not request.json:
            abort(400)

        logging.debug("MIS NAME %s", mis_name)
        logging.debug("request.json: %s", request.json)

        if (DEPARTURE_TIME not in request.json and ARRIVAL_TIME not in request.json):
            abort(400)

        # Required
        departure_time = request.json.get(DEPARTURE_TIME, "")
        arrival_time = request.json.get(ARRIVAL_TIME, "")
        departures = []
        arrivals = []
        for d in request.json[DEPARTURES][DEPARTURE]:
            departures.append(LocationContextType(
                                    Position=PositionType(
                                        Lat=d[POSITION][LAT],
                                        Long=d[POSITION][LONG]),
                                    AccessDuration=d[ACCESS_DURATION],
                                    QuayId=d[QUAY_ID]))
        for a in request.json[ARRIVALS][ARRIVAL]:
            arrivals.append(LocationContextType(
                                    Position=PositionType(
                                        Lat=a[POSITION][LAT],
                                        Long=a[POSITION][LONG]),
                                    AccessDuration=a[ACCESS_DURATION],
                                    QuayId=a[QUAY_ID]))


        # Optional
        
        # TODO do all validators
        algorithm = request.json.get('algorithm', AlgorithmEnum.CLASSIC)
        if not AlgorithmEnum.validate(algorithm):
            abort(400)
        modes = request.json.get('modes', TransportModeEnum.ALL)
        self_drive_conditions = []
        for c in request.json.get('selfDriveConditions', []):
            condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                    SelfDriveMode=c.get("SelfDriveMode", ""))
            if not TripPartEnum.validate(condition.TripPart) or \
               not SelfDriveModeEnum.validate(condition.SelfDriveMode):
               abort(400)
            self_drive_conditions.append(condition)

        accessibility_constraint = string_to_bool(request.json.get('accessibilityConstraint', "False"))
        language = request.json.get('language', "")
        options = request.json.get("options", [])

        if departure_time:
            departure_time = datetime.datetime.strptime(departure_time, TIME_FORMAT)
        if arrival_time:
            arrival_time = datetime.datetime.strptime(arrival_time, TIME_FORMAT)

        resp_code = 200
        try:
            sumed_up_itineraries = mis.get_sumed_up_itineraries(
                                        departures, arrivals, departure_time,
                                        arrival_time, algorithm=algorithm, 
                                        modes=modes, self_drive_conditions=self_drive_conditions,
                                        accessibility_constraint=accessibility_constraint,
                                        language=language, options=options)
            sumed_up_itineraries.Status = ResponseStatusType(Code=StatusCodeEnum.OK)
        except MisApiException as exc:
            resp_code = 500
            sumed_up_itineraries = SumedUpItinerariesResponseType(
                                            Status=ResponseStatusType(Code=exc.error_code))
        except:
            logging.error(format_exc())
            resp_code = 500
            sumed_up_itineraries = SumedUpItinerariesResponseType(
                                            Status=ResponseStatusType(Code=StatusCodeEnum.INTERNAL_ERROR))

        request_duration = datetime.datetime.now() - request_start_date
        sumed_up_itineraries.Status.RuntimeDuration = request_duration.total_seconds()
        resp_data = {'SumedUpItinerariesResponseType' : \
                     marshal(sumed_up_itineraries, sumed_up_itineraries_response_type)}

        # TODO handle errors
        return Response(json.dumps(resp_data),
                        status=resp_code, mimetype='application/json')
