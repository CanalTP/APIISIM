import Queue, logging
import json, traceback, httplib2
from datetime import datetime, timedelta
import threading
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker, scoped_session, aliased
import metabase
from geoalchemy2 import Geography
from geoalchemy2.functions import GenericFunction, ST_DWithin
from mod_pywebsocket import msgutil
import os
from common.plan_trip import *
from common.mis_plan_summed_up_trip import LocationContextType, \
                                           SummedUpItinerariesRequestType, \
                                           SummedUpItinerariesResponseType, \
                                           StatusType, SummedUpTripType
from common.mis_plan_trip import ItineraryRequestType, multiDeparturesType, \
                                 multiArrivalsType, ItineraryResponseType
from common import AlgorithmEnum, SelfDriveModeEnum, TripPartEnum, string_to_bool, \
                   TransportModeEnum, PlanSearchOptions, PlanTripStatusEnum, \
                   PlanTripErrorEnum, OUTPUT_ENCODING, StatusCodeEnum, \
                   xsd_duration_to_timedelta, parse_location_context
from common.marshalling import marshal, itinerary_request_type, \
                               summed_up_itineraries_request_type, \
                               summed_up_trip_type, \
                               plan_trip_existence_notification_response_type, \
                               plan_trip_notification_response_type, \
                               plan_trip_response_type, ending_search_type, \
                               starting_search_type, \
                               plan_trip_cancellation_response_type, DATE_FORMAT


MAX_TRACE_LENGTH = 3
SURROUNDING_MISES_MAX_DISTANCE = 400 # In meters


class TraceStop(LocationContextType):
    def __init__(self, *args, **kwargs):
        super(TraceStop, self).__init__(*args, **kwargs)
        self.departure_time = None
        self.arrival_time = None

    def __eq__(self, other):
        return self.PlaceTypeId == other.PlaceTypeId

    def __repr__(self):
        return ("<TraceStop(PlaceTypeId='%s')>" % \
                (self.PlaceTypeId)) \
                .encode(OUTPUT_ENCODING)


