# -*- coding: utf8 -*-

import json
import logging
import urllib
import traceback
from datetime import datetime, timedelta
from operator import itemgetter
from copy import deepcopy
from Queue import Queue
import threading

import httplib2

from apiisim.mis_translator.mis_api import MisApiBase, MisApiException, \
    MisApiDateOutOfScopeException, MisApiBadRequestException, \
    MisApiInternalErrorException, MisApiUnauthorizedException, \
    MisCapabilities, MisApiUnknownObjectException
from apiisim.common.mis_collect_stops import StopPlaceType, quaysType
from apiisim.common.mis_plan_trip import TripStopPlaceType, LocationStructure, LocationContextType, \
    EndPointType, StepEndPointType, StepType, \
    QuayType, CentroidType, TripType, \
    SectionType, PTRideType, LegType, \
    LineType, PTNetworkType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesResponseType, SummedUpTripType
from apiisim.common import AlgorithmEnum, SelfDriveModeEnum, TripPartEnum, TypeOfPlaceEnum, \
    TransportModeEnum, PublicTransportModeEnum, PlanSearchOptions


NAME = "navitia"
ITEMS_PER_PAGE = 1000
DATE_FORMAT = "%Y%m%dT%H%M%S"


class SectionTypeEnum:
    PUBLIC_TRANSPORT = "public_transport"
    STREET_NETWORK = "street_network"
    WAITING = "waiting"
    TRANSFER = "transfer"
    BIRD_FLY = "bird_fly"
    BOARDING = "boarding"
    LANDING = "landing"
    BSS_RENT = "bss_rent"
    BSS_PUT_BACK = "bss_put_back"


# Not used, it's best to use the default algorithm (ALL) and then
# filter the results ourselves depending on the request parameters.
class JourneyTypeEnum:
    ALL = "all"
    BEST = "best"
    RAPID = "rapid"
    NO_TRAIN = "no_train"
    COMFORT = "comfort"
    CAR = "car"
    LESS_FALLBACK_WALK = "less_fallback_walk"
    LESS_FALLBACK_BIKE = "less_fallback_bike"
    FASTEST = "fastest"
    NON_PT_WALK = "non_pt_walk"
    NON_PT_BIKE = "non_pt_bike"
    NON_PT_BSS = "non_pt_bss"
    HEALTHY = "healthy"


TYPE_OF_PLACE_MAPPING = {
    # Navitia 'embedded_type' : TypeOfPlaceEnum
    'stop_point': TypeOfPlaceEnum.STOP_PLACE,
    'stop_area': TypeOfPlaceEnum.STOP_PLACE,
    'address': TypeOfPlaceEnum.ADDRESS,
    'poi': TypeOfPlaceEnum.POI,
    'adminstrative_region': TypeOfPlaceEnum.LOCATION
}


# TODO Maybe add some commercial_modes too
PUBLIC_TRANSPORT_MODE_MAPPING = {
    # Navitia physical_mode id : PublicTransportModeEnum
    "physical_mode:Coach": PublicTransportModeEnum.COACH,
    "physical_mode:Taxi": PublicTransportModeEnum.TAXI,
    "physical_mode:default_physical_mode": PublicTransportModeEnum.UNKNOWN,
    "physical_mode:Bus": PublicTransportModeEnum.BUS,
    "physical_mode:Tramway": PublicTransportModeEnum.TRAM,
    "physical_mode:Ferry": PublicTransportModeEnum.WATER,
    "physical_mode:RapidTransit": PublicTransportModeEnum.URBANRAIL,
    "physical_mode:LocalTrain": PublicTransportModeEnum.RAIL,
    "physical_mode:LongDistanceTrain": PublicTransportModeEnum.INTERCITYRAIL,
    "physical_mode:Train": PublicTransportModeEnum.RAIL,
    "physical_mode:Metro": PublicTransportModeEnum.METRO,
    "physical_mode:Air": PublicTransportModeEnum.AIR,
    "physical_mode:CheckIn": PublicTransportModeEnum.AIR,
    "physical_mode:CheckOut": PublicTransportModeEnum.AIR,
}

