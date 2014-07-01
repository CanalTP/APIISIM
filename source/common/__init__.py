import re
from datetime import timedelta
from mis_plan_trip import LocationContextType, LocationStructure


# Encoding used when converting objects to strings
OUTPUT_ENCODING = "utf-8"

def parse_location_context(location):
    ret = LocationContextType()

    if "Position" in location:
        ret.Position = LocationStructure(
                            Latitude=location["Position"]["Latitude"],
                            Longitude=location["Position"]["Longitude"])
    ret.AccessTime = xsd_duration_to_timedelta(location["AccessTime"])
    ret.PlaceTypeId = location.get("PlaceTypeId", None)

    if not ret.PlaceTypeId and not ret.Position:
        raise Exception("Location has no Position or PlaceTypeId")

    return ret


def timedelta_to_xsd_duration(delta):
    # TODO handle days, months and years
    ret = "PT"
    total = int(delta.total_seconds())
    hours = total / 3600
    minutes = total / 60 - (hours * 60)
    seconds = total - (hours * 3600) - (minutes * 60)
    ret += (unicode(hours) + "H") if hours else ""
    ret += (unicode(minutes) + "M") if minutes else ""
    ret += unicode(seconds) + "S"
    return ret


def xsd_duration_to_timedelta(duration):
    regex  = re.compile('P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?'
                        '(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?'
                        '(?:(?P<seconds>\d+)S)?)?')
    duration = regex.match(duration).groupdict(0)
    delta = timedelta(days=int(duration['days']) + (int(duration['months']) * 30) \
                           + (int(duration['years']) * 365),
                      hours=int(duration['hours']),
                      minutes=int(duration['minutes']),
                      seconds=int(duration['seconds']))

    return delta


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
