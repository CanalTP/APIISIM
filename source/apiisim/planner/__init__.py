import logging, os, json, httplib2
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from apiisim.common.mis_plan_trip import ItineraryResponseType, ItineraryRequestType
from apiisim.common.plan_trip import PlanTripRequestType, \
                                     PlanTripExistenceNotificationResponseType, \
                                     PlanTripNotificationResponseType, \
                                     PlanTripResponse, EndingSearch, StartingSearch, \
                                     AbstractNotificationResponseType, StepEndPointType, \
                                     EndPointType, TripStopPlaceType, LocationStructure, \
                                     TripType, StepType, PTRideType, LegType, SectionType, \
                                     PartialTripType, ComposedTripType, ProviderType
from apiisim.common.mis_plan_summed_up_trip import LocationContextType, \
                                                   SummedUpItinerariesResponseType, \
                                                   StatusType, SummedUpTripType, \
                                                   SummedUpItinerariesRequestType
from apiisim.common import OUTPUT_ENCODING, StatusCodeEnum, xsd_duration_to_timedelta
from apiisim.common.marshalling import marshal, itinerary_request_type, \
                               summed_up_itineraries_request_type, \
                               summed_up_trip_type, \
                               plan_trip_existence_notification_response_type, \
                               plan_trip_notification_response_type, \
                               plan_trip_response_type, ending_search_type, \
                               starting_search_type, DATE_FORMAT, \
                               plan_trip_cancellation_response_type
from apiisim import metabase


class PlannerException(Exception):
    pass
class InvalidResponseException(PlannerException):
    def __init__(self):
        PlannerException.__init__(self, "MIS response is invalid")
class NoItineraryFoundException(PlannerException):
    def __init__(self):
        PlannerException.__init__(self, "No itinerary found")
class BadRequestException(PlannerException):
    def __init__(self, message, field=""):
        PlannerException.__init__(self, message)
        self.field = field

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