TRANSPORT_MODE_MAPPING = {
    # TransportModeEnum : [Navitia physical and/or commercial modes]}
    TransportModeEnum.BUS: ["physical_mode:Bus",
                            "commercial_mode:BHNS",
                            "commercial_mode:busway"],
    TransportModeEnum.TROLLEYBUS: ["commercial_mode:BHNS",
                                   "commercial_mode:busway"],
    TransportModeEnum.TRAM: ["physical_mode:Tramway"],
    TransportModeEnum.COACH: ["physical_mode:Coach"],
    TransportModeEnum.RAIL: ["physical_mode:Train",
                             "physical_mode:LongDistanceTrain",
                             "physical_mode:RapidTransit",
                             "physical_mode:Metro",
                             "physical_mode:Tramway",
                             "physical_mode:LocalTrain"],
    TransportModeEnum.INTERCITYRAIL: ["physical_mode:LongDistanceTrain"],
    TransportModeEnum.URBANRAIL: ["physical_mode:RapidTransit",
                                  "physical_mode:Metro",
                                  "physical_mode:Tramway"],
    TransportModeEnum.METRO: ["physical_mode:Metro"],
    TransportModeEnum.AIR: ["physical_mode:Air"],
    TransportModeEnum.WATER: ["physical_mode:Ferry",
                              "commercial_mode:Bateau"],
    # TransportModeEnum.CABLE : "physical_mode:Tramway",
    # TransportModeEnum.FUNICULAR : "physical_mode:Tramway",
    TransportModeEnum.TAXI: ["physical_mode:Taxi"],
    TransportModeEnum.BIKE: ["commercial_mode:C72TAD"],
    TransportModeEnum.CAR: ["commercial_mode:C72TAD"]
}

SELF_DRIVE_MODE_MAPPING = {
    # SelfDriveModeEnum : [Navitia modes]
    SelfDriveModeEnum.FOOT: ["walking"],
    SelfDriveModeEnum.CAR: ["car"],
    SelfDriveModeEnum.BICYCLE: ["bike", "bss"],
}


# Navitia mode : SelfDriveModeEnum
INVERSE_SELF_DRIVE_MODE_MAPPING = {}
for k, v in SELF_DRIVE_MODE_MAPPING.items():
    for x in v:
        INVERSE_SELF_DRIVE_MODE_MAPPING[x] = k


def parse_stop_area(point):
    place = TripStopPlaceType()
    embedded_type = point["embedded_type"]
    point_data = point[embedded_type]

    if embedded_type == "stop_area":
        place.id = point_data["id"]
    elif embedded_type == "stop_point":
        place.id = point_data["stop_area"]["id"]
    else:
        place.id = None

    place.Position = LocationStructure(Latitude=point_data["coord"]["lat"],
                                       Longitude=point_data["coord"]["lon"])

    return EndPointType(TripStopPlace=place)


def parse_end_point(point):
    place = TripStopPlaceType()
    place.id = point["id"]
    place.Name = point["name"]
    embedded_type = point["embedded_type"]
    place.TypeOfPlaceRef = TYPE_OF_PLACE_MAPPING.get(embedded_type,
                                                     TypeOfPlaceEnum.LOCATION)

    point_data = point[embedded_type]
    for r in point_data.get("administrative_regions", []):
        if r["level"] == 8:  # City level
            place.CityCode = r["id"]
            place.CityName = r["name"]
    place.Position = LocationStructure(Latitude=point_data["coord"]["lat"],
                                       Longitude=point_data["coord"]["lon"])

    return EndPointType(TripStopPlace=place)


def parse_stop_times(stop_times):
    def parse_step_point(point):
        place = TripStopPlaceType()
        place.id = point["id"]
        place.Name = point["name"]
        place.TypeOfPlaceRef = TYPE_OF_PLACE_MAPPING["stop_point"]
        place.Position = LocationStructure(Latitude=point["coord"]["lat"],
                                           Longitude=point["coord"]["lon"])
        return StepEndPointType(TripStopPlace=place)

    if not stop_times or len(stop_times) < 2:
        return None

    steps = []
    for i in range(0, len(stop_times) - 1):
        s1 = stop_times[i]
        s2 = stop_times[i + 1]
        step = StepType()
        step.id = "%s:%s" % (s1["stop_point"]["id"], s2["stop_point"]["id"])
        # TODO what if it is not a 'stop_point'
        step.Departure = parse_step_point(s1["stop_point"])
        step.Arrival = parse_step_point(s2["stop_point"])
        step.Departure.DateTime = datetime.strptime(s1['arrival_date_time'], DATE_FORMAT)
        step.Arrival.DateTime = datetime.strptime(s2['arrival_date_time'], DATE_FORMAT)
        step.Duration = step.Arrival.DateTime - step.Departure.DateTime
        steps.append(step)

    return steps


