# -*- coding: utf8 -*-

from base import MisApiBase, Stop, AlgorithmEnum, TransportModeEnum, \
                 SiteTypeEnum, MisApiException, SelfDriveModeEnum, \
                 MisApiDateOutOfScopeException, MisApiBadRequestException, \
                 MisApiInternalErrorException, PublicTransportModeEnum, \
                 TripPartEnum, MisApiUnauthorizedException
import json, httplib2, logging, urllib
# TODO  do not use import *
from sim_plan_trip import *
from sim_plan_sumed_up_trip import SumedUpItinerariesResponseType, SumedUpTripType
from datetime import datetime
from random import randint
from operator import itemgetter

NAME = "navitia"
ITEMS_PER_PAGE = 100
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
    LESS_FALLBACK_BIKE = "less_fallback_bike"
    FASTEST = "fastest"
    NON_PT_WALK = "non_pt_walk"
    NON_PT_BIKE = "non_pt_bike"
    NON_PT_BSS = "non_pt_bss"
    HEALTHY = "healthy"


SITE_TYPE_MAPPING = {
    # Navitia 'embedded_type' : SiteTypeEnum
    'stop_point' : SiteTypeEnum.STOP_PLACE,
    'stop_area' : SiteTypeEnum.STOP_PLACE,
    'address' :    SiteTypeEnum.ADDRESS,
    'poi' :    SiteTypeEnum.POI,
    'adminstrative_region' : SiteTypeEnum.LOCATION
}


# TODO Maybe add some commercial_modes too
PUBLIC_TRANSPORT_MODE_MAPPING = {
    # Navitia physical_mode id : PublicTransportModeEnum
    "physical_mode:Coach" : PublicTransportModeEnum.COACH,
    "physical_mode:Taxi" : PublicTransportModeEnum.TAXI,
    "physical_mode:default_physical_mode" : PublicTransportModeEnum.UNKNOWN,
    "physical_mode:Bus" : PublicTransportModeEnum.BUS,
    "physical_mode:Tramway" : PublicTransportModeEnum.TRAM,
    "physical_mode:Ferry" : PublicTransportModeEnum.WATER,
    "physical_mode:RapidTransit" : PublicTransportModeEnum.URBANRAIL,
    "physical_mode:LocalTrain" : PublicTransportModeEnum.RAIL,
    "physical_mode:LongDistanceTrain" : PublicTransportModeEnum.INTERCITYRAIL,
    "physical_mode:Train" : PublicTransportModeEnum.RAIL,
    "physical_mode:Metro" : PublicTransportModeEnum.METRO,
    "physical_mode:Air" : PublicTransportModeEnum.AIR,
    "physical_mode:CheckIn" : PublicTransportModeEnum.AIR,
    "physical_mode:CheckOut" : PublicTransportModeEnum.AIR,
}


TRANSPORT_MODE_MAPPING = {
    # TransportModeEnum : [Navitia physical and/or commercial modes]}
    TransportModeEnum.BUS : ["physical_mode:Bus",
                             "commercial_mode:BHNS", 
                             "commercial_mode:busway"],
    TransportModeEnum.TROLLEYBUS : ["commercial_mode:BHNS", 
                                    "commercial_mode:busway"],
    TransportModeEnum.TRAM : ["physical_mode:Tramway"],
    TransportModeEnum.COACH : ["physical_mode:Coach"],
    TransportModeEnum.RAIL : ["physical_mode:Train", 
                              "physical_mode:LongDistanceTrain",
                              "physical_mode:RapidTransit",
                              "physical_mode:Metro",
                              "physical_mode:Tramway",
                              "physical_mode:LocalTrain"],
    TransportModeEnum.INTERCITYRAIL : ["physical_mode:LongDistanceTrain"],
    TransportModeEnum.URBANRAIL : ["physical_mode:RapidTransit", 
                                   "physical_mode:Metro",
                                   "physical_mode:Tramway"],
    TransportModeEnum.METRO : ["physical_mode:Metro"],
    TransportModeEnum.AIR : ["physical_mode:Air"],
    TransportModeEnum.WATER : ["physical_mode:Ferry", 
                               "commercial_mode:Bateau"],
    # TransportModeEnum.CABLE : "physical_mode:Tramway",
    # TransportModeEnum.FUNICULAR : "physical_mode:Tramway",
    TransportModeEnum.TAXI : ["physical_mode:Taxi"],
    TransportModeEnum.BIKE : ["commercial_mode:C72TAD"],
    TransportModeEnum.CAR : ["commercial_mode:C72TAD"]
}

