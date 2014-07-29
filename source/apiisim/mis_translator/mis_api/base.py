from apiisim.common.mis_plan_trip import ItineraryResponseType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType
from apiisim.common import StatusCodeEnum

class MisApiException(Exception):
    error_code = StatusCodeEnum.INTERNAL_ERROR
class MisApiDateOutOfScopeException(MisApiException):
    error_code = StatusCodeEnum.DATE_OUT_OF_SCOPE
class MisApiBadRequestException(MisApiException):
    error_code = StatusCodeEnum.BAD_REQUEST
class MisApiUnauthorizedException(MisApiException):
    error_code = StatusCodeEnum.INTERNAL_ERROR
class MisApiInternalErrorException(MisApiException):
    error_code = StatusCodeEnum.INTERNAL_ERROR


class MisApiBase(object):

    def __init__(self, api_key=""):
        self._api_key = api_key

    """
        Return a list with all stop points from this mis
    """
    def get_stops(self):
        return [] # [StopPlaceType]

    """
        departures: [LocationContextType]
        arrivals: [LocationContextType]
        departure_time: DateTime
        arrival_time: DateTime
        algorithm: AlgorithmEnum
        modes: [TransportModeEnum]
        self_drive_conditions [SelfDriveConditionType]
        accessibility_constraint: Boolean
        language: String
        options: [PlanSearchOptions]
    """
    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm, modes, self_drive_conditions,
                      accessibility_constraint, language, options):
        return TripType()

    """
        departures: [LocationContextType]
        arrivals: [LocationContextType]
        departure_time: DateTime
        arrival_time: DateTime
        algorithm: AlgorithmEnum
        modes: [TransportModeEnum]
        self_drive_conditions [SelfDriveConditionType]
        accessibility_constraint: Boolean
        language: String
        options: [PlanSearchOptions]
    """
    def get_summed_up_itineraries(self, departures, arrivals, departure_time, arrival_time,
                                  algorithm, modes, self_drive_conditions,
                                  accessibility_constraint, language, options):
        return [] # [SummedUpTripType]