def journey_to_summed_up_trip(journey):
    if not journey:
        return None

    trip = SummedUpTripType()
    trip.InterchangeCount = journey["nb_transfers"]
    sections = journey.get('sections', [])
    if not sections:
        logging.debug("No section found")
        return None

    first_section = sections[0]
    last_section = sections[-1]
    trip.Departure = parse_end_point(first_section['from'])
    trip.Departure.DateTime = datetime.strptime(first_section['departure_date_time'], DATE_FORMAT)
    trip.Arrival = parse_end_point(last_section['to'])
    trip.Arrival.DateTime = datetime.strptime(last_section['arrival_date_time'], DATE_FORMAT)
    trip.InterchangeDuration = 0
    for s in [x for x in sections if x["type"] != SectionTypeEnum.PUBLIC_TRANSPORT]:
        trip.InterchangeDuration += s["duration"]

    return trip


def journey_to_str(journey):
    if journey["sections"]:
        return ("From: %s | To: %s | Departure: %s | Arrival: %s | Duration: %s | "
                "Nb_transfers: %s | Type: %s" % (
                    journey["sections"][0]["from"]["id"], journey["sections"][-1]["to"]["id"],
                    journey["departure_date_time"], journey["arrival_date_time"],
                    journey["duration"], journey["nb_transfers"], journey["type"]))
    else:
        return ("(no section) | Departure: %s | Arrival: %s | Duration: %s | "
                "Nb_transfers: %s | Type: %s" % (
                    journey["departure_date_time"], journey["arrival_date_time"],
                    journey["duration"], journey["nb_transfers"], journey["type"]))


def journey_to_detailed_trip(journey):
    if not journey:
        return None

    trip = TripType()
    trip.Duration = timedelta(seconds=journey["duration"])
    trip.Distance = 0
    trip.Disrupted = False
    trip.InterchangeNumber = journey["nb_transfers"]
    trip.CarFootprint = None

    trip.sections = []
    sections = journey['sections']
    for s in sections:
        section = SectionType()
        section.PartialTripId = s["id"]
        if s["type"] == SectionTypeEnum.PUBLIC_TRANSPORT:
            ptr = PTRideType()

            line = LineType()
            line.id = next((x["id"] for x in s.get("links", []) if x["type"] == "line"), "")
            line.Name = s["display_informations"]["label"]
            line.Number = s["display_informations"].get("code", "") or None
            line.PublishedName = line.Name or None
            line.RegistrationNumber = line.id or None
            ptr.Line = line

            network = PTNetworkType()
            network.id = next((x["id"] for x in s.get("links", []) if x["type"] == "network"), "")
            network.Name = s["display_informations"]["network"]
            network.RegistrationNumber = network.id or None
            ptr.PTNetwork = network

            physical_mode_id = next((x["id"] for x in s.get("links", []) if x["type"] == "physical_mode"), "")
            ptr.PublicTransportMode = PUBLIC_TRANSPORT_MODE_MAPPING.get(
                physical_mode_id,
                PublicTransportModeEnum.UNKNOWN)
            ptr.Departure = parse_end_point(s["from"])
            ptr.Arrival = parse_end_point(s["to"])
            ptr.Departure.DateTime = datetime.strptime(s["departure_date_time"], DATE_FORMAT)
            ptr.Arrival.DateTime = datetime.strptime(s["arrival_date_time"], DATE_FORMAT)
            ptr.Duration = timedelta(seconds=s["duration"])
            # TODO remove that hard coded 0 index
            ptr.Distance = s["geojson"]["properties"][0]["length"]
            ptr.StopHeadSign = s["display_informations"].get("headsign", None)
            ptr.steps = parse_stop_times(s.get("stop_date_times", None))
            section.PTRide = ptr
        else:  # Consider section as LegType
            # TODO handle waiting status
            if s["type"] == SectionTypeEnum.WAITING:
                continue
            leg = LegType()
            leg.Departure = parse_end_point(s["from"])
            leg.Arrival = parse_end_point(s["to"])
            leg.Departure.DateTime = datetime.strptime(s["departure_date_time"], DATE_FORMAT)
            leg.Arrival.DateTime = datetime.strptime(s["arrival_date_time"], DATE_FORMAT)
            leg.Duration = timedelta(seconds=s["duration"])
            leg.SelfDriveMode = INVERSE_SELF_DRIVE_MODE_MAPPING.get(
                s.get("transfer_type", ""),
                SelfDriveModeEnum.FOOT)
            section.Leg = leg

        trip.sections.append(section)

    # Navitia doesn't send global departure and arrival items, we have to get
    # them from sections.
    if trip.sections:
        l = lambda obj, attr1, attr2: getattr(obj, attr1) or getattr(obj, attr2)
        trip.Departure = l(trip.sections[0], 'PTRide', 'Leg').Departure
        trip.Arrival = l(trip.sections[-1], 'PTRide', 'Leg').Arrival

    return trip


