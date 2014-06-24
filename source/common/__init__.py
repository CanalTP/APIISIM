# Encoding used when converting objects to strings
OUTPUT_ENCODING = "utf-8"

def string_to_bool(string):
    if string in ["True", "true", "TRUE"]:
        return True
    else:
        return False

class StringEnum:
    """
        Return True if given string is in given enum (cls being the enum class), 
        False otherwise.
    """
    @classmethod
    def validate(cls, string):
        for k, v in cls.__dict__.iteritems():
            if not k.startswith('__') and string == v:
                return True
        return False

class PlanTripStatusEnum:
    OK = "0"
    BAD_REQUEST = "1"
    SERVER_ERROR = "2"

class PlanTripErrorEnum:
    OK ="OK"
    NO_MORE_SOLUTION_FOR_REQUEST = "NO_MORE_SOLUTION_FOR_REQUEST"
    NO_SOLUTION_FOR_REQUEST = "NO_SOLUTION_FOR_REQUEST"
    BAD_REQUEST = "BAD_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    REQUESTED_DATE_OUT_OF_SCOPE = "REQUESTED_DATE_OUT_OF_SCOPE"
    DEPARTURE_UNKNOWN = "DEPARTURE_UNKNOWN"
    ARRIVAL_UNKNOWN = "ARRIVAL_UNKNOWN"
    DEPARTURE_TOO_FAR = "DEPARTURE_TOO_FAR"
    ARRIVAL_TOO_FAR = "ARRIVAL_TOO_FAR"

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

class TypeOfPlaceEnum:
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