SELF_DRIVE_MODE_MAPPING = {
    # SelfDriveModeEnum : [Navitia modes]
    SelfDriveModeEnum.WALK : ["walking"],
    SelfDriveModeEnum.CAR : ["car"],
    SelfDriveModeEnum.BIKE : ["bike", "bss"],
}

# Navitia mode : SelfDriveModeEnum
INVERSE_SELF_DRIVE_MODE_MAPPING = {}
for k, v in SELF_DRIVE_MODE_MAPPING.items():
    for x in v:
        INVERSE_SELF_DRIVE_MODE_MAPPING[x] = k


def parse_end_point(point):
    site = SiteTypeType()
    site.id = point["id"]
    site.Name = point["name"]
    embedded_type = point["embedded_type"]
    site.SiteType = SITE_TYPE_MAPPING.get(embedded_type, 
                                          SiteTypeEnum.LOCATION)

    point_data = point[embedded_type]
    for r in point_data.get("administrative_regions", []):
        if r["level"] == 8: # City level
            site.CityCode = r["id"]
            site.CityName = r["name"]
    site.Position = PositionType(Lat=point_data["coord"]["lat"], 
                                 Long=point_data["coord"]["lon"])

    return EndPointType(Site=StopPlaceType(Parent=site))


def parse_stop_times(stop_times):
    def parse_step_point(point):
        site = SiteTypeType()
        site.id = point["id"]
        site.Name = point["name"]
        site.SiteType = SITE_TYPE_MAPPING["stop_point"]
        site.Position = PositionType(Lat=point["coord"]["lat"], 
                                     Long=point["coord"]["lon"])

        return StepEndPointType(StopPlace=StopPlaceType(Parent=site))


    if not stop_times or len(stop_times) < 2:
        return None

    steps = []
    for i in range(0, len(stop_times) - 1):
        s1 = stop_times[i]
        s2 = stop_times[i+1]
        step = StepType()
        step.id = "%s:%s" % (s1["stop_point"]["id"], s2["stop_point"]["id"])
        # TODO what if it is not a 'stop_point'
        step.Departure = parse_step_point(s1["stop_point"])
        step.Arrival = parse_step_point(s2["stop_point"])
        step.Departure.Time = datetime.strptime(s1['arrival_date_time'], DATE_FORMAT)
        step.Arrival.Time = datetime.strptime(s2['arrival_date_time'], DATE_FORMAT)
        # Duration in minutes
        step.Duration = (step.Arrival.Time - step.Departure.Time).total_seconds() / 60
        steps.append(step)

    return steps


def journey_to_sumed_up_trip(journey):
    if not journey:
        return None

    trip = SumedUpTripType()
    trip.InterchangeCount = journey["nb_transfers"]
    sections = clean_sections(journey.get('sections', []))
    if not sections:
        logging.debug("No section found")
        return None

    first_section = sections[0]
    # logging.debug("First section %s", first_section)
    last_section = sections[-1]
    # logging.debug("Last section %s", last_section)
    trip.Departure = parse_end_point(first_section['from'])
    trip.Departure.Time = datetime.strptime(first_section['departure_date_time'], DATE_FORMAT)
    trip.Arrival = parse_end_point(last_section['to'])
    trip.Arrival.Time = datetime.strptime(last_section['arrival_date_time'], DATE_FORMAT)
    trip.InterchangeDuration = 0
    for s in [x for x in sections if x["type"] != SectionTypeEnum.PUBLIC_TRANSPORT]:
        trip.InterchangeDuration += s["duration"]

    return trip


# TODO maybe delete it, not useful anymore
# Remove some unnecessary sections.
def clean_sections(sections):
    # We ignore all sections before the first section 
    # of type PUBLIC_TRANSPORT or after the last section of type 
    # PUBLIC_TRANSPORT.
    first = 0
    last = 0
    for i in range(0, len(sections)):
        if sections[i]["type"] == SectionTypeEnum.PUBLIC_TRANSPORT:
            first = i
            break

    for i in reversed(range(0, len(sections))):
        if sections[i]["type"] == SectionTypeEnum.PUBLIC_TRANSPORT:
            last = i
            break

    sections = sections[first:last+1]
    return sections