def algo_classic(journeys, departure_at=False, optimize_departure_and_arrival=False):
    if departure_at:
        # Get journey with minimum arrival time
        l = sorted([(x, datetime.strptime(x["arrival_date_time"], DATE_FORMAT))
                    for x in journeys],
                   key=itemgetter(1))
    else:
        # Get journey with maximum departure time
        l = sorted([(x, datetime.strptime(x["departure_date_time"], DATE_FORMAT))
                    for x in journeys],
                   key=itemgetter(1), reverse=True)

    # Find all journeys that match given criteria. If there is only one, this is
    # the best journey, if there are multiple ones, we'll have to filter results a
    # bit further.
    first_selection = [x[0] for x in l if x[1] == l[0][1]]
    if len(first_selection) <= 1:
        return first_selection[0]

    if not optimize_departure_and_arrival:
        # We have several journeys to choose from, so get journey of type "best"
        # (which is according to Navitia, the best journey).
        l = [x for x in first_selection if x["type"] == "best"]
        if len(l) == 0:
            # If there is no journey of type "best", just go to the next step.
            second_selection = first_selection
        elif len(l) == 1:
            # We found the best one, return it.
            return l[0]
        else:
            # If there are multiple journeys of type "best", go to the next step but
            # only keep journeys of type "best".
            second_selection = l
    else:
        second_selection = first_selection

    # If we still haven't found a unique best journey (remember this is possible
    # as these journeys come from different Navitia requests, so we can have
    # multiple journeys with type "best"), look for the journey with maximum
    # departure_time or with minimum arrival_time, depending on the departure_at
    # parameter.
    if departure_at:
        l = sorted([(x, datetime.strptime(x["departure_date_time"], DATE_FORMAT))
                    for x in second_selection],
                   key=itemgetter(1), reverse=True)
    else:
        l = sorted([(x, datetime.strptime(x["arrival_date_time"], DATE_FORMAT))
                    for x in second_selection],
                   key=itemgetter(1))

    return l[0][0]


def algo_shortest(journeys, departure_at, optimize_departure_and_arrival=False):
    # Filter in journeys with minimum transfers count
    y = min([x["nb_transfers"] for x in journeys])
    j = [x for x in journeys if x["nb_transfers"] == y]
    return algo_classic(j, departure_at, optimize_departure_and_arrival)


def algo_fastest(journeys, departure_at, optimize_departure_and_arrival=False):
    # Get journey with minimum duration
    y = min([x["duration"] for x in journeys])
    j = [x for x in journeys if x["duration"] == y]
    return algo_classic(j, departure_at, optimize_departure_and_arrival)


def algo_minchanges(journeys, departure_at, optimize_departure_and_arrival=False):
    # Get journey with minimum transfer duration
    transfer_durations = []  # [(journey, transfer_duration)]
    for journey in journeys:
        transfer_durations.append(
            (journey, sum([s["duration"] for s in journey["sections"]
                           if s["type"] != SectionTypeEnum.PUBLIC_TRANSPORT])))
    y = min([x[1] for x in transfer_durations])
    j = [x[0] for x in transfer_durations if x[1] == y]
    return algo_classic(j, departure_at, optimize_departure_and_arrival)


def choose_best_journey(journeys, algo, departure_at=True, optimize_departure_and_arrival=False):
    if not journeys:
        return None

    for j in journeys:
        logging.debug("JOURNEY RECEIVED: %s", journey_to_str(j))
    logging.debug("CHOOSE BEST (algorithm: %s - count: %s - clockwise: %s - optimize origin: %s)", algo, len(journeys),
                  departure_at, optimize_departure_and_arrival)

    best = None
    if algo == AlgorithmEnum.CLASSIC:
        best = algo_classic(journeys, departure_at, optimize_departure_and_arrival)
    elif algo == AlgorithmEnum.SHORTEST:
        best = algo_shortest(journeys, departure_at, optimize_departure_and_arrival)
    elif algo == AlgorithmEnum.FASTEST:
        best = algo_fastest(journeys, departure_at, optimize_departure_and_arrival)
    elif algo == AlgorithmEnum.MINCHANGES:
        best = algo_minchanges(journeys, departure_at, optimize_departure_and_arrival)

    logging.debug("FOUND BEST: %s", journey_to_str(best))

    return best


