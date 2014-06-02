from sim_plan_trip import ItineraryResponseType
from sim_plan_sumed_up_trip import SumedUpItinerariesResponseType

class StringEnum:
    @classmethod
    def validate(cls, string):
        for k, v in cls.__dict__.iteritems():
            if not k.startswith('__') and string == v:
                return True
        return False

class AlgorithmEnum(StringEnum):
    CLASSIC  = 'CLASSIC'
    SHORTEST = 'SHORTEST'
    FASTEST = 'FASTEST'
    MINCHANGES = 'MINCHANGES'

class StatusCodeEnum:
    OK = "OK"
    UNKNOWN_END_POINT = "UNKNOWN_END_POINT"
    TOO_MANY_END_POINT = "TOO_MANY_END_POINT"
    TOO_FAR_POSITION = "TOO_FAR_POSITION"
    DATE_OUT_OF_SCOPE = "DATE_OUT_OF_SCOPE"
    BAD_REQUEST = "BAD_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SelfDriveModeEnum(StringEnum):
    CAR = "CAR"
    BIKE = "BIKE"
    WALK = "WALK"

class TripPartEnum(StringEnum):
    DEPARTURE = "DEPARTURE"
    ARRIVAL = "ARRIVAL"

class SiteTypeEnum:
    LOCATION = "LOCATION"
    ADDRESS = "ADDRESS"
    BOARDING_POSITION = "BOARDING_POSITION"
    QUAY = "QUAY"
    COMMERCIAL_STOP_POINT = "COMMERCIAL_STOP_POINT"
    STOP_PLACE = "STOP_PLACE"
    POI = "POI"
    ROAD_LINK = "ROAD_LINK"
    CITY = "CITY"


class TransportModeEnum(StringEnum):
    ALL = 'ALL'
    BUS = 'BUS'
    TROLLEYBUS = 'TROLLEYBUS'
    TRAM = 'TRAM'
    COACH = 'COACH'
    RAIL = 'RAIL'
    INTERCITYRAIL = 'INTERCITYRAIL'
    URBANRAIL = 'URBANRAIL'
    METRO = 'METRO'
    AIR = 'AIR'
    WATER = 'WATER'
    CABLE = 'CABLE'
    FUNICULAR = 'FUNICULAR'
    TAXI = 'TAXI'
    BIKE = 'BIKE'
    CAR = 'CAR'


class PublicTransportModeEnum:
    BUS = 'BUS'
    TROLLEYBUS = 'TROLLEYBUS'
    TRAM = 'TRAM'
    COACH = 'COACH'
    RAIL = 'RAIL'
    URBANRAIL = 'URBANRAIL'
    INTERCITYRAIL = 'INTERCITYRAIL'
    METRO = 'METRO'
    AIR = 'AIR'
    WATER = 'WATER'
    CABLE = 'CABLE'
    FUNICULAR = 'FUNICULAR'
    TAXI = 'TAXI'
    UNKNOWN = "UNKNOWN"


class PlanSearchOptions:
    DEPARTURE_ARRIVAL_OPTIMIZED = "DEPARTURE_ARRIVAL_OPTIMIZED"

class MisApiException(Exception):
    error_code = StatusCodeEnum.INTERNAL_ERROR
class MisApiDateOutOfScopeException(MisApiException):
    error_code = StatusCodeEnum.DATE_OUT_OF_SCOPE
class MisApiBadRequestException(MisApiException):
    error_code = StatusCodeEnum.BAD_REQUEST
class MisApiInternalErrorException(MisApiException):
    error_code = StatusCodeEnum.INTERNAL_ERROR


class Stop():
    def __init__(self, code, name, lat, long):
        self.code = code
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return ("<Stop: code=%s, name=%s, lat=%s, long=%s>" % \
               (self.code, self.name , self.lat , self.long)).encode("utf-8")


class MisApiBase():

    def __init__(self, api_key=""):
        self._api_key = api_key

    # Return a list with all stop points from this mis
    def get_stops(self):
        return []

    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm=AlgorithmEnum.CLASSIC, modes=[], 
                      self_drive_conditions=[],
                      accessibility_constraint=False,
                      language=""):
        return ItineraryResponseType()

    def get_sumed_up_itineraries(self, departures, arrivals, departure_time, arrival_time,
                                 algorithm=AlgorithmEnum.CLASSIC, modes=[], 
                                 self_drive_conditions=[],
                                 accessibility_constraint=False,
                                 language="",
                                 options=[]):
        return SumedUpItinerariesResponseType()