def benchmark(func):
    def decorator(*args, **kwargs):
        start_date = datetime.now()
        logging.debug("%s(%s %s) | START: %s", func.__name__, args, kwargs, start_date)

        result = func(*args, **kwargs)

        end_date = datetime.now()
        logging.debug("%s(%s %s) | END: %s | DURATION: %ss",
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

def parse_detailed_trip(trip):
    if not trip:
        return None

    ret = TripType()

    ret.Departure = parse_end_point(trip["Departure"])
    ret.Arrival = parse_end_point(trip["Arrival"])
    ret.Duration = xsd_duration_to_timedelta(trip["Duration"])
    ret.Distance = trip.get("Distance", 0)
    ret.Disrupted = trip.get("Disrupted", False)
    ret.InterchangeNumber = trip.get("InterchangeNumber", 0)
    ret.sections = parse_sections(trip["sections"])

    return ret

def parse_steps(steps):
    ret = [] # [StepType]
    for step in steps:
        ret.append(
                StepType(
                    id=step["id"],
                    Departure=parse_end_point(step["Departure"], step_end_point=True),
                    Arrival=parse_end_point(step["Arrival"], step_end_point=True),
                    Duration=xsd_duration_to_timedelta(step["Duration"])))
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
            ptr.Duration = xsd_duration_to_timedelta(p["Duration"])
            ptr.Distance = p["Distance"]
            ptr.steps = parse_steps(p["steps"])
        elif "Leg" in section:
            l = section["Leg"]
            leg = LegType()
            leg.SelfDriveMode = l["SelfDriveMode"]
            leg.Departure = parse_end_point(l["Departure"])
            leg.Arrival = parse_end_point(l["Arrival"])
            leg.Duration = xsd_duration_to_timedelta(l["Duration"])

        ret.append(SectionType(
                        PartialTripId=section.get("PartialTripId", ""),
                        PTRide=ptr, Leg=leg))

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

# full_trip is [(MisApi, DetailedTrip)]
def create_full_notification(request_id, trace_id, full_trip, runtime_duration):
    composed_trip = None
    if full_trip:
        composed_trip = ComposedTripType()
        composed_trip.id = trace_id
        composed_trip.Departure = full_trip[0][1].Departure
        composed_trip.Arrival = full_trip[-1][1].Arrival
        composed_trip.Duration = sum([x[1].Duration for x in full_trip], timedelta())
        composed_trip.InterchangeNumber = sum([x[1].InterchangeNumber for x in full_trip])
        composed_trip.Distance = sum([x[1].Distance for x in full_trip])
        composed_trip.sections = []
        composed_trip.partialTrips = []
        for mis_api, trip in full_trip:
            for s in trip.sections:
                s.PartialTripId = mis_api.get_name()
            composed_trip.sections.extend(trip.sections)
            partial_trip = PartialTripType()
            partial_trip.id = mis_api.get_name()
            partial_trip.Provider = ProviderType(
                                        Name=mis_api.get_name(),
                                        Url=mis_api.get_api_url())
            partial_trip.Departure = trip.Departure
            partial_trip.Arrival = trip.Arrival
            partial_trip.Duration = trip.Duration
            partial_trip.Distance = trip.Distance
            composed_trip.partialTrips.append(partial_trip)

    return PlanTripNotificationResponseType(
                RequestId=request_id,
                RuntimeDuration=runtime_duration,
                ComposedTrip=composed_trip)


class TraceStop(LocationContextType):
    def __init__(self, *args, **kwargs):
        super(TraceStop, self).__init__(*args, **kwargs)
        self.departure_time = None
        self.arrival_time = None

    def __eq__(self, other):
        return self.PlaceTypeId == other.PlaceTypeId

    def __hash__(self):
        return hash(self.PlaceTypeId)

    def __repr__(self):
        return (u"<TraceStop(PlaceTypeId='%s')>" % \
                (self.PlaceTypeId)) \
                .encode(OUTPUT_ENCODING)


class MisApi(object):
    def __init__(self, db_session, id):
        mis = db_session.query(metabase.Mis).filter_by(id=id).one()
        self._api_url = mis.api_url
        self._api_key = mis.api_key
        self._name = mis.name
        self._multiple_starts_and_arrivals = mis.multiple_starts_and_arrivals
        self._http = httplib2.Http("/tmp/.planner_cache")

    def get_multiple_starts_and_arrivals(self):
        return self._multiple_starts_and_arrivals

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
            # TODO error handling (raise exception)
            logging.error("POST <%s> FAILED: %s" % (url, resp.status))

        logging.debug("Response: \n%s", resp)
        logging.debug("Content: \n%s", content)
        return resp, json.loads(content)

    # request is an object of class ItineraryRequestType
    def get_itinerary(self, request):
        ret = ItineraryResponseType()

        data = request.marshal()
        _, content = self._send_request("itineraries", data)
        # TODO error handling
        content = content["ItineraryResponseType"]
        ret.RequestId = content["RequestId"]
        ret.Status = StatusType(content["Status"]["Code"],
                                content["Status"].get("RuntimeDuration", 0))
        if ret.Status.Code != StatusCodeEnum.OK:
            raise Exception("<get_itinerary> %s" % ret.Status.Code)
        ret.DetailedTrip = parse_detailed_trip(content.get("DetailedTrip", None))
        if ret.DetailedTrip:
            ret.DetailedTrip.id = self._name

        return ret

    # request is an object of class SummedUpItinerariesRequestType
    # If must_be_complete is True, an exception is raised if MIS response
    # doesn't contain an itinerary for each given arrival point (if
    # it is a departure_at request). If it is an arrival_at request, it ensures
    # that MIS response contains an itinerary for each given departure point.
    def get_summed_up_itineraries(self, request, must_be_complete=False):
        ret = SummedUpItinerariesResponseType()

        # data = {"SummedUpItinerariesRequestType" : request.marshal()}
        # Remove duplicates
        request.departures = list(set(request.departures))
        request.arrivals = list(set(request.arrivals))
        data = request.marshal()
        _, content = self._send_request("summed_up_itineraries", data)
        # TODO error handling
        content = content["SummedUpItinerariesResponseType"]
        ret.RequestId = content["RequestId"]
        ret.Status = StatusType(content["Status"]["Code"],
                                content["Status"].get("RuntimeDuration", 0))
        if ret.Status.Code != StatusCodeEnum.OK:
            raise Exception("<get_summed_up_itineraries> %s" % ret.Status.Code)
        ret.summedUpTrips = parse_summed_up_trips(content.get("summedUpTrips", []))

        if must_be_complete:
            if request.DepartureTime:
                nb_expected = len(request.arrivals)
            else:
                nb_expected = len(request.departures)
            if len(ret.summedUpTrips) < nb_expected:
                raise Exception("Incomplete MIS reply: expected %s itineraries, got %s"
                                % (nb_expected, len(ret.summedUpTrips)))

        return ret

    def __repr__(self):
        return (u"<MisApi(name='%s')>" % \
                (self._name)) \
                .encode(OUTPUT_ENCODING)


class Planner(object):
    def __init__(self, db_url):
        # Create engine used to connect to database
        logging.debug("DB_URL: %s", db_url)
        self._db_engine = create_engine(db_url, echo=False)
        # Class that will be instantiated by every thread to create their own 
        # thread-local sessions
        self._db_session_factory = scoped_session(sessionmaker(
                                                        bind=self._db_engine, 
                                                        expire_on_commit=False))

    def __del__(self):
        # Not mandatory but a good way to ensure that no connection to the database
        # is kept alive (particularly useful for unit tests).
        self._db_engine.dispose()

    def create_db_session(self):
        return self._db_session_factory()

    def remove_db_session(self, db_session):
        db_session.close()
        self._db_session_factory.remove()