def modes_to_forbidden_uris(enabled_modes):
    if TransportModeEnum.ALL in enabled_modes:
        return []

    # Forbid all modes except the ones that are explicitly enabled.
    # So first create a set containing all existing modes and then remove those
    # that are enabled.
    forbidden_uris = set()
    for modes_list in TRANSPORT_MODE_MAPPING.values():
        forbidden_uris.update(modes_list)

    for m in enabled_modes:
        try:
            forbidden_uris.difference_update(TRANSPORT_MODE_MAPPING[m])
        except KeyError:
            # Some modes have no equivalent in Navitia (like Funicular), so
            # just ignore them.
            pass
    logging.debug("FORBIDDEN URIS: %s", forbidden_uris)

    return forbidden_uris


def params_set_datetime(params, departure_time, arrival_time, departure, arrival):
    if departure_time:
        params['datetime_represents'] = 'departure'
        params['datetime'] = \
            (departure_time + departure.AccessTime).strftime(DATE_FORMAT)
    else:
        params['datetime_represents'] = 'arrival'
        params['datetime'] = \
            (arrival_time + arrival.AccessTime).strftime(DATE_FORMAT)


def params_set_modes(params, modes, self_drive_conditions):
    params["forbidden_uris[]"] = modes_to_forbidden_uris(modes)
    params["first_section_mode[]"] = list(SELF_DRIVE_MODE_MAPPING[SelfDriveModeEnum.FOOT])
    params["last_section_mode[]"] = list(SELF_DRIVE_MODE_MAPPING[SelfDriveModeEnum.FOOT])

    for c in self_drive_conditions:
        if c.TripPart == TripPartEnum.DEPARTURE:
            params["first_section_mode[]"].extend(
                SELF_DRIVE_MODE_MAPPING[c.SelfDriveMode])
        else:
            params["last_section_mode[]"].extend(
                SELF_DRIVE_MODE_MAPPING[c.SelfDriveMode])

    # Navitia bss mode includes walking so don't use both at the same time.
    for l in [params["last_section_mode[]"], params["first_section_mode[]"]]:
        if "bss" in l and "walking" in l:
            l.remove("walking")
            # We ignore DEPARTURE_ARRIVAL_OPTIMIZED option as Navitia always does this
            # optimization (it cannot be disabled).


# location is a LocationContextType object
def get_location_id(location):
    return location.PlaceTypeId or "%s;%s" % (location.Position.Longitude, location.Position.Latitude)