def init_logging():
    handler = logging.FileHandler(
                    os.environ.get("PLANNER_LOG_FILE", "") or "/tmp/meta_planner.log")
    formatter = logging.Formatter('%(asctime)s <%(thread)d> [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)


class ST_GeogFromText(GenericFunction):
    name = 'ST_GeogFromText'
    type = Geography


def log_error(func):
    def decorator(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            return result
        except Exception as e:
            logging.error("Class <%s>: %s\n%s", self.__class__.__name__,
                          e, traceback.format_exc())
            raise

    return decorator


def benchmark(func):
    def decorator(*args, **kwargs):
        start_date = datetime.now()
        logging.debug("%s(%s %s)|START: %s", func.__name__, args, kwargs, start_date)

        result = func(*args, **kwargs)

        end_date = datetime.now()
        logging.debug("%s(%s %s)|END: %s|DURATION: %ss",
            func.__name__, args, kwargs, end_date,
            (end_date - start_date).total_seconds())
        return result

    return decorator


def parse_end_point(point, step_end_point=False):
    if step_end_point:
        ret = StepEndPointType()
        ret.PassThrough = point.get("PassThrough", False)
    else:
        ret = EndPointType()

    place = TripStopPlaceType()
    p = point["TripStopPlace"]
    place.id = p["id"]
    place.Name = p.get("Name", "")
    place.CityCode = p.get("CityCode", "")
    place.CityName = p.get("CityName", "")
    place.TypeOfPlaceRef = p.get("TypeOfPlaceRef", "")
    if "Position" in p:
        place.Position = LocationStructure(
                            Latitude=p["Position"]["Latitude"],
                            Longitude=p["Position"]["Longitude"])

    ret.TripStopPlace = place
    ret.DateTime = datetime.strptime(point["DateTime"], DATE_FORMAT)
    return ret


def parse_summed_up_trips(trips):
    ret = [] # [summedUpTripType]
    for trip in trips:
        departure = parse_end_point(trip["Departure"])
        arrival = parse_end_point(trip["Arrival"])
        ret.append(SummedUpTripType(
                        Departure=departure, Arrival=arrival,
                        InterchangeCount=trip["InterchangeCount"],
                        InterchangeDuration=trip["InterchangeDuration"]))
    return ret


def parse_steps(steps):
    ret = [] # [StepType]
    for step in steps:
        ret.append(
                StepType(
                    Departure=parse_end_point(step["Departure"], step_end_point=True),
                    Arrival=parse_end_point(step["Arrival"], step_end_point=True),
                    Duration=step["Duration"]))
    return ret


def parse_sections(sections):
    ret = []
    for section in sections:
        ptr = None
        leg = None
        if "PTRide" in section:
            p = section["PTRide"]
            ptr = PTRideType()
            ptr.ptNetworkRef = p["ptNetworkRef"]
            ptr.lineRef = p["lineRef"]
            ptr.PublicTransportMode = p["PublicTransportMode"]
            ptr.Departure = parse_end_point(p["Departure"])
            ptr.Arrival = parse_end_point(p["Arrival"])
            ptr.Duration = p["Duration"]
            ptr.Distance = p["Distance"]
            ptr.steps = parse_steps(p["steps"])
        elif "Leg" in section:
            l = section["Leg"]
            leg = LegType()
            leg.SelfDriveMode = l["SelfDriveMode"]
            leg.Departure = parse_end_point(l["Departure"])
            leg.Arrival = parse_end_point(l["Arrival"])
            leg.Duration = l["Duration"]

        ret.append(SectionType(
                        PartialTripId=section.get("PartialTripId", ""),
                        PTRide=ptr, Leg=leg))

    return ret


def parse_detailed_trip(trip):
    ret = TripType()

    ret.Departure = parse_end_point(trip["Departure"])
    ret.Arrival = parse_end_point(trip["Arrival"])
    ret.Duration = trip["Duration"]
    ret.Distance = trip.get("Distance", 0)
    ret.Disrupted = trip.get("Disrupted", False)
    ret.InterchangeNumber = trip.get("InterchangeNumber", 0)
    ret.sections = parse_sections(trip["sections"])

    return ret


################################################################################

def _marshal_ItineraryRequestType(self):
    return marshal(self, itinerary_request_type)
ItineraryRequestType.marshal = _marshal_ItineraryRequestType

def _marshal_SummedUpItinerariesRequestType(self):
    return marshal(self, summed_up_itineraries_request_type)
SummedUpItinerariesRequestType.marshal = _marshal_SummedUpItinerariesRequestType

def _marshal_SummedUpTripType(self):
    return {"SummedUpTripType" : marshal(self, summed_up_trip_type)}
SummedUpTripType.marshal = _marshal_SummedUpTripType

def _marshal_PlanTripExistenceNotificationResponseType(self):
    return {"PlanTripExistenceNotificationResponseType" : marshal(self, plan_trip_existence_notification_response_type)}
PlanTripExistenceNotificationResponseType.marshal = _marshal_PlanTripExistenceNotificationResponseType

def _marshal_PlanTripNotificationResponseType(self):
    return {"PlanTripNotificationResponseType" : marshal(self, plan_trip_notification_response_type)}
PlanTripNotificationResponseType.marshal = _marshal_PlanTripNotificationResponseType

def _marshal_PlanTripResponse(self):
    return {"PlanTripResponse" : marshal(self, plan_trip_response_type)}
PlanTripResponse.marshal = _marshal_PlanTripResponse

def _marshal_EndingSearch(self):
    return {"EndingSearch" : marshal(self, ending_search_type)}
EndingSearch.marshal = _marshal_EndingSearch

def _marshal_StartingSearch(self):
    return {"StartingSearch" : marshal(self, starting_search_type)}
StartingSearch.marshal = _marshal_StartingSearch

class PlanTripCancellationResponse(AbstractNotificationResponseType):
    def marshal(self):
        return {"PlanTripCancellationResponse" : marshal(self, plan_trip_cancellation_response_type)}

def _repr(self):
    return unicode(self.marshal()).encode(OUTPUT_ENCODING)

PlanTripRequestType.__repr__ = _repr
ItineraryRequestType.__repr__ = _repr
SummedUpItinerariesRequestType.__repr__ = _repr
SummedUpTripType.__repr__ = _repr

################################################################################


class MisApi(object):
    def __init__(self, id):
        db_session = Session()
        mis = db_session.query(metabase.Mis).filter_by(id=id).one()
        self._api_url = mis.api_url
        self._api_key = mis.api_key
        self._name = mis.name
        self._http = httplib2.Http("/tmp/.planner_cache")
        Session.remove()
        db_session.close()
        db_session.bind.dispose()

    def get_name(self):
        return self._name

    def get_api_url(self):
        return self._api_url

    def _send_request(self, resource, data):
        url = self._api_url + ("/" if self._api_url[-1] != "/" else "") + resource
        logging.debug("<MIS REQUEST>\n"
                      "URL: \n%s\n"
                      "DATA: \n%s", url, json.dumps(data))
        headers = {'Content-type': 'application/json',
                   'Authorization' : self._api_key}
        resp, content = self._http.request(url, "POST", headers=headers, body=json.dumps(data))
        if resp.status != 200:
            # TODO error handling
            logging.error("POST <%s> FAILED: %s" % (url, resp.status))

        logging.debug("Response: \n%s", resp)
        logging.debug("Content: \n%s", content)
        return resp, json.loads(content)

    # request is an object of class ItineraryRequestType
    def get_itinerary(self, request):
        ret = ItineraryResponseType()

        data = request.marshal()
        resp, content = self._send_request("itineraries", data)
        # TODO error handling
        content = content["ItineraryResponseType"]
        ret.RequestId = content["RequestId"]
        ret.Status = StatusType(content["Status"]["Code"],
                                content["Status"].get("RuntimeDuration", 0))
        if ret.Status.Code != StatusCodeEnum.OK:
            raise Exception("<get_itinerary> %s" % ret.Status.Code)
        ret.DetailedTrip = parse_detailed_trip(content.get("DetailedTrip", None))

        return ret

    # request is an object of class SummedUpItinerariesRequestType
    def get_summed_up_itineraries(self, request):
        ret = SummedUpItinerariesResponseType()

        # data = {"SummedUpItinerariesRequestType" : request.marshal()}
        data = request.marshal()
        resp, content = self._send_request("summed_up_itineraries", data)
        # TODO error handling
        content = content["SummedUpItinerariesResponseType"]
        ret.RequestId = content["RequestId"]
        ret.Status = StatusType(content["Status"]["Code"],
                                content["Status"].get("RuntimeDuration", 0))
        if ret.Status.Code != StatusCodeEnum.OK:
            raise Exception("<get_summed_up_itineraries> %s" % ret.Status.Code)
        ret.summedUpTrips = parse_summed_up_trips(content.get("summedUpTrips", []))

        return ret

    def __repr__(self):
        return ("<MisApi(name='%s')>" % \
                (self._name)) \
                .encode(OUTPUT_ENCODING)


class WorkerThread(threading.Thread):
    def __init__(self, params, job_queue, notif_queue):
        threading.Thread.__init__(self)
        self._params = params
        self._job_queue = job_queue
        self._notif_queue = notif_queue
        self.exit_code = 1

    @log_error
    def run(self):
        logging.debug("Worker Thread started")
        trace = self._job_queue.get()
        trip_calculator = PlanTripCalculator(self._params, self._notif_queue)
        try:
            trip_calculator.compute_trip(trace)
            self.exit_code = 0
        except Exception as e:
            logging.error("compute_trip(%s): %s\n%s", trace, e, traceback.format_exc())
        logging.debug("Worker Thread finished")


"""
    Parse request dict and return a new PlanTripRequestType object with its
    attributes set accordingly.
"""
def parse_request(request):
    ret = PlanTripRequestType()

    request = request.get("PlanTripRequestType", None)
    if not request:
        return None

    # Required
    ret.clientRequestId = request["clientRequestId"]
    departure_time = request.get("DepartureTime", "")
    arrival_time = request.get("ArrivalTime", "")
    if departure_time and arrival_time:
        logging.error("Request cannot have both departure time and arrival time")
        return None
    if not departure_time and not arrival_time:
        logging.error("No departure/arrival time given")
        return None
    try:
        if departure_time:
            ret.DepartureTime = datetime.strptime(departure_time, DATE_FORMAT)
        if arrival_time:
            ret.ArrivalTime = datetime.strptime(arrival_time, DATE_FORMAT)
    except ValueError as exc:
        logging.error("DateTime format error: %s", exc)
        return None

    try:
        ret.Departure = parse_location_context(request["Departure"])
        ret.Arrival = parse_location_context(request["Arrival"])
    except Exception as e:
        logging.error(e)
        return None
    if not ret.Departure or not ret.Arrival:
        logging.error("Missing departure or arrival")
        return None

    # Optional
    ret.MaxTrips = request.get('MaxTrips', 0)
    ret.Algorithm = request.get('Algorithm', AlgorithmEnum.CLASSIC)
    if not AlgorithmEnum.validate(ret.Algorithm):
        logging.error("Invalid algorithm")
        return None

    ret.modes = request.get('modes', [TransportModeEnum.ALL])
    for m in ret.modes:
        if not TransportModeEnum.validate(m):
            logging.error("Invalid transport mode")
            return None

    ret.selfDriveConditions = []
    for c in request.get('selfDriveConditions', []):
        condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                SelfDriveMode=c.get("SelfDriveMode", ""))
        if not TripPartEnum.validate(condition.TripPart) or \
           not SelfDriveModeEnum.validate(condition.SelfDriveMode):
           logging.error("Invalid self drive condition")
           return None
        ret.selfDriveConditions.append(condition)

    ret.AccessibilityConstraint = string_to_bool(request.get('AccessibilityConstraint', "False"))
    ret.Language = request.get('Language', "")

    return ret


def stop_to_trace_stop(stop):
    ret = TraceStop()

    ret.AccessTime = timedelta()
    ret.PlaceTypeId = stop.code
    l = LocationStructure()
    l.Longitude = stop.lat
    l.Latitude  = stop.long
    ret.Position = l

    return ret

# trips is [(MisApi, DetailedTrip)]
def create_full_notification(request_id, trips, runtime_duration):
    composed_trip = None
    if trips:
        composed_trip = ComposedTripType()
        # TODO
        composed_trip.id = request_id + "_"
        composed_trip.Departure = trips[0][1].Departure
        composed_trip.Arrival = trips[-1][1].Arrival
        composed_trip.Duration = sum([xsd_duration_to_timedelta(x[1].Duration) for x in trips], timedelta())
        composed_trip.InterchangeNumber = sum([x[1].InterchangeNumber for x in trips])
        # TODO set partial ids in sections
        composed_trip.sections = []
        for s in [x[1].sections for x in trips]:
            composed_trip.sections.extend(s)
        composed_trip.partialTrips = []
        for mis_api, trip in trips:
            partial_trip = PartialTripType()
            # TODO
            partial_trip.id = 0
            partial_trip.Provider = ProviderType(
                                        Name=mis_api.get_name(),
                                        Url=mis_api.get_api_url())
            partial_trip.Departure = trip.Departure
            partial_trip.Arrival = trip.Arrival
            partial_trip.Duration = xsd_duration_to_timedelta(trip.Duration)
            composed_trip.partialTrips.append(partial_trip)

    return PlanTripNotificationResponseType(
                RequestId=request_id,
                RuntimeDuration=runtime_duration,
                ComposedTrip=[composed_trip] if composed_trip else [])


class PlanTripCalculator(object):
    # Maximum number of transfers between 2 MIS. We need that limit to have acceptable
    # performance when using MIS that don't support n-m itineraries requests.
    MAX_TRANSFERS = 10

    def __init__(self, params, notif_queue):
        self._db_session = Session()
        self._params = params
        self._notif_queue = notif_queue

    @benchmark
    def _get_transfers(self, mis1_id, mis2_id):
        # {mis1_id : [(transfer, stop_mis1, stop_mis2)],
        #  mis2_id : [(transfer, stop_mis2, stop_mis1)]}
        # To ease further processing (in compute_trip()), stops are returned
        # as TraceStop objects, not as metabase.Stop objects.
        ret = {mis1_id : [], mis2_id: []}
        subq = self._db_session.query(metabase.TransferMis.transfer_id) \
                                        .filter(or_(and_(metabase.TransferMis.mis1_id==mis1_id,
                                                         metabase.TransferMis.mis2_id==mis2_id),
                                                    and_(metabase.TransferMis.mis1_id==mis2_id,
                                                         metabase.TransferMis.mis2_id==mis1_id))) \
                                        .order_by(metabase.TransferMis.transfer_id) \
                                        .limit(self.MAX_TRANSFERS) \
                                        .subquery()
        # logging.debug("transfers_ids : %s", transfers_ids)
        s1 = aliased(metabase.Stop)
        s2 = aliased(metabase.Stop)

        results = self._db_session.query(metabase.Transfer, s1, s2) \
                                  .filter(metabase.Transfer.id == subq.c.transfer_id) \
                                  .filter(and_(metabase.Transfer.stop1_id == s1.id),
                                               metabase.Transfer.stop2_id == s2.id) \
                                  .all()
        for t, s1, s2 in results:
            l1 = stop_to_trace_stop(s1)
            l2 = stop_to_trace_stop(s2)
            if s1.mis_id == mis1_id: # implies s2.mis_id == mis2_id
                ret[mis1_id].append((t, l1, l2))
                ret[mis2_id].append((t, l2, l1))
            elif s1.mis_id == mis2_id: # implies s2.mis_id == mis1_id
                ret[mis2_id].append((t, l1, l2))
                ret[mis1_id].append((t, l2, l1))
            else:
                raise Exception("Inconsistency in database, transfer %s is"
                                "not coherent with its stops %s %s", t, s1, s2)

        # logging.debug("ret: len %s len %s\n%s", len(ret[mis1_id]), len(ret[mis2_id]), ret)
        return ret


    """
        Return set of MIS that have at least one stop point whose distance to given
        postion is less than max_distance. Also ensure that returned MIS are available at
        given date.
    """
    @benchmark
    def _get_surrounding_mises(self, position, date):
        ret = set() # ([mis_id])
        all_mises = self._db_session.query(metabase.Mis).all()

        for mis in all_mises:
            if self._db_session.query(metabase.Stop.id) \
                               .filter(metabase.Stop.mis_id == mis.id) \
                               .filter(
                                    ST_DWithin(
                                        metabase.Stop.geog,
                                        ST_GeogFromText('POINT(%s %s)' \
                                            % (position.Longitude, position.Latitude)),
                                        SURROUNDING_MISES_MAX_DISTANCE)) \
                               .count() > 0 \
               and (mis.start_date <= date <= mis.end_date):
                ret.add(mis.id)

        logging.debug("MISes surrounding point (%s %s): %s",
                      position.Longitude, position.Latitude, ret)
        return ret


    def _get_mis_modes(self, mis_id):
        return set([x[0] for x in \
                    self._db_session.query(metabase.Mode.code) \
                                    .filter(metabase.MisMode.mis_id == mis_id) \
                                    .filter(metabase.Mode.id == metabase.MisMode.mode_id) \
                                    .all()])


    @benchmark
    def _get_connected_mises(self, mis_id):
        s1 = set([x[0] for x in \
                  self._db_session.query(metabase.MisConnection.mis1_id) \
                                  .filter(metabase.MisConnection.mis2_id == mis_id) \
                                  .all()])
        s2 = set([x[0] for x in \
                  self._db_session.query(metabase.MisConnection.mis2_id) \
                                  .filter(metabase.MisConnection.mis1_id == mis_id) \
                                  .all()])
        return s1 | s2


    @benchmark
    def _get_mis_traces(self, departure_mises, arrival_mises, max_trace_length):
        ret = [] # [[mis_id]] each mis_id list is a trace
        if max_trace_length < 1:
            logging.warning("Requesting Mis traces with max_trace_length < 1")
            return ret

        # Add all Mis in common
        for mis in (departure_mises & arrival_mises):
            ret.append([mis])
        if max_trace_length == 1:
            return ret

        for mis_id in departure_mises:
            connected_mises = self._get_connected_mises(mis_id)
            for subtrace in self._get_mis_traces(connected_mises,
                                        arrival_mises, max_trace_length - 1):
                if not mis_id in subtrace:
                    subtrace.insert(0, mis_id)
                    ret.append(subtrace)

        return ret


    @benchmark
    def compute_traces(self):
        # Get Mis near departure and arrival points
        date = self._params.DepartureTime or self._params.ArrivalTime
        departure_mises = self._get_surrounding_mises(self._params.Departure.Position, date)
        arrival_mises = self._get_surrounding_mises(self._params.Arrival.Position, date)

        # Filter out Mis that don't support at least one of the requested modes
        if self._params.modes and not TransportModeEnum.ALL in self._params.modes:
            departure_mises = set([x for x in departure_mises if (set(self._params.modes) & self._get_mis_modes(x))])
            arrival_mises = set([x for x in arrival_mises if (set(self._params.modes) & self._get_mis_modes(x))])

        logging.debug("departure_mises %s", departure_mises)
        logging.debug("arrival_mises %s", arrival_mises)

        return self._get_mis_traces(departure_mises, arrival_mises, MAX_TRACE_LENGTH)

    @benchmark
    def _get_detailed_trace(self, mis_trace):
        i = 0
        ret = []
        # [
        #   (
        #     MisApi,
        #     [TraceStop], # departures
        #     [TraceStop], # arrivals
        #     [TraceStop], # linked_stops (stops linked to arrivals via a transfer)
        #     [timedelta]   # transfer_durations
        #   )
        # ]
        while True:
            # Divide trace in chunks of 3 MIS
            chunk = mis_trace[i:i+3]
            if not chunk:
                break
            logging.debug("CHUNK: %s", chunk)

            trace_departure = self._params.Departure if i == 0 else None
            trace_arrival = self._params.Arrival if len(mis_trace) <= (i + 3) else None
            mis1_id = chunk[0]
            mis2_id = chunk[1] if len(chunk) > 1 else 0
            mis3_id = chunk[2] if len(chunk) > 2 else 0
            mis1_api = MisApi(mis1_id) if mis1_id else None
            mis2_api = MisApi(mis2_id) if mis2_id else None
            mis3_api = MisApi(mis3_id) if mis3_id else None
            chunk_transfers = {mis1_id : {mis2_id : [], mis3_id : []},
                               mis2_id : {mis1_id : [], mis3_id : []},
                               mis3_id : {mis1_id : [], mis2_id : []}}

            # logging.debug("mis1_id: %s, mis2_id: %s, mis3_id: %s", mis1_id, mis2_id, mis3_id)
            # logging.debug("trace_arrival: %s", trace_arrival)
            for x, y in [(mis1_id, mis2_id), (mis2_id, mis3_id)]:
                if not x or not y:
                    continue
                t = self._get_transfers(x, y)
                chunk_transfers[x][y] = t[x]
                chunk_transfers[y][x] = t[y]

            if trace_departure:
                ret = [(mis1_api,
                        [trace_departure],
                        [x[1] for x in chunk_transfers[mis1_id][mis2_id]],
                        [x[2] for x in chunk_transfers[mis1_id][mis2_id]],
                        [timedelta(seconds=x[0].duration) for x in chunk_transfers[mis1_id][mis2_id]])]

            if mis3_id:
                ret.append(
                    (mis2_api,
                     [x[2] for x in chunk_transfers[mis1_id][mis2_id]],
                     [x[1] for x in chunk_transfers[mis2_id][mis3_id]],
                     [x[2] for x in chunk_transfers[mis2_id][mis3_id]],
                     [timedelta(seconds=x[0].duration) for x in chunk_transfers[mis2_id][mis3_id]]))

                if trace_arrival:
                    ret.append(
                        (mis3_api,
                         [x[2] for x in chunk_transfers[mis2_id][mis3_id]],
                         [trace_arrival],
                         None,
                         None))
                    break
            else:
                if trace_arrival:
                    ret.append(
                        (mis2_api,
                         [x[2] for x in chunk_transfers[mis1_id][mis2_id]],
                         [trace_arrival],
                         None,
                         None))
                    break
            i += 1

        return ret


    @benchmark
    def compute_trip(self, mis_trace):
        start_date = datetime.now()
        # TODO do it for arrival_at trip

        # Return best trip, which is a list of partial trips.
        ret = [] #  [DetailedTrip]

        if not mis_trace:
            raise Exception("Empty mis_trace")

        # Check that first and last MIS support departure/arrival points with
        # geographic coordinates.
        for mis_id in [mis_trace[0], mis_trace[-1]]:
            if not self._db_session.query(metabase.Mis.geographic_position_compliant) \
                                   .filter_by(id=mis_id) \
                                   .one()[0]:
                raise Exception("First or last Mis is not geographic_position_compliant")

        detailed_request = ItineraryRequestType()
        detailed_request.Algorithm = self._params.Algorithm
        detailed_request.modes = self._params.modes
        detailed_request.selfDriveConditions = self._params.selfDriveConditions
        detailed_request.AccessibilityConstraint = self._params.AccessibilityConstraint
        detailed_request.Language = self._params.Language

        # If there is only one MIS in the trace, just do a detailed request on the
        # given MIS.
        if len(mis_trace) == 1:
            detailed_request.multiDepartures = multiDeparturesType()
            detailed_request.multiDepartures.Departure = [self._params.Departure]
            detailed_request.multiDepartures.Arrival = self._params.Arrival
            detailed_request.DepartureTime = self._params.DepartureTime
            detailed_request.ArrivalTime = self._params.ArrivalTime
            mis_api = MisApi(mis_trace[0])
            resp = mis_api.get_itinerary(detailed_request)
            ret.append((mis_api, resp.DetailedTrip))
            notif = create_full_notification(self._params.clientRequestId, ret, datetime.now() - start_date)
            self._notif_queue.put(notif)
            return ret

        summed_up_request = SummedUpItinerariesRequestType()
        summed_up_request.Algorithm = self._params.Algorithm
        summed_up_request.modes = self._params.modes
        summed_up_request.selfDriveConditions = self._params.selfDriveConditions
        summed_up_request.AccessibilityConstraint = self._params.AccessibilityConstraint
        summed_up_request.Language = self._params.Language

        # Minimum arrival_time to arrival
        best_arrival_time = None

        detailed_trace = self._get_detailed_trace(mis_trace)
        # logging.debug("DETAILED_TRACE %s", detailed_trace)

        # Do all non detailed requests
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace[0:-1]:
            summed_up_request.departures = list(set(departures))
            summed_up_request.arrivals = list(set(arrivals))
            if not summed_up_request.DepartureTime:
                summed_up_request.DepartureTime = self._params.DepartureTime
            else:
                summed_up_request.DepartureTime = min([x.arrival_time for x in departures])
                for d in departures:
                    d.AccessTime = d.arrival_time - summed_up_request.DepartureTime
            summed_up_request.ArrivalTime = None
            summed_up_request.options = []
            resp = mis_api.get_summed_up_itineraries(summed_up_request)
            for trip in resp.summedUpTrips:
                # logging.debug("TRIP: %s", trip)
                for stop in arrivals:
                    if stop.PlaceTypeId == trip.Arrival.TripStopPlace.id:
                        # logging.debug("MATCH: %s", stop.PlaceTypeId)
                        stop.arrival_time = trip.Arrival.DateTime
            # To have linked_stops arrival_time, just add transfer time to request results
            for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                l.arrival_time = a.arrival_time + t

        # Do non-detailed optimized request (only one, always)
        mis_api, departures, arrivals, linked_stops, transfer_durations = detailed_trace[-1]
        summed_up_request.departures = list(set(departures))
        summed_up_request.arrivals = list(set(arrivals))
        summed_up_request.DepartureTime = min([x.arrival_time for x in departures])
        for d in departures:
            d.AccessTime = d.arrival_time - summed_up_request.DepartureTime
        summed_up_request.ArrivalTime = None
        summed_up_request.options = [PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED]
        resp = mis_api.get_summed_up_itineraries(summed_up_request)

        best_arrival_time = resp.summedUpTrips[0].Arrival.DateTime
        for trip in resp.summedUpTrips:
            for stop in departures:
                if stop.PlaceTypeId == trip.Departure.TripStopPlace.id:
                    stop.departure_time = trip.Departure.DateTime

        # Substract transfer time from previous request results
        mis_api, departures, arrivals, linked_stops, transfer_durations = detailed_trace[-2]
        for a, l, t in zip(arrivals, linked_stops, transfer_durations):
            a.departure_time = l.departure_time - t
        notif = PlanTripExistenceNotificationResponseType(
                    RequestId=self._params.clientRequestId, DepartureTime=self._params.DepartureTime,
                    ArrivalTime=best_arrival_time,
                    Departure=self._params.Departure, Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        # Do arrival_at non-detailed request
        if len(detailed_trace) > 2:
            summed_up_request.departures = list(set(departures))
            summed_up_request.arrivals = list(set(arrivals))
            summed_up_request.DepartureTime = None
            summed_up_request.ArrivalTime = min([x.departure_time for x in arrivals])
            for a in arrivals:
                a.AccessTime = a.departure_time - summed_up_request.ArrivalTime
            summed_up_request.options = []
            resp = mis_api.get_summed_up_itineraries(summed_up_request)

            for trip in resp.summedUpTrips:
                for stop in departures:
                    if stop.PlaceTypeId == trip.Departure.TripStopPlace.id:
                        stop.departure_time = trip.Departure.DateTime

            # Substract transfer time from previous request results
            _, departures, arrivals, linked_stops, transfer_durations = detailed_trace[-3]
            for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                a.departure_time = l.departure_time - t

        # Do all detailed requests.
        # Best arrival stop from previous request, will become the departure
        # point of the next request.
        prev_stop = None
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace:
            # Arrival times are embedded in departures/arrivals objects
            detailed_request.ArrivalTime = None
            if not prev_stop:
                # At first, do an arrival_at request.
                prev_stop = departures[0]
                detailed_request.DepartureTime = None
                detailed_request.ArrivalTime = min([x.departure_time for x in arrivals])
                for a in arrivals:
                   a.AccessTime = a.departure_time - detailed_request.ArrivalTime
            else:
                # All other requests are departure_at requests.
                detailed_request.DepartureTime = prev_stop.departure_time
                detailed_request.ArrivalTime = None
            detailed_request.multiArrivals = multiArrivalsType()
            detailed_request.multiArrivals.Departure = prev_stop
            detailed_request.multiArrivals.Arrival = list(set(arrivals))
            resp = mis_api.get_itinerary(detailed_request)
            ret.append((mis_api, resp.DetailedTrip))

            if not linked_stops:
                # We are at the end of the trace.
                break

            # Request result gives us the best arrival stop, the next step
            # is to find all stops that are linked to this stop via a transfer.
            best_stops = []
            for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                if a.PlaceTypeId == resp.DetailedTrip.Arrival.TripStopPlace.id:
                    l.departure_time = resp.DetailedTrip.Arrival.DateTime + t
                    best_stops.append(l)
            # If we find several stops linked to the best arrival stop, choose
            # the one which has best departure_time.
            best_stops.sort(key=lambda x: x.departure_time)
            prev_stop = best_stops[0]

        notif = create_full_notification(self._params.clientRequestId, ret, datetime.now() - start_date)
        self._notif_queue.put(notif)

        return ret

    def __del__(self):
        logging.debug("Deleting PlanTripCalculator instance")
        if self._db_session:
            Session.remove()
            self._db_session.close()
            self._db_session.bind.dispose()


# Check if we've received a cancellation request
class CancellationListener(threading.Thread):
    def __init__(self, connection, params, queue):
        threading.Thread.__init__(self)
        self._connection = connection
        self._params = params
        self._queue = queue

    @log_error
    def run(self):
        logging.info("<CancellationListener> Thread started")
        while True:
            msg = self._connection.ws_stream.receive_message()
            logging.debug("<CancellationListener> Received message %s", msg)
            # if msg is None:
            #     # Connection has been closed
            #     break
            try:
                msg = json.loads(msg)
                if "PlanTripCancellationRequest" in msg \
                    and msg["PlanTripCancellationRequest"]["RequestId"] == self._params.clientRequestId:
                    self._queue.put("CANCEL")
                    break
            except:
                pass
        logging.info("<CancellationListener> Thread finished")


class CalculationManager(threading.Thread):
    def __init__(self, params, traces, notif_queue, termination_queue):
        threading.Thread.__init__(self)
        self._params = params
        self._traces = traces
        self._termination_queue = termination_queue
        self._notif_queue = notif_queue

    @log_error
    def run(self):
        logging.info("<CalculationManager> thread started")
        job_queue = Queue.Queue()
        i = 0
        workers = []
        for trace in self._traces:
            i += 1
            worker = WorkerThread(self._params, job_queue, self._notif_queue)
            workers.append(worker)
            job_queue.put(trace)
            worker.start()
            worker.join() # TODO delete that, just for debugging
            if i == self._params.MaxTrips:
                break
        for w in workers:
            w.join()
        self._termination_queue.put("FINISHED")
        logging.info("<CalculationManager> thread finished")


class NotificationThread(threading.Thread):
    def __init__(self, connection, queue):
        threading.Thread.__init__(self)
        self._connection = connection
        self._queue = queue

    @log_error
    def run(self):
        start_date = datetime.now()
        existence_notifications_sent = 0
        notifications_sent = 0
        while True:
            logging.debug("Waiting for notification...")
            notif = self._queue.get()
            if notif is None:
                self._queue.task_done()
                logging.debug("Notification Thread finished")
                break
            if isinstance(notif, EndingSearch):
                notif.ExistenceNotificationsSent = existence_notifications_sent
                notif.NotificationsSent = notifications_sent
                notif.Runtime = datetime.now() - start_date
            elif isinstance(notif, PlanTripNotificationResponseType):
                notifications_sent += 1
            elif isinstance(notif, PlanTripExistenceNotificationResponseType):
                existence_notifications_sent += 1
            logging.debug("Sending notification...")
            self._connection.ws_stream.send_message(json.dumps(notif.marshal()), binary=False)
            logging.debug("Notification sent")
            self._queue.task_done()

    def stop(self):
        self._queue.put(None)


class ConnectionHandler(object):
    def __init__(self, connection):
        self._connection = connection
        self._request_id = 0
        self._notif_queue = None
        self._notif_thread = None
        self._calculation_thread = None
        self._cancellation_thread = None

    def _send_status(self, status, error=None):
        logging.error("Sending <%s> status", status)
        notif = PlanTripResponse()
        notif.Status = status
        notif.RequestId = self._request_id
        if error:
            notif.errors = [error]
        self._notif_queue.put(notif)

    @log_error
    def process(self):
        termination_queue = Queue.Queue()
        notif_queue = Queue.Queue()
        self._notif_queue = notif_queue

        request = self._connection.ws_stream.receive_message()
        self._notif_thread = NotificationThread(self._connection, notif_queue)
        self._notif_thread.start()
        logging.debug("REQUEST: %s", request)
        # logging.debug(content)
        request = json.loads(request)
        params = parse_request(request)
        if not params:
            self._send_status(PlanTripStatusEnum.BAD_REQUEST)
            return
        self._request_id = params.clientRequestId

        try:
            trip_calculator = PlanTripCalculator(params, notif_queue)
            traces = trip_calculator.compute_traces()
        except Exception as e:
            logging.error("compute_traces: %s %s", e, traceback.format_exc())
            self._send_status(PlanTripStatusEnum.SERVER_ERROR)
            return

        logging.info("MIS TRACES: %s", traces)
        self._send_status(PlanTripStatusEnum.OK)
        notif_queue.put(StartingSearch(MaxComposedTripSearched=len(traces), RequestId=self._request_id))
        self._cancellation_thread = CancellationListener(self._connection, params, termination_queue)
        self._cancellation_thread.start()
        self._calculation_thread = CalculationManager(params, traces, notif_queue, termination_queue)
        self._calculation_thread.start()

        msg = termination_queue.get()
        if msg == "CANCEL":
            notif_queue.put(PlanTripCancellationResponse(RequestId=self._request_id))
            logging.debug("Request cancelled by client")
        else:
            notif_queue.put(EndingSearch(MaxComposedTripSearched=len(traces),
                                         RequestId=self._request_id,
                                         Status=PlanTripStatusEnum.OK))
            logging.info("Request finished")

    def __del__(self):
        logging.debug("Deleting ConnectionHandler instance")
        if self._notif_thread:
            self._notif_thread.stop()
            self._notif_thread.join()
        if self._calculation_thread:
            self._calculation_thread.join()


def web_socket_do_extra_handshake(connection):
    # This example handler accepts any connection.
    pass  # Always accept.


@benchmark
def web_socket_transfer_data(connection):
    connection_handler = ConnectionHandler(connection)
    connection_handler.process()
    del connection_handler


init_logging()
# Create engine used to connect to database
# db_url = "postgresql+psycopg2://postgres:postgres@localhost/afimb_db3"
db_url = os.environ.get("PLANNER_DB_URL", "") or \
                "postgresql+psycopg2://postgres:postgres@localhost/afimb_stubs_db"
db_engine = create_engine(db_url, echo=False)
# Class that will be instantiated by every thread to create their own thread-local sessions
Session = scoped_session(sessionmaker(bind=db_engine, expire_on_commit=False))