def journey_to_str(journey):
    return ("<Journey> Departure: %s|Arrival: %s|Duration: %s|"
            "Nb_transfers: %s|Type: %s" % (journey["departure_date_time"],
            journey["arrival_date_time"], journey["duration"],
            journey["nb_transfers"], journey["type"]))

def parse_journey(journey):
    if not journey:
        return None

    trip = TripType()
    trip.DepartureTime = datetime.strptime(journey["departure_date_time"], DATE_FORMAT)
    trip.ArrivalTime = datetime.strptime(journey["arrival_date_time"], DATE_FORMAT)
    trip.Duration = journey["duration"]
    trip.KmlOverview = ""
    trip.Distance = 0
    trip.Disrupted = False
    trip.InterchangeNumber = journey["nb_transfers"]
    trip.CarFootprint = None

    trip.sections = []
    sections = clean_sections(journey['sections'])
    for s in sections:
        # logging.debug("SECTION: %s", s)
        section = SectionType()
        section.PartialTripId = s["id"]
        if s["type"] == SectionTypeEnum.PUBLIC_TRANSPORT:
            ptr = PTRideType()
            ptr.ptNetworkRef = s["display_informations"]["network"]
            ptr.lineRef = s["display_informations"]["code"]
            physical_mode_id = next((x["id"] for x in s.get("links", []) if x["type"] == "physical_mode"), "")
            ptr.PublicTransportMode = PUBLIC_TRANSPORT_MODE_MAPPING.get(
                                            physical_mode_id, 
                                            PublicTransportModeEnum.UNKNOWN)
            ptr.Departure = parse_end_point(s["from"])
            ptr.Arrival = parse_end_point(s["to"])
            ptr.Departure.Site.Parent.Time = datetime.strptime(s["departure_date_time"], DATE_FORMAT)
            ptr.Arrival.Site.Parent.Time = datetime.strptime(s["arrival_date_time"], DATE_FORMAT)
            ptr.Duration = s["duration"]
            # TODO remove that hard coded 0 index
            ptr.Distance = s["geojson"]["properties"][0]["length"]
            ptr.steps = parse_stop_times(s.get("stop_date_times", None))
            section.PTRide = ptr
        else: # Consider section as LegType
            # TODO handle waiting status 
            if s["type"] == SectionTypeEnum.WAITING:
                continue
            leg = LegType()
            leg.Departure = parse_end_point(s["from"])
            leg.Arrival = parse_end_point(s["to"])
            leg.Departure.Site.Parent.Time = datetime.strptime(s["departure_date_time"], DATE_FORMAT)
            leg.Arrival.Site.Parent.Time = datetime.strptime(s["arrival_date_time"], DATE_FORMAT)
            leg.Duration = s["duration"]
            leg.SelfDriveMode = INVERSE_SELF_DRIVE_MODE_MAPPING.get(
                                    s["transfer_type"], SelfDriveModeEnum.WALK)
            section.Leg = leg

        trip.sections.append(section)


    # Navitia doesn't send global departure and arrival items, we have to get 
    # them from sections.
    if trip.sections:
        l = lambda obj, attr1, attr2: getattr(obj, attr1) or getattr(obj, attr2)
        trip.Departure = l(trip.sections[0], 'PTRide', 'Leg').Departure
        trip.Arrival = l(trip.sections[-1], 'PTRide', 'Leg').Arrival

    return trip


