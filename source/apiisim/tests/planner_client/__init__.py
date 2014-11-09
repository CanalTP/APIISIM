from apiisim.common import AlgorithmEnum, TransportModeEnum
from apiisim.common.plan_trip import PlanTripRequestType, LocationPointType, LocationStructure, \
    PlanTripCancellationRequest, EndingSearch, PlanTripNotificationResponseType, \
    PlanTripExistenceNotificationResponseType, PlanTripResponse, StartingSearch
from apiisim.common.mis_plan_trip import LocationContextType
from random import randint
import datetime


def new_location(place_id, longitude, latitude):
    ret = LocationContextType()
    ret.PlaceTypeId = place_id
    l = LocationStructure()
    l.Longitude = longitude
    l.Latitude = latitude
    ret.Position = l

    return ret


def new_request(departure, arrival):
    ret = PlanTripRequestType()

    ret.clientRequestId = "request_" + str(randint(0, 60000))
    # ret.DepartureTime = datetime.datetime(year=2014, month=8, day=22, hour=18) - timedelta(days=50)
    ret.DepartureTime = datetime.datetime.now() - datetime.timedelta(days=10)
    ret.ArrivalTime = None
    ret.Departure = departure
    ret.Arrival = arrival

    ret.MaxTrips = 10
    ret.Algorithm = AlgorithmEnum.CLASSIC
    ret.modes = [TransportModeEnum.ALL]
    ret.selfDriveConditions = []
    ret.AccessibilityConstraint = False
    ret.Language = ""

    return ret


# Below are some examples of itinerary requests.

def trip_paris_reims():
    return new_request(new_location(None, 2.348294, 48.858108),  # Chatelet
                       new_location(None, 4.034720, 49.262780))  # Reims

def trip_orly_reims():
    return new_request(new_location("stop_area:DUA:SA:59841", 2.369208, 48.729012),  # Orly
                       new_location("stop_area:CGD:SA:1137", 5.051595, 47.332904))  # Reims