# -*- coding: utf8 -*-

"""
    Generic Mis API stub class. It retrieves stops from a JSON file, then creates
    and populates a database with them. When receiving itinerary requests, two
    implementations are available:
        - one that returns random itineraries by randomly choosing stops in its database.
            -> _RandomMisApi
        - one that returns shortest itineraries based on "as the crow flies"
          distance between stop points (using PostGIS). Although simplistic, it
          provides much more meaningful results than the random stub.
            -> _SimpleMisApi
"""
from base import MisApiBase, Stop
import json, logging, os
from common.mis_plan_trip import ItineraryResponseType, EndPointType, \
                                 TripStopPlaceType, TripType
from common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType, SummedUpTripType
from common import PlanSearchOptions
import metabase
from datetime import timedelta
from random import randint
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, GenericFunction


NAME = "_stub"

DB_TRIGGER = \
"""
CREATE OR REPLACE FUNCTION stop_pre_update_handler()
RETURNS trigger AS $$
BEGIN
    -- When inserting, OLD is not defined so we have to make a special case for INSERT
    IF (TG_OP = 'INSERT') THEN
        NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
    ELSE
        IF NEW.lat != OLD.lat OR NEW.long != OLD.long THEN
            NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER stop_pre_update BEFORE INSERT OR UPDATE ON stop
FOR EACH ROW
EXECUTE PROCEDURE stop_pre_update_handler();
"""


class ST_GeogFromText(GenericFunction):
    name = 'ST_GeogFromText'
    type = Geography


Base = declarative_base()

class DbStop(Base):
    __tablename__ = 'stop'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False)
    name = Column(String, nullable=False)
    lat = Column(Float(53), nullable=False)
    long = Column(Float(53), nullable=False)
    geog = Column(Geography(geometry_type="POINT", srid=4326,
                            spatial_index=True))


def create_db(db_name):
    engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost/postgres", echo=False)
    conn = engine.connect()
    # Delete database. If it doesn't exist, SQLAlchemy will raise an error,
    # just ignore it.
    try:
        conn.execute("COMMIT")
        conn.execute("DROP DATABASE %s" % db_name)
    except:
        pass

    conn.execute("COMMIT")
    conn.execute("CREATE DATABASE %s" % db_name)
    conn.close()
    engine.dispose()

    engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost/%s" % db_name, echo=False)
    conn = engine.connect()
    conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    Base.metadata.create_all(bind=engine)

    conn.execute(DB_TRIGGER)
    conn.close()
    engine.dispose()


def connect_db(db_name):
    engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost/%s" % db_name, echo=False)
    return Session(bind=engine, expire_on_commit=False)


def populate_db(db_name, stops_file):
    db_session = connect_db(db_name)

    try:
        with open(stops_file, 'r') as f:
            content = f.read()
            content = json.loads(content[content.find('{"stop_areas"'):])

        for s in  content["stop_areas"]:
            new_stop = DbStop()
            new_stop.code = s["id"]
            new_stop.name = s["name"]
            new_stop.lat = s["coord"]["lat"]
            new_stop.long = s["coord"]["lon"]
            db_session.add(new_stop)
        db_session.commit()
    finally:
        db_session.close()
        db_session.bind.dispose()


# location is a LocationContextType object
def get_location_id(location):
    return location.PlaceTypeId \
        or "%s;%s" % (location.Position.Longitude, location.Position.Latitude)


def random_date(min_date, max_date):
    if min_date and max_date:
        delta = (max_date - min_date).total_seconds()
    else:
        delta = 36000 # 10 hours
    if min_date:
        return min_date + timedelta(seconds=randint(0, delta))
    else:
        return max_date - timedelta(seconds=randint(0, delta))

# location is a LocationContextType object
def location_to_end_point(location, departure_time=None, arrival_time=None):
    ret = EndPointType()
    if not departure_time and not arrival_time:
        ret.DateTime = None
    else:
        ret.DateTime = random_date(departure_time, arrival_time)
    place = TripStopPlaceType()
    place.id = get_location_id(location)
    place.Position = location.Position
    ret.TripStopPlace = place

    return ret

class _MisApi(MisApiBase):
    _STOPS_FILE = os.path.dirname(os.path.realpath(__file__)) + "/" + "_stub_stops.json"
    _DB_NAME = "_stub_db"
    _initialized = False

    def __init__(self, api_key=""):
        if not self._initialized:
            create_db(self._DB_NAME)
            populate_db(self._DB_NAME, self._STOPS_FILE)
            self.__class__._initialized = True
        self._db_session = connect_db(self._DB_NAME)

    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        return None

    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        return None

    def get_stops(self):
        ret = []
        stops = self._db_session.query(DbStop).all()
        for s in stops:
            ret.append(Stop(code=s.code, name=s.name, lat=s.lat, long=s.long))

        return ret


    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm, modes, self_drive_conditions,
                      accessibility_constraint, language, options):
        trip = self._generate_detailed_trip(departures, arrivals, departure_time, arrival_time)
        return ItineraryResponseType(DetailedTrip=trip)


    def get_summed_up_itineraries(self, departures, arrivals, departure_time,
                                  arrival_time, algorithm,
                                  modes, self_drive_conditions,
                                  accessibility_constraint,
                                  language, options):

        ret = SummedUpItinerariesResponseType()

        trips = []
        if PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED in options:
            for d in departures:
                for a in arrivals:
                    trips.append(self._generate_summed_up_trip([d], [a], departure_time, arrival_time))
        else:
            if departure_time:
                for a in arrivals:
                    trips.append(self._generate_summed_up_trip(departures, [a], departure_time, None))
            else:
                for d in departures:
                    trips.append(self._generate_summed_up_trip([d], arrivals, None, arrival_time))

        ret.summedUpTrips = trips
        logging.debug("Summed up trips (%s) : %s", len(ret.summedUpTrips), ret.summedUpTrips)

        return ret

    def __del__(self):
        if self._db_session:
            self._db_session.close()
            self._db_session.bind.dispose()


# Return random itineraries.
class _RandomMisApi(_MisApi):
    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_detailed_trip> only supports 1-n requests")

        ret = TripType()
        ret.Duration = timedelta(seconds=randint(0, 36000))
        ret.Distance = randint(0, 10000)
        ret.Disrupted = False
        ret.InterchangeNumber = randint(0, 10)
        ret.sections = []

        if len(departures) > 1:
            departure = departures[randint(0, len(departures) - 1)]
            ret.Departure = location_to_end_point(departure, departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrivals[0], ret.Departure.DateTime, arrival_time)
        else:
            arrival = arrivals[randint(0, len(arrivals) - 1)]
            ret.Departure = location_to_end_point(departures[0], departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrival, ret.Departure.DateTime, arrival_time)

        return ret


    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_summed_up_trip> only supports 1-n requests")

        ret = SummedUpTripType()
        if len(departures) > 1:
            departure = departures[randint(0, len(departures) - 1)]
            ret.Departure = location_to_end_point(departure, departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrivals[0], ret.Departure.DateTime, arrival_time)
        else:
            arrival = arrivals[randint(0, len(arrivals) - 1)]
            ret.Departure = location_to_end_point(departures[0], departure_time, arrival_time)
            ret.Arrival = location_to_end_point(arrival, ret.Departure.DateTime, arrival_time)

        ret.InterchangeCount = randint(0, 10)
        ret.InterchangeDuration = randint(0, 1000)

        return ret


# Return itineraries based on "as the crow flies" distance between stops.
class _SimpleMisApi(_MisApi):
    # Return closest location to loc.
    def _get_closest_location(self, loc, locations):
        distances = [] # [(LocationContextType, distance to loc (in meters))]
        if loc.PlaceTypeId:
            geog1 = self._db_session.query(metabase.Stop.geog) \
                                    .filter(metabase.Stop.code == loc.PlaceTypeId) \
                                    .subquery().c.geog
        else:
            geog1 = ST_GeogFromText('POINT(%s %s)' \
                                    % (loc.Position.Longitude, loc.Position.Latitude))
        for l in locations:
            if l.PlaceTypeId:
                geog2 = self._db_session.query(metabase.Stop.geog) \
                                        .filter(metabase.Stop.code == l.PlaceTypeId) \
                                        .subquery().c.geog
            else:
                geog2 = ST_GeogFromText('POINT(%s %s)' \
                                    % (l.Position.Longitude, l.Position.Latitude))
            d = self._db_session.query(ST_Distance(geog1, geog2)).first()[0]
            distances.append((l, d))

        distances.sort(key=lambda x: x[1])
        # logging.debug("Best stop: %s | Distance: %s", distances[0][0].PlaceTypeId, distances[0][1])
        return distances[0]


    def _generate_detailed_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_detailed_trip> only supports 1-n requests")

        ret = TripType()
        ret.Disrupted = False
        ret.InterchangeNumber = randint(0, 10)
        ret.sections = []

        if len(departures) > 1:
            best_departure, distance = self._get_closest_location(arrivals[0], departures)
            ret.Departure = location_to_end_point(best_departure)
            ret.Arrival = location_to_end_point(arrivals[0])
        else:
            best_arrival, distance = self._get_closest_location(departures[0], arrivals)
            ret.Departure = location_to_end_point(departures[0])
            ret.Arrival = location_to_end_point(best_arrival, ret.Departure.DateTime, arrival_time)

        duration = timedelta(seconds=distance / 10)
        if departure_time:
            ret.Departure.DateTime = departure_time
            ret.Arrival.DateTime = departure_time + duration
        else:
            ret.Departure.DateTime = arrival_time - duration
            ret.Arrival.DateTime = arrival_time

        ret.Distance = distance
        ret.Duration = duration
        # logging.debug("Departure %s %s", ret.Departure.TripStopPlace.id, ret.Departure.DateTime)
        # logging.debug("Arrival %s %s", ret.Arrival.TripStopPlace.id, ret.Arrival.DateTime)

        return ret


    def _generate_summed_up_trip(self, departures, arrivals, departure_time, arrival_time):
        if len(departures) > 1 and len(arrivals) > 1:
            raise Exception("<generate_summed_up_trip> only supports 1-n requests")

        ret = SummedUpTripType()
        if len(departures) > 1:
            best_departure, distance = self._get_closest_location(arrivals[0], departures)
            ret.Departure = location_to_end_point(best_departure)
            ret.Arrival = location_to_end_point(arrivals[0])
        else:
            best_arrival, distance = self._get_closest_location(departures[0], arrivals)
            ret.Departure = location_to_end_point(departures[0])
            ret.Arrival = location_to_end_point(best_arrival)

        duration = timedelta(seconds=distance / 10)
        if departure_time:
            ret.Departure.DateTime = departure_time
            ret.Arrival.DateTime = departure_time + duration
        else:
            ret.Departure.DateTime = arrival_time - duration
            ret.Arrival.DateTime = arrival_time

        ret.InterchangeCount = randint(0, 10)
        ret.InterchangeDuration = randint(0, 1000)
        # logging.debug("Departure %s %s", ret.Departure.TripStopPlace.id, ret.Departure.DateTime)
        # logging.debug("Arrival %s %s", ret.Arrival.TripStopPlace.id, ret.Arrival.DateTime)

        return ret


MisApi = _SimpleMisApi