def algo_classic(journeys, departure_at=False):
    if departure_at:
        # Get journey with minimum arrival time
        l = sorted([(x, datetime.strptime(x["arrival_date_time"], DATE_FORMAT)) \
                    for x in journeys], 
                    key=itemgetter(1))
    else:
        # Get journey with maximum departure time
        l = sorted([(x, datetime.strptime(x["departure_date_time"], DATE_FORMAT)) \
                    for x in journeys], 
                    key=itemgetter(1), reverse=True)

    # Find all journeys that match given criteria. If there is only one, this is 
    # the best journey, if there are multiple ones, we'll have to filter results a 
    # bit further.
    first_selection = [x[0] for x in l if x[1] == l[0][1]]
    if len(first_selection) <= 1:
        return first_selection[0]
    
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

    # If we still haven't found a unique best journey (remember this is possible 
    # as these journeys come from different Navitia requests, so we can have 
    # multiple journeys with type "best"), look for the journey with maximum 
    # departure_time or with minimum arrival_time, depending on the departure_at 
    # parameter.
    if departure_at:
        l = sorted([(x, datetime.strptime(x["departure_date_time"], DATE_FORMAT)) \
                    for x in second_selection], 
                    key=itemgetter(1), reverse=True)
    else:
        l = sorted([(x, datetime.strptime(x["arrival_date_time"], DATE_FORMAT)) \
                    for x in second_selection], 
                    key=itemgetter(1))

    return l[0][0]


def algo_shortest(journeys):
    # Get journey with minimum number of transfers
    l = sorted([(x, x["nb_transfers"]) for x in journeys], key=itemgetter(1))
    return l[0][0]


def algo_fastest(journeys):
    # Get journey with minimum duration
    l = sorted([(x, x["duration"]) for x in journeys], key=itemgetter(1))
    return l[0][0]


def algo_minchanges(journeys):
    # Get journey with minimum transfer duration
    transfer_durations = [] # [(journey, transfer_duration)]
    for j in journeys:
        transfer_durations.append( \
                (j, sum([x["duration"] for x in j["sections"] \
                         if x["type"] != SectionTypeEnum.PUBLIC_TRANSPORT])))
    l = sorted(transfer_durations, key=itemgetter(1))
    logging.debug("transfer_durations: Best %s from %s", l[0][1], [x[1] for x in transfer_durations])
    return l[0][0]


def choose_best_journey(journeys, algo, departure_at=True):
    logging.debug("Algorithm: %s\n"
                  "Number of journeys: %s\n"
                  "Departure at: %s", len(journeys), algo, departure_at)
    if not journeys:
        return None

    best = None
    if algo == AlgorithmEnum.CLASSIC:
        best = algo_classic(journeys, departure_at)
    elif algo == AlgorithmEnum.SHORTEST:
        best = algo_shortest(journeys)
    elif algo == AlgorithmEnum.FASTEST:
        best = algo_fastest(journeys)
    elif algo == AlgorithmEnum.MINCHANGES:
        best = algo_minchanges(journeys)

    logging.debug("BEST: %s \nFROM %s", journey_to_str(best), 
                                        [journey_to_str(x) for x in journeys])
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


def get_params(departure_time, arrival_time, modes, self_drive_conditions):
    params = {}

    if departure_time:
        params['datetime'] = departure_time.strftime(DATE_FORMAT)
        params['datetime_represents'] = 'departure'
    else:
        params['datetime'] = arrival_time.strftime(DATE_FORMAT)
        params['datetime_represents'] = 'arrival'

    params["forbidden_uris[]"] = modes_to_forbidden_uris(modes)
    params["first_section_mode[]"] = list(
                                        SELF_DRIVE_MODE_MAPPING[SelfDriveModeEnum.WALK])
    params["last_section_mode[]"] = list(
                                        SELF_DRIVE_MODE_MAPPING[SelfDriveModeEnum.WALK])

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

    return params


