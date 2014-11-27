import datetime

from apiisim.planner import TraceStop
from apiisim.common.plan_trip import LocationStructure, TripType, StepEndPointType, TripStopPlaceType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType


class TripCollection:
    def __init__(self):
        pass

    @staticmethod
    def _new_stop_trace(place_id, longitude, latitude, link=False):
        ret = TraceStop()
        ret.AccessTime = datetime.timedelta()
        ret.PlaceTypeId = place_id + ("L" if link else "")
        l = LocationStructure()
        l.Longitude = longitude
        l.Latitude = latitude
        ret.Position = l
        return ret

    @staticmethod
    def _stop_trace_paris(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:DUA:SA:9:1020", 2.705505, 48.825188, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _stop_trace_reims(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:TAD:SA:51454", 4.033091, 49.256602, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _stop_trace_strasbourg(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:SCF:SA:SAOCE87212027", 7.735625, 48.585114, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _stop_trace_orleans(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:CCA:SA:ORLE", 4.345873, 48.953255, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _stop_trace_lyon(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:DUA:SA:59:3663677", 2.451872, 48.809786, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _stop_trace_marseille(dep_time, arr_time, link=False):
        s = TripCollection._new_stop_trace("stop_area:SCF:SA:SAOCE87751008", 5.380651, 43.302734, link)
        s.departure_time = dep_time
        s.arrival_time = arr_time
        return s

    @staticmethod
    def _summed_up_from_paris_lyon_to_marseille():
        trips = SummedUpItinerariesResponseType()
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 14, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:DUA:SA:59:3663677"  # Lyon 14h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 15, 14)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 15h14
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:DUA:SA:9:1020"  # Paris 12h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 15, 15)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 15h15
        trips.summedUpTrips.append(trip)
        return trips

    @staticmethod
    def _summed_up_from_paris_lyon_to_strasbourg_marseille():
        trips = SummedUpItinerariesResponseType()
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 14, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:DUA:SA:59:3663677"  # Lyon 14h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 15, 14)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 15h14
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:DUA:SA:9:1020"  # Paris 12h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 15, 15)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87212027"  # Strasbourg 15h15
        trips.summedUpTrips.append(trip)
        return trips

    @staticmethod
    def _summed_up_from_marseille_to_paris_strasbourg_lyon():
        trips = SummedUpItinerariesResponseType()
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 12h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 15, 40)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:DUA:SA:9:1020"  # Paris 15h40
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 12h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 17, 20)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87212027"  # Strasbourg 17h20
        trips.summedUpTrips.append(trip)
        trip = TripType()
        trip.Departure = StepEndPointType()
        trip.Departure.DateTime = datetime.datetime(2014, 10, 21, 12, 30)
        trip.Departure.TripStopPlace = TripStopPlaceType()
        trip.Departure.TripStopPlace.id = "stop_area:SCF:SA:SAOCE87751008"  # Marseille 12h30
        trip.Arrival = StepEndPointType()
        trip.Arrival.DateTime = datetime.datetime(2014, 10, 21, 13, 20)
        trip.Arrival.TripStopPlace = TripStopPlaceType()
        trip.Arrival.TripStopPlace.id = "stop_area:DUA:SA:59:3663677"  # Lyon 13h20
        trips.summedUpTrips.append(trip)
        return trips