# We need that to be able to remove duplicated stops easily (in get_stops()).
class _StopPlaceType(StopPlaceType):
    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class MisApi(MisApiBase):
    def __init__(self, config, api_key=""):
        self._api_url = "http://navitia2-ws.ctp.xxx.canaltp.fr//v1/coverage/yyy/"
        self._api_key = api_key

        self._geographic_position_compliant = True

        # emulation mode
        self._nm_journeys = False
        self._multithread = True
        self._max_threads = 24
        self._max_stops = 20

        if config and config.has_section("Navitia"):
            if config.has_option('Navitia', 'nm_journeys'):
                self._nm_journeys = config.getboolean('Navitia', 'nm_journeys')
            if config.has_option('Navitia', 'multithread'):
                self._multithread = config.getboolean('Navitia', 'multithread')
            if config.has_option('Navitia', 'max_threads'):
                self._max_threads = config.getint('Navitia', 'max_threads')
            if config.has_option('Navitia', 'max_stops'):
                self._max_stops = config.getint('Navitia', 'max_stops')

    @staticmethod
    def _check_answer(resp, content, get_or_post_str, url):
        if resp.status == 200:
            return

        exc_msg = "%s <%s> FAILED: %s" % (get_or_post_str, url, resp.status)
        try:
            content = json.loads(content)
        except:
            content = {}
        error_id = content.get("error", {}).get("id", "")
        if error_id:
            exc_msg += " (%s)" % error_id
        logging.error(exc_msg)

        if resp.status == 404:
            if error_id == 'date_out_of_bounds':
                raise MisApiDateOutOfScopeException(exc_msg)
            if error_id == 'unknown_object':
                raise MisApiUnknownObjectException(exc_msg)
        elif resp.status == 400:
            raise MisApiBadRequestException(exc_msg)
        elif resp.status == 401:
            raise MisApiUnauthorizedException(exc_msg)
        elif resp.status == 500:
            raise MisApiInternalErrorException(exc_msg)
        raise MisApiException(exc_msg)

    def _send_request(self, url, json_data=None):
        http = httplib2.Http()

        # logging.debug("NAVITIA Authorization: %s", self._api_key)
        logging.debug("NAVITIA URL %s", url)

        headers = {'Authorization': self._api_key}
        if json_data is not None:
            headers['Content-type'] = 'application/json'

        if json_data is None:
            resp, content = http.request(url, "GET", headers=headers)
        else:
            logging.debug("NAVITIA JSON POST %s", json.dumps(json_data))
            resp, content = http.request(url, "POST", body=json.dumps(json_data).encode("ASCII", "replace"),
                                         headers=headers)

        logging.debug("NAVITIA RESP %s", content)
        MisApi._check_answer(resp, content, "GET" if (json_data is None) else "POST", url)
        return resp, content

    def _journeys_request(self, params):
        url = self._api_url + "/journeys" + '?' + urllib.urlencode(params, True)
        resp, content = self._send_request(url)

        # Navitia may give us multiple journeys, we retrieve them all and then
        # choose the best according to request parameters.
        content = json.loads(content)
        logging.debug("NB JOURNEYS: %s", len(content.get("journeys", [])))
        return [x for x in content.get("journeys", [])]

    def _nm_journeys_request(self, params):
        url = self._api_url + "/journeys"
        resp, content = self._send_request(url, json_data=params)

        # Navitia may give us multiple journeys, we retrieve them all and then
        # choose the best according to request parameters.
        content = json.loads(content)
        logging.debug("NB JOURNEYS: %s", len(content.get("journeys", [])))
        return [x for x in content.get("journeys", [])]

    def get_capabilities(self):
        return MisCapabilities(True, self._geographic_position_compliant, [TransportModeEnum.ALL])

    def _get_stops_by_mode(self, physical_mode):
        ret = []
        base_url = self._api_url + ("/physical_modes/%s/stop_areas" % physical_mode)
        params = {"count": ITEMS_PER_PAGE}
        max_pages = 0
        pages_read = 0
        while True:
            url = base_url + ("&" if "?" in base_url else "?") + urllib.urlencode(params)
            resp, content = self._send_request(url)

            content = json.loads(content)
            for s in content["stop_areas"]:
                ret.append(
                    _StopPlaceType(
                        id=s["id"],
                        quays=[QuayType(
                            id=s["id"],
                            Name=s["name"],
                            PrivateCode=s["id"],
                            Centroid=CentroidType(
                                Location=LocationStructure(
                                    Longitude=s["coord"]["lon"],
                                    Latitude=s["coord"]["lat"])))]))

            next_base_url = None
            for s in content["links"]:
                if "type" in s and s['type'] == "next":
                    next_base_url = s["href"]

            if (not next_base_url) or (base_url == next_base_url):
                # We have read all pages, quit
                break
            else:
                # Read next page
                base_url = next_base_url

            if max_pages > 0:
                pages_read += 1
                if pages_read > max_pages:
                    break

        return ret

    def get_stops(self):
        ret = []
        for mode in ["physical_mode:Coach", "physical_mode:LocalTrain",
                     "physical_mode:LongDistanceTrain", "physical_mode:Train",
                     "physical_mode:Ferry", "physical_mode:Air",
                     "physical_mode:RapidTransit", "physical_mode:Bus"]:
            try:
                ret += self._get_stops_by_mode(mode)
            except MisApiUnknownObjectException:
                # Some physical modes may not be not supported by the MIS, just
                # ignore them.
                pass

        ret = list(set(ret))

        return ret

    @staticmethod
    def _clean_up_trip_response(journeys, departures, arrivals, clockwise, algorithm, options):
        if not journeys:
            # No journey found, no need to go further, just return empty list.
            return []

        optimize = PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED in options

        best_journeys = []
        if clockwise:
            for a in arrivals:
                journeys_to_arrival = [x[2] for x in journeys if x[1] == a]
                if not journeys_to_arrival:
                    continue
                best_journeys.append(
                    choose_best_journey(journeys_to_arrival, algorithm,
                                        optimize_departure_and_arrival=optimize)
                )
        else:
            for d in departures:
                journeys_from_departure = [x[2] for x in journeys if x[0] == d]
                if not journeys_from_departure:
                    continue
                best_journeys.append(
                    choose_best_journey(journeys_from_departure, algorithm, departure_at=False,
                                        optimize_departure_and_arrival=optimize)
                )

        ret = [journey_to_summed_up_trip(x) for x in best_journeys if x]
        return ret

    def itinerary_worker(self, sync_queue, sync_params, sync_departure_time, sync_arrival_time,
                         sync_journeys, sync_lock):
        while True:
            sync_lock.acquire()
            ends = sync_queue.empty()
            if not ends:
                worker_departure, worker_arrival = sync_queue.get()
            sync_lock.release()
            if ends:
                break
            thread_params = deepcopy(sync_params)
            thread_params['from'] = get_location_id(worker_departure)
            thread_params['to'] = get_location_id(worker_arrival)
            params_set_datetime(thread_params, sync_departure_time, sync_arrival_time, worker_departure, worker_arrival)
            try:
                worker_journeys = self._journeys_request(thread_params)
            except:
                worker_journeys = []
                logging.getLogger('exceptions').error(traceback.format_exc())
            for j in worker_journeys:
                sync_lock.acquire()
                sync_journeys.append((worker_departure, worker_arrival, j))
                sync_lock.release()
            sync_queue.task_done()

    def get_emulated_itinerary(self, departures, arrivals, departure_time, arrival_time,
                               algorithm, modes, self_drive_conditions,
                               accessibility_constraint, language, options):
        # Limit size of departures and arrivals
        departures = departures[:self._max_stops]
        arrivals = arrivals[:self._max_stops]

        params = {}
        params_set_modes(params, modes, self_drive_conditions)

        journeys = []
        # Request journeys for every departure/arrival pair and then
        # choose best.
        q = Queue(maxsize=0)
        if len(departures) > 1:
            for d in departures:
                q.put((d, arrivals[0]))
        else:
            for a in arrivals:
                q.put((departures[0], a))
        threads = []
        thread_lock = threading.Lock()
        for _ in range(self._max_threads) if self._multithread else [0]:
            worker = threading.Thread(target=self.itinerary_worker,
                                      args=(q, params, departure_time, arrival_time, journeys, thread_lock))
            worker.setDaemon(True)
            worker.start()
            threads.append(worker)
        q.join()
        for thread in threads:
            thread.join()

        best_journey = choose_best_journey(zip(*journeys)[2], algorithm, bool(departure_time))
        # If no journey found, DetailedTrip is None
        return journey_to_detailed_trip(best_journey)

    def get_hardcoded_itinerary(self, departures, arrivals, departure_time, arrival_time,
                                algorithm, modes, self_drive_conditions,
                                accessibility_constraint, language, options):
        params = {}
        params_set_modes(params, modes, self_drive_conditions)

        # fix json format issues
        params["forbidden_uris[]"] = list(params["forbidden_uris[]"])
        params["first_section_mode[]"] = "walking"
        params["last_section_mode[]"] = "walking"

        # request detailed itinerary 1-n or n-1
        if len(departures) > 1:
            params['to'] = [{"uri": get_location_id(arrivals[0]), "access_duration": 0}]
            params['from'] = []
            for d in departures:
                params['from'].append(
                    {"uri": get_location_id(d), "access_duration": int(d.AccessTime.total_seconds() // 60)})
        else:
            params['from'] = [{"uri": get_location_id(departures[0]), "access_duration": 0}]
            params['to'] = []
            for a in arrivals:
                params['to'].append(
                    {"uri": get_location_id(a), "access_duration": int(a.AccessTime.total_seconds() // 60)})

        if departure_time:
            params['datetime_represents'] = 'departure'
            params['datetime'] = departure_time.strftime(DATE_FORMAT)
        else:
            params['datetime_represents'] = 'arrival'
            params['datetime'] = arrival_time.strftime(DATE_FORMAT)

        params['details'] = 'true'

        journeys = self._nm_journeys_request(params)

        best_journey = choose_best_journey(journeys, algorithm, bool(departure_time))
        # If no journey found, DetailedTrip is None
        return journey_to_detailed_trip(best_journey)

    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm, modes, self_drive_conditions,
                      accessibility_constraint, language, options):
        if self._nm_journeys:
            return self.get_hardcoded_itinerary(departures, arrivals, departure_time, arrival_time,
                                                algorithm, modes, self_drive_conditions,
                                                accessibility_constraint, language, options)
        else:
            return self.get_emulated_itinerary(departures, arrivals, departure_time, arrival_time,
                                               algorithm, modes, self_drive_conditions,
                                               accessibility_constraint, language, options)

    def get_emulated_summed_up_itineraries(self, departures, arrivals, departure_time,
                                           arrival_time, algorithm,
                                           modes, self_drive_conditions,
                                           accessibility_constraint,
                                           language, options):
        # Limit size of departures and arrivals
        departures = departures[:self._max_stops]
        arrivals = arrivals[:self._max_stops]

        params = {}
        params_set_modes(params, modes, self_drive_conditions)

        journeys = []
        # Request itinerary for every departure/arrival pair and then
        # choose best.
        q = Queue(maxsize=0)
        for d in departures:
            for a in arrivals:
                q.put((d, a))
        threads = []
        thread_lock = threading.Lock()
        for _ in range(self._max_threads) if self._multithread else [0]:
            worker = threading.Thread(target=self.itinerary_worker,
                                      args=(q, params, departure_time, arrival_time, journeys, thread_lock))
            worker.setDaemon(True)
            worker.start()
            threads.append(worker)
        q.join()
        for thread in threads:
            thread.join()

        trips = MisApi._clean_up_trip_response(journeys, departures, arrivals, departure_time, algorithm, options)
        return trips

    def get_hardcoded_summed_up_itineraries(self, departures, arrivals, departure_time,
                                            arrival_time, algorithm,
                                            modes, self_drive_conditions,
                                            accessibility_constraint,
                                            language, options):
        def location_context_to_str(location):
            if not location.PlaceTypeId:
                return "%s;%s" % (location.Position.Longitude, location.Position.Latitude)
            else:
                return location.PlaceTypeId

        params = {}
        params_set_modes(params, modes, self_drive_conditions)

        # fix json format issues
        params["forbidden_uris[]"] = list(params["forbidden_uris[]"])
        params["first_section_mode[]"] = "walking"
        params["last_section_mode[]"] = "walking"

        # Request itinerary for every departure/arrival pair and then
        # choose best.
        params['from'] = []
        for d in departures:
            params['from'].append(
                {"uri": get_location_id(d), "access_duration": int(d.AccessTime.total_seconds() // 60)})

        params['to'] = []
        for a in arrivals:
            params['to'].append({"uri": get_location_id(a), "access_duration": int(a.AccessTime.total_seconds() // 60)})

        if departure_time:
            params['datetime_represents'] = 'departure'
            params['datetime'] = departure_time.strftime(DATE_FORMAT)
        else:
            params['datetime_represents'] = 'arrival'
            params['datetime'] = arrival_time.strftime(DATE_FORMAT)

        params['details'] = 'true' if PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED in options else 'false'

        journeys = []
        for j in self._nm_journeys_request(params):
            org = parse_stop_area(j["sections"][0]["from"])
            dst = parse_stop_area(j["sections"][-1]["to"])

            if len(departures) == 1:
                d = [departures[0]]
            else:
                d = [s for s in departures if org.TripStopPlace.id == s.PlaceTypeId] or \
                    [sorted([(s, (lambda (x, y): 0.44 * x * x + y * y)(
                        (s.Position.Latitude - float(org.TripStopPlace.Position.Latitude),
                         s.Position.Longitude - float(org.TripStopPlace.Position.Longitude)))) for s in departures],
                            key=lambda distance: distance[1])[0][0]]

            # fix pareto
            if d[0].PlaceTypeId:
                j["sections"][0]["from"]["id"] = d[0].PlaceTypeId

            if len(arrivals) == 1:
                a = [arrivals[0]]
            else:
                a = [s for s in arrivals if dst.TripStopPlace.id == s.PlaceTypeId] or \
                    [sorted([(s, (lambda (x, y): 0.44 * x * x + y * y)(
                        (s.Position.Latitude - float(dst.TripStopPlace.Position.Latitude),
                         s.Position.Longitude - float(dst.TripStopPlace.Position.Longitude)))) for s in arrivals],
                            key=lambda distance: distance[1])[0][0]]

            # fix pareto
            if a[0].PlaceTypeId:
                j["sections"][-1]["to"]["id"] = a[0].PlaceTypeId

            journeys.append((d[0], a[0], j))
            logging.debug("NxM RESULT FOR %s -> %s", location_context_to_str(d[0]), location_context_to_str(a[0]))

        trips = MisApi._clean_up_trip_response(journeys, departures, arrivals, departure_time, algorithm, options)
        return trips

    def get_summed_up_itineraries(self, departures, arrivals, departure_time,
                                  arrival_time, algorithm,
                                  modes, self_drive_conditions,
                                  accessibility_constraint,
                                  language, options):
        if self._nm_journeys:
            return self.get_hardcoded_summed_up_itineraries(departures, arrivals, departure_time,
                                                            arrival_time, algorithm,
                                                            modes, self_drive_conditions,
                                                            accessibility_constraint,
                                                            language, options)
        else:
            return self.get_emulated_summed_up_itineraries(departures, arrivals, departure_time,
                                                           arrival_time, algorithm,
                                                           modes, self_drive_conditions,
                                                           accessibility_constraint,
                                                           language, options)