class MisApi(MisApiBase):

    def __init__(self, api_key=""):
        # self._api_url = "http://api.navitia.io/v1/coverage/paris"
        self._api_url = "http://navitia2-ws.ctp.dev.canaltp.fr//v1/coverage/paysdelaloire/"
        self._api_key = api_key
        self._http = None

    def _journeys_request(self, params=[]):
        url = self._api_url + "/journeys" + '?' + urllib.urlencode(params, True)
        resp, content = self._send_request(url)

        # Navitia may give us multiple journeys, we retrieve them all and then 
        # choose the best according to request parameters.
        content = json.loads(content)
        logging.debug("NB JOURNEYS: %s", len(content.get("journeys", [])))
        return [x for x in content.get("journeys", [])]


    def _send_request(self, url):
        if not self._http:
            self._http = httplib2.Http(".cache")

        logging.debug("NAVITIA URL %s", url)

        headers = {'Authorization' : self._api_key}

        resp, content = self._http.request(url, "GET", headers=headers)
        if resp.status == 200:
            return resp, content

        exc_msg = "GET <%s> FAILED: %s" % (url, resp.status)
        logging.error(exc_msg)
        try:
            content = json.loads(content)
        except:
            content = {}
        if resp.status == 404:
            error_id = content.get("error", {}).get("id", "")
            if error_id == 'date_out_of_bounds':
                raise MisApiDateOutOfScopeException(exc_msg)
        elif resp.status == 400:
            raise MisApiBadRequestException(exc_msg)
        elif resp.status == 401:
            raise MisApiUnauthorizedException(exc_msg)
        elif resp.status == 500:
            raise MisApiInternalErrorException(exc_msg)
        raise MisApiException(exc_msg)


    def get_stops(self):
        base_url = self._api_url + "/stop_areas"
        params = {"count" : ITEMS_PER_PAGE}
        stops = []
        # TODO delete that, just here for testing purposes
        max_pages = 10
        pages_read = 0
        while True:
            url = base_url + ("&" if "?" in base_url else "?") + urllib.urlencode(params)
            resp, content = self._send_request(url)

            content = json.loads(content)
            for s in  content["stop_areas"]:
                stops.append(Stop(code=s["id"],
                                  name=s["name"],
                                  lat=s["coord"]["lat"],
                                  long=s["coord"]["lon"]))

            for s in  content["links"]:
                if "type" in s and s['type'] == "next":
                    next_base_url = s["href"]

            if base_url == next_base_url:
                # We have read all pages, quit
                break
            else:
                # Read next page
                base_url = next_base_url

            # TODO delete that, just here for testing purposes
            pages_read = pages_read  + 1
            if pages_read > max_pages:
                break

        return stops


    def get_itinerary(self, departures, arrivals, departure_time, arrival_time,
                      algorithm=AlgorithmEnum.CLASSIC, modes=[], 
                      self_drive_conditions=[],
                      accessibility_constraint=False,
                      language=""):
        params = get_params(departure_time, arrival_time, 
                            modes, self_drive_conditions)
        journeys = []
        # Request journeys for every departure/arrival pair and then
        # choose best.
        if len(departures) > 1:
            params['to'] = arrivals[0].QuayId
            for d in departures:
                params['from'] = d.QuayId
                journeys.extend(self._journeys_request(params))
        else:
            params['from'] = departures[0].QuayId
            for a in arrivals:
                params['to'] = a.QuayId
                journeys.extend(self._journeys_request(params))

        best_journey = choose_best_journey(journeys, algorithm)
        # If no journey found, DetailedTrip is None
        return ItineraryResponseType(DetailedTrip=parse_journey(best_journey))


    def get_sumed_up_itineraries(self, departures, arrivals, departure_time, 
                                 arrival_time, algorithm=AlgorithmEnum.CLASSIC, 
                                 modes=[], self_drive_conditions=[],
                                 accessibility_constraint=False,
                                 language="", options=[]):
        params = get_params(departure_time, arrival_time, 
                            modes, self_drive_conditions)

        # Request itinerary for every departure/arrival pair and then
        # choose best.
        journeys = []
        for d in departures:
            for a in arrivals:
                params['from'] = d.QuayId
                params['to'] = a.QuayId
                for j in self._journeys_request(params):
                    journeys.append((d, a, j))

        best_journeys = []
        if departure_time:
            for a in arrivals:
                journeys_to_arrival = [x[2] for x in journeys if x[1] == a]
                best_journeys.append(
                        choose_best_journey(journeys_to_arrival, algorithm))
        else:
            for d in departures:
                journeys_from_departure = [x[2] for x in journeys if x[0] == d]
                best_journeys.append(
                        choose_best_journey(journeys_from_departure, algorithm,
                                            departure_at=False))

        ret = SumedUpItinerariesResponseType()
        ret.sumedUpTrips = [journey_to_sumed_up_trip(x) for x in best_journeys]

        logging.debug("Sumed up trips (%s) : %s", len(ret.sumedUpTrips), ret.sumedUpTrips)

        return ret
