from apiisim.common.mis_plan_trip import TripType
from apiisim.common import StatusCodeEnum


class MisApiException(Exception):
    error_code = StatusCodeEnum.INTERNAL_ERROR


class MisApiDateOutOfScopeException(MisApiException):
    error_code = StatusCodeEnum.DATE_OUT_OF_SCOPE


class MisApiBadRequestException(MisApiException):
    error_code = StatusCodeEnum.BAD_REQUEST


class MisApiUnknownObjectException(MisApiException):
    error_code = StatusCodeEnum.BAD_REQUEST


class MisApiUnauthorizedException(MisApiException):
    error_code = StatusCodeEnum.INTERNAL_ERROR


class MisApiInternalErrorException(MisApiException):
    error_code = StatusCodeEnum.INTERNAL_ERROR


class MisCapabilities(object):
    def __init__(self, multiple_starts_and_arrivals, geographic_position_compliant,
                 public_transport_modes):
        # Integer
        self.multiple_starts_and_arrivals = multiple_starts_and_arrivals
        # Boolean
        self.geographic_position_compliant = geographic_position_compliant
        # [TransportModeEnum]
        self.public_transport_modes = public_transport_modes


class MisApiBase(object):
    def __init__(self, config, api_key=""):
        self._api_key = api_key

    """
        Return a list with all stop points from this mis
    """

    def get_stops(self):
        return []  # [StopPlaceType]

    def get_capabilities(self):
        return MisCapabilities(False, False, [])

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
        return []  # [SummedUpTripType]
