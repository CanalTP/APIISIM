from apiisim.planner import MisApi, benchmark, stop_to_trace_stop, \
    create_full_notification, NoItineraryFoundException
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased
from apiisim import metabase
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, GenericFunction
from geoalchemy2.functions import ST_Intersects
from apiisim.common.plan_trip import PlanTripExistenceNotificationResponseType, \
    ProviderType
from apiisim.common.mis_plan_summed_up_trip import SummedUpItinerariesRequestType
from apiisim.common.mis_plan_trip import ItineraryRequestType, multiDeparturesType, \
    multiArrivalsType
from apiisim.common import TransportModeEnum, PlanSearchOptions
from apiisim.planner import CancelledRequestException
import logging


class StGeogFromText(GenericFunction):
    name = 'ST_GeogFromText'
    type = Geography


class PlanTripCalculator(object):
    # Maximum MIS trace length
    MAX_TRACE_LENGTH = 3
    SURROUNDING_MISES_MAX_DISTANCE = 400  # In meters

    def __init__(self, planner, params, notif_queue):
        self._planner = planner
        self._db_session = self._planner.create_db_session()
        self._params = params
        self._notif_queue = notif_queue
        self._cancelled = False

    def __del__(self):
        logging.debug("Deleting PlanTripCalculator instance")
        if self._db_session:
            self._planner.remove_db_session(self._db_session)

    def stop(self):
        self._cancelled = True

    @benchmark
    def _get_transfers(self, mis1_id, mis2_id):
        # ([transfer_duration], [stop_mis1], [stop_mis2])
        # To ease further processing (in compute_trip()), stops are returned
        # as TraceStop objects, not as metabase.Stop objects.
        ret = ([], [], [])
        subq = self._db_session.query(metabase.TransferMis.transfer_id) \
            .filter(or_(and_(metabase.TransferMis.mis1_id == mis1_id,
                             metabase.TransferMis.mis2_id == mis2_id),
                        and_(metabase.TransferMis.mis1_id == mis2_id,
                             metabase.TransferMis.mis2_id == mis1_id))).filter(
            metabase.TransferMis.transfer_active == True).order_by(metabase.TransferMis.transfer_id).subquery()
        # logging.debug("transfers_ids : %s", transfers_ids)
        s1 = aliased(metabase.Stop)
        s2 = aliased(metabase.Stop)

        results = self._db_session.query(metabase.Transfer, s1, s2) \
            .filter(metabase.Transfer.id == subq.c.transfer_id) \
            .filter(and_(metabase.Transfer.stop1_id == s1.id),
                    metabase.Transfer.stop2_id == s2.id) \
            .all()
        for t, s1, s2 in results:
            l1 = stop_to_trace_stop(s1)
            l2 = stop_to_trace_stop(s2)
            if s1.mis_id == mis1_id:  # implies s2.mis_id == mis2_id
                ret[0].append(timedelta(seconds=t.duration))
                ret[1].append(l1)
                ret[2].append(l2)
            elif s1.mis_id == mis2_id:  # implies s2.mis_id == mis1_id
                ret[0].append(timedelta(seconds=t.duration))
                ret[1].append(l2)
                ret[2].append(l1)
            else:
                raise Exception("Inconsistency in database, transfer %s is"
                                "not coherent with its stops %s %s", t, s1, s2)

        # logging.debug("ret: len %s len %s\n%s", len(ret[mis1_id]), len(ret[mis2_id]), ret)
        return ret

    """
        Return set of MIS that:
            - have at least one stop point whose distance to given position is
              less than max_distance.
            - if MIS provides a shape, given point must be included in this shape.
        Also ensure that returned MIS are available at given date.
        Note that date must of type 'date', not 'datetime'.
    """

    @benchmark
    def _get_surrounding_mis(self, position, date):
        ret = set()  # ([mis_id])
        all_mises = self._db_session.query(metabase.Mis).all()

        for mis in all_mises:
            if self._db_session.query(metabase.Stop.id) \
                    .filter(metabase.Stop.mis_id == mis.id) \
                    .filter(ST_DWithin(
                    metabase.Stop.geog,
                    StGeogFromText('POINT(%s %s)' % (position.Longitude, position.Latitude)),
                    self.SURROUNDING_MISES_MAX_DISTANCE)).count() > 0 and (mis.start_date <= date <= mis.end_date):

                shape = MisApi(self._db_session, mis.id).get_shape()
                if shape:
                    intersect = self._db_session.query(ST_Intersects(
                        StGeogFromText('POINT(%s %s)' % (position.Longitude, position.Latitude)),
                        StGeogFromText(shape))).one()[0]
                    logging.debug("INTERSECTS <%s>: %s", mis.name, intersect)
                    if intersect:
                        ret.add(mis.id)
                else:
                    ret.add(mis.id)

        logging.info("MIS surrounding point (%s %s): %s",
                     position.Longitude, position.Latitude, ret)
        return ret

    def _get_mis_modes(self, mis_id):
        return set([x[0] for x in
                    self._db_session.query(metabase.Mode.code)
                        .filter(metabase.MisMode.mis_id == mis_id)
                        .filter(metabase.Mode.id == metabase.MisMode.mode_id)
                        .all()])

    @benchmark
    def _get_connected_mis(self, mis_id):
        s1 = set([x[0] for x in
                  self._db_session.query(metabase.MisConnection.mis1_id)
                      .filter(metabase.MisConnection.mis2_id == mis_id)
                      .all()])
        s2 = set([x[0] for x in
                  self._db_session.query(metabase.MisConnection.mis2_id)
                      .filter(metabase.MisConnection.mis1_id == mis_id)
                      .all()])
        return s1 | s2

    @benchmark
    def _get_mis_traces(self, departure_mises, arrival_mises, max_trace_length):
        ret = []  # [[mis_id]] each mis_id list is a trace
        if max_trace_length < 1:
            logging.warning("Requesting MIS traces with max_trace_length < 1")
            return ret

        # Add all Mis in common
        for mis in (departure_mises & arrival_mises):
            ret.append([mis])
        if max_trace_length == 1:
            return ret

        for mis_id in departure_mises:
            connected_mis = self._get_connected_mis(mis_id)
            for sub_trace in self._get_mis_traces(connected_mis,
                                                 arrival_mises, max_trace_length - 1):
                if not mis_id in sub_trace:
                    sub_trace.insert(0, mis_id)
                    ret.append(sub_trace)

        return ret

    def _generate_trace_id(self, mis_trace):
        return "_".join(map(str, mis_trace))

    def _get_trace_transfers(self, mis_trace):
        # {mis1_id : {mis2_id : transfers},
        # mis2_id : {mis3_id : transfers, ...}
        ret = {}
        for i in range(0, len(mis_trace) - 1):
            mis1_id = mis_trace[i]
            mis2_id = mis_trace[i + 1]
            t = self._get_transfers(mis1_id, mis2_id)
            if mis1_id not in ret:
                ret[mis1_id] = {}
            ret[mis1_id][mis2_id] = t

        return ret

    def _get_providers(self, mis_trace):
        ret = []  # [ProviderType]
        for mis_id in mis_trace:
            mis_api = MisApi(self._db_session, mis_id)
            ret.append(ProviderType(
                Name=mis_api.get_name(),
                Url=mis_api.get_api_url()))
        return ret

    def _filter_traces(self, traces):
        # For each trace, check that MISes that are 'in the middle' of the trace,
        # (i.e. not the first or last MIS of trace) support n-m itineraries requests.
        # If not, ignore that trace.
        ret = []
        for t in traces:
            is_valid = True
            for mis_id in t[1:-1]:
                if not MisApi(self._db_session, mis_id).get_multiple_starts_and_arrivals():
                    is_valid = False
                    break
            if is_valid:
                ret.append(t)
        return ret

    @benchmark
    def compute_traces(self):
        # Get Mis near departure and arrival points
        date = (self._params.DepartureTime or self._params.ArrivalTime).date()

        logging.info("Finding departure MIS...")
        departure_mis = self._get_surrounding_mis(self._params.Departure.Position, date)
        # Filter out Mis that don't support at least one of the requested modes
        if self._params.modes and not TransportModeEnum.ALL in self._params.modes:
            departure_mis = set([x for x in departure_mis if (set(self._params.modes) & self._get_mis_modes(x))])
        logging.info("Departure MIS (compatible modes): %s", departure_mis)

        logging.info("Finding arrival MIS...")
        arrival_mis = self._get_surrounding_mis(self._params.Arrival.Position, date)
        # Filter out Mis that don't support at least one of the requested modes
        if self._params.modes and not TransportModeEnum.ALL in self._params.modes:
            arrival_mis = set([x for x in arrival_mis if (set(self._params.modes) & self._get_mis_modes(x))])
        logging.info("Arrival MIS (compatible modes): %s", arrival_mis)

        return self._filter_traces(
            self._get_mis_traces(departure_mis, arrival_mis, self.MAX_TRACE_LENGTH))

    def _list_of_location_context_to_str(self, location_list):
        def location_context_to_str(location):
            if not location.PlaceTypeId:
                return "%s;%s" % (location.Position.Longitude, location.Position.Latitude)
            else:
                if location.AccessTime:
                    return "%s (%s)" % (location.PlaceTypeId, location.AccessTime)
                else:
                    return location.PlaceTypeId

        if not location_list:
            return "None"
        log_str = ""
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            for item in location_list:
                if log_str:
                    log_str += " - "
                log_str += location_context_to_str(item)
        else:
            for item in location_list[0:3]:
                if log_str:
                    log_str += " - "
                log_str += location_context_to_str(item)
            if len(location_list) > 3:
                log_str += " ... "

        return log_str

    def _log_detailed_trace(self, mis_trace):
        logging.info("Detailing trace...")
        count = 1
        for mis in mis_trace:
            logging.info("Region %d - MIS %s " % (count, mis[0].get_name()))
            logging.info(" + Org: %s " % self._list_of_location_context_to_str(mis[1]))
            logging.info(" + Dst: %s " % self._list_of_location_context_to_str(mis[2]))
            logging.info(" + Lnk: %s " % self._list_of_location_context_to_str(mis[3]))
            count += 1

    # (
    # MisApi,
    # [TraceStop], # departures
    # [TraceStop], # arrivals
    # [TraceStop], # linked_stops (stops linked to arrivals via a transfer)
    # [timedelta]  # transfer_durations
    # )

    @benchmark
    def _detailed_trace(self, mis_trace):
        i = 0
        ret = []
        # [
        # (
        # MisApi,
        # [TraceStop], # departures
        # [TraceStop], # arrivals
        # [TraceStop], # linked_stops (stops linked to arrivals via a transfer)
        # [timedelta]  # transfer_durations
        # )
        # ]

        if len(mis_trace) < 2:
            raise Exception("mis_trace length must be > 1")

        transfers = self._get_trace_transfers(mis_trace)
        while True:
            # Divide trace in chunks of 3 MIS
            chunk = mis_trace[i:i + 3]
            if not chunk:
                break
            logging.debug("CHUNK: %s", chunk)

            trace_start = self._params.Departure if i == 0 else None
            trace_end = self._params.Arrival if len(mis_trace) <= (i + 3) else None
            mis1_id = chunk[0]
            mis2_id = chunk[1] if len(chunk) > 1 else 0
            mis3_id = chunk[2] if len(chunk) > 2 else 0
            mis1_api = MisApi(self._db_session, mis1_id) if mis1_id else None
            mis2_api = MisApi(self._db_session, mis2_id) if mis2_id else None
            mis3_api = MisApi(self._db_session, mis3_id) if mis3_id else None

            if trace_start:
                ret = [(mis1_api,
                        [trace_start],
                        transfers[mis1_id][mis2_id][1],
                        transfers[mis1_id][mis2_id][2],
                        transfers[mis1_id][mis2_id][0])]

            if mis3_id:
                ret.append(
                    (mis2_api,
                     transfers[mis1_id][mis2_id][2],
                     transfers[mis2_id][mis3_id][1],
                     transfers[mis2_id][mis3_id][2],
                     transfers[mis2_id][mis3_id][0]))

                if trace_end:
                    ret.append(
                        (mis3_api,
                         transfers[mis2_id][mis3_id][2],
                         [trace_end],
                         None,
                         None))
                    break
            else:
                if trace_end:
                    ret.append(
                        (mis2_api,
                         transfers[mis1_id][mis2_id][2],
                         [trace_end],
                         None,
                         None))
                    break
            i += 1

        return ret

    def _init_request(self, request):
        request.id = self._params.clientRequestId
        request.Algorithm = self._params.Algorithm
        request.modes = self._params.modes
        request.selfDriveConditions = self._params.selfDriveConditions
        request.AccessibilityConstraint = self._params.AccessibilityConstraint
        request.Language = self._params.Language

    def _single_mis_trip(self, mis_id, trace_id, providers):
        # Return best "meta-trip", which is a list of detailed trips.
        ret = []  # [(mis_api, DetailedTrip)]

        detailed_request = ItineraryRequestType()
        self._init_request(detailed_request)
        detailed_request.multiDepartures = multiDeparturesType()
        detailed_request.multiDepartures.Departure = [self._params.Departure]
        detailed_request.multiDepartures.Arrival = self._params.Arrival
        detailed_request.DepartureTime = self._params.DepartureTime
        detailed_request.ArrivalTime = self._params.ArrivalTime
        mis_api = MisApi(self._db_session, mis_id)
        resp = mis_api.get_itinerary(detailed_request)
        if not resp.DetailedTrip:
            raise NoItineraryFoundException()
        ret.append((mis_api, resp.DetailedTrip))

        notif = PlanTripExistenceNotificationResponseType(
            RequestId=self._params.clientRequestId,
            ComposedTripId=trace_id,
            DepartureTime=resp.DetailedTrip.Departure.DateTime,
            ArrivalTime=resp.DetailedTrip.Arrival.DateTime,
            Duration=resp.DetailedTrip.Duration,
            providers=providers,
            Departure=self._params.Departure, Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        return ret

    """
        Update transition stops after receiving itinerary results from a MIS.
            - Departure/Arrival time is updated according to trips data.
            - If no itinerary is found from/to a given departure/arrival stop, this stop (and
              its linked stops & linked durations) are removed from the whole "meta-trip".
    """

    def _update_stop_times(self, transition_stops, linked_stops, transition_durations,
                           stop_field, trips, trip_field):
        logging.debug("Updating transition stops...")
        log_str = ""
        for stop in transition_stops:
            if log_str:
                log_str += ", "
            log_str += stop.PlaceTypeId
        logging.debug(". Req %d %s: %s", len(transition_stops), trip_field, log_str)

        log_str = ""
        for trip in trips:
            if log_str:
                log_str += ", "
            log_str += getattr(trip, trip_field).TripStopPlace.id
        logging.debug(". Ret %d %s: %s", len(trips), trip_field, log_str)

        to_del = []
        for stop in transition_stops:
            found = False
            for trip in trips:
                if stop.PlaceTypeId == getattr(trip, trip_field).TripStopPlace.id:
                    setattr(stop, stop_field, getattr(trip, trip_field).DateTime)
                    found = True
                    break
            if not found:
                # No itinerary found from/to this transition point, so remove this point
                # from the trip, along with its linked stops.
                to_del.extend([i for i, x in enumerate(transition_stops) if x == stop])

        to_del = set(to_del)
        for i in sorted(to_del, reverse=True):
            deleted_stop = transition_stops.pop(i)
            # logging.debug("No itinerary found using stop point %s, deleting it", deleted_stop)
            if linked_stops:
                deleted_stop = linked_stops.pop(i)
                # logging.debug("Also deleting its linked stop point %s", deleted_stop)
                transition_durations.pop(i)

        if not transition_stops:
            raise NoItineraryFoundException()

    """
        Update transition transfers after receiving itinerary results from a MIS.
            - Compute Departure/Arrival time after transfer
            - Filter out not optimal transfers
    """

    def _update_linked_stop_times(self, transition_stops, linked_stops, transition_durations, clockwise):
        transition_by_linked = {}
        for i, s, l, t in zip(range(len(transition_stops)), transition_stops, linked_stops, transition_durations):
            if clockwise:
                l.arrival_time = s.arrival_time + t
            else:
                l.departure_time = s.departure_time - t
            if not l in transition_by_linked:  # "PlaceTypeId" field is checked (TraceStop)
                transition_by_linked[l] = []
            transition_by_linked[l].append((i, l.arrival_time if clockwise else l.departure_time))

        to_del = []
        for a in transition_by_linked:
            links = transition_by_linked[a]
            if len(links) < 2:
                continue
            links.sort(key=lambda x: x[1], reverse=not clockwise)
            to_del.extend([pair[0] for pair in links[1:]])

        to_del = set(to_del)
        for i in sorted(to_del, reverse=True):
            transition_stops.pop(i)
            linked_stops.pop(i)
            transition_durations.pop(i)

    """
        Update arrival stops after receiving itinerary results from a MIS.
            - Arrival time is updated according to trips data.
            - If no itinerary is found to a given arrival stop, this stop (and
              its linked stops) are removed from the whole "meta-trip".
            - Compute transition times and filter in best results.
    """

    def _update_transition_arrivals(self, arrivals, linked_stops, transition_durations, trips):
        self._update_stop_times(arrivals, linked_stops, transition_durations,
                                "arrival_time", trips, "Arrival")
        if linked_stops:
            self._update_linked_stop_times(arrivals, linked_stops, transition_durations, clockwise=True)

    """
        Update departure stops after receiving itinerary results from a MIS.
            - Departure time is updated according to trips data.
            - If no itinerary is found from a given departure stop, this stop
              (and its linked stops) are removed from the whole "meta-trip".
            - Compute transition times and filter in best results.
    """

    def _update_transition_departures(self, departures, linked_stops, transition_durations, trips):
        self._update_stop_times(departures, linked_stops, transition_durations,
                                "departure_time", trips, "Departure")
        if linked_stops:
            self._update_linked_stop_times(departures, linked_stops, transition_durations, clockwise=False)

    """
        Keep only the best trip from SIM response
    """

    def _filter_best_trip_response(self, resp_trips, clockwise):
        if len(resp_trips) == 0:
            return
        if clockwise:
            best_time = min([x.Arrival.DateTime for x in resp_trips])
            to_del = [i for i, x in enumerate(resp_trips) if x.Arrival.DateTime != best_time]
        else:
            best_time = max([x.Departure.DateTime for x in resp_trips])
            to_del = [i for i, x in enumerate(resp_trips) if x.Departure.DateTime != best_time]

        to_del = set(to_del)
        for i in sorted(to_del, reverse=True):
            trip = resp_trips[i]
            logging.debug("Remove bad trip from MIS response %s (%s) -> %s (%s)", trip.Departure.TripStopPlace.id,
                          trip.Departure.DateTime, trip.Arrival.TripStopPlace.id, trip.Arrival.DateTime)
            resp_trips.pop(i)

    def _clear_access_time(self, departures, arrivals):
        for d in departures:
            d.AccessTime = timedelta()
        for a in arrivals:
            a.AccessTime = timedelta()

    def _log_calculation_step(self, mis_name, dep_time, arr_time, lnk_time, log_dep, log_arr, log_lnk, clockwise):
        if lnk_time:
            if clockwise:
                logging.info("Step %d - %s : dep %s arr %s lnk %s" %
                             (self.step, mis_name, dep_time, arr_time, lnk_time))
            else:
                logging.info("Step %d - %s : lnk %s dep %s arr %s" %
                             (self.step, mis_name, lnk_time, dep_time, arr_time))
        else:
            logging.info("Step %d - %s : dep %s arr %s" %
                         (self.step, mis_name, dep_time, arr_time))

        if clockwise:
            logging.info("Step %d - %s : Org %s" %
                         (self.step, mis_name, self._list_of_location_context_to_str(log_dep)))
            logging.info("Step %d - %s : Dst %s" %
                         (self.step, mis_name, self._list_of_location_context_to_str(log_arr)))
        else:
            logging.info("Step %d - %s : Dst %s" %
                         (self.step, mis_name, self._list_of_location_context_to_str(log_arr)))
            logging.info("Step %d - %s : Org %s" %
                         (self.step, mis_name, self._list_of_location_context_to_str(log_dep)))

        if log_lnk:
            logging.info("Step %d - %s : Lnk %s" %
                         (self.step, mis_name, self._list_of_location_context_to_str(log_lnk)))

        self.step += 1

    # Report intermediate results
    def _log_calculation_results(self, mis_name, departures, arrivals, linked_stops, req_time, clockwise,
                                 target_time=None):
        if clockwise:
            if len(departures) > 1:
                rep_dep = sorted(departures, key=lambda lambda_s: lambda_s.arrival_time)
            else:
                rep_dep = departures
            if linked_stops:
                rep_arr, rep_lnk = tuple(
                    zip(*sorted(zip(arrivals, linked_stops), key=lambda pair: pair[0].arrival_time)))
                for s in rep_arr:
                    s.AccessTime = s.arrival_time - rep_arr[0].arrival_time
                for s in rep_lnk:
                    s.AccessTime = s.arrival_time - rep_lnk[0].arrival_time
            else:
                rep_arr = arrivals
                rep_lnk = []
            self._log_calculation_step(mis_name, req_time,
                                       rep_arr[0].arrival_time if rep_lnk else target_time,
                                       rep_lnk[0].arrival_time if rep_lnk else None,
                                       rep_dep, rep_arr, rep_lnk, clockwise=True)
        else:
            if len(arrivals) > 1:
                rep_arr = sorted(arrivals, key=lambda lambda_s: lambda_s.departure_time, reverse=True)
            else:
                rep_arr = arrivals
            if linked_stops:
                rep_dep, rep_lnk = tuple(
                    zip(*sorted(zip(departures, linked_stops), key=lambda pair: pair[0].departure_time, reverse=True)))
                for s in rep_dep:
                    s.AccessTime = s.departure_time - rep_dep[0].departure_time
                for s in rep_lnk:
                    s.AccessTime = s.departure_time - rep_lnk[0].departure_time
            else:
                rep_dep = departures
                rep_lnk = []
            self._log_calculation_step(mis_name,
                                       rep_dep[0].departure_time if rep_lnk else target_time,
                                       req_time,
                                       rep_lnk[0].departure_time if rep_lnk else None,
                                       rep_dep, rep_arr, rep_lnk, clockwise=False)

    def _process_calculation_step(self, detailed_trace, idx, detailed, clockwise,
                                  origin_mis=False, reversal_mis=False, log_info=""):
        def mis_stops(tr_idx, tr_clockwise):
            if tr_clockwise:
                return detailed_trace[tr_idx]
            else:
                tr_mis_api, tr_departures, tr_arrivals, _, _ = detailed_trace[tr_idx]
                if tr_idx > 0:
                    _, _, tr_linked_stops, _, tr_transfer_durations = detailed_trace[tr_idx - 1]
                else:
                    tr_linked_stops = None
                    tr_transfer_durations = None
                return tr_mis_api, tr_departures, tr_arrivals, tr_linked_stops, tr_transfer_durations

        # read stops relative to this MIS
        mis_api, departures, arrivals, linked_stops, transfer_durations = mis_stops(idx, clockwise)

        # build request
        request = ItineraryRequestType() if detailed else SummedUpItinerariesRequestType()
        self._init_request(request)
        self._clear_access_time(departures, arrivals)
        if detailed:
            if len(departures) > 1:
                request.multiDepartures = multiDeparturesType()
                request.multiDepartures.Departure = list(set(departures))
                request.multiDepartures.Arrival = arrivals[0]
            else:
                request.multiArrivals = multiArrivalsType()
                request.multiArrivals.Departure = departures[0]
                request.multiArrivals.Arrival = list(set(arrivals))
        else:
            request.departures = list(set(departures))
            request.arrivals = list(set(arrivals))
            request.options = [PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED] if reversal_mis else []
        if clockwise:
            if origin_mis:
                request.DepartureTime = self._params.DepartureTime
            else:
                request.DepartureTime = min([x.arrival_time for x in departures])
                for d in departures:
                    d.AccessTime = d.arrival_time - request.DepartureTime
            request.ArrivalTime = None
        else:
            request.DepartureTime = None
            if origin_mis:
                request.ArrivalTime = self._params.ArrivalTime
            else:
                request.ArrivalTime = min([x.departure_time for x in arrivals])
                for a in arrivals:
                    a.AccessTime = a.departure_time - request.ArrivalTime

        # send request
        if self._cancelled:
            raise CancelledRequestException()
        resp = mis_api.get_itinerary(request) if detailed else mis_api.get_summed_up_itineraries(request)
        trips = [resp.DetailedTrip] if detailed else resp.summedUpTrips
        if not trips:
            raise NoItineraryFoundException()
        if reversal_mis:
            # keep only the best result (we suppose MIS returns noisy results)
            self._filter_best_trip_response(trips, clockwise)

        # update time information in detailed trace
        if linked_stops:
            if clockwise:
                self._update_transition_arrivals(arrivals, linked_stops, transfer_durations, trips)
            else:
                self._update_transition_departures(departures, linked_stops, transfer_durations, trips)
        if len(departures) == 0 or len(arrivals) == 0:
            raise NoItineraryFoundException()

        # get optimal departure/arrival time
        target_time = None if linked_stops \
            else min([x.Arrival.DateTime for x in trips]) if clockwise \
            else max([x.Departure.DateTime for x in trips])

        # report intermediate results
        self._log_calculation_results(mis_api.get_name(), departures, arrivals, linked_stops,
                                      request.DepartureTime if clockwise else request.ArrivalTime, clockwise,
                                      target_time=target_time)

        if reversal_mis:
            # read reversal stop information
            mis_api, departures, arrivals, linked_stops, transfer_durations = mis_stops(idx, not clockwise)

            # update time information in detailed trace
            if clockwise:
                self._update_transition_departures(departures, linked_stops, transfer_durations, trips)
            else:
                self._update_transition_arrivals(arrivals, linked_stops, transfer_durations, trips)
            if len(departures) == 0 or len(arrivals) == 0:
                raise NoItineraryFoundException()

            # custom logging message at reversal step
            if log_info:
                logging.info(log_info)

            # report intermediate results
            self._log_calculation_results(mis_api.get_name(), departures, arrivals, linked_stops,
                                          target_time, not clockwise)

        if detailed:
            return mis_api, trips[0]
        elif reversal_mis:
            return mis_api, trips
        else:
            return None

    """
        Compute a trip according to the detailed_trace provided
    """

    def _departure_at_trip(self, detailed_trace, trace_id, providers):
        ret = []  # [(mis_api, DetailedTrip)]

        self.step = 1
        n = len(detailed_trace)

        logging.info("Processing first pass (left->right) that optimize arrival time...")
        for i in range(n - 1):
            self._process_calculation_step(detailed_trace, i, detailed=False, clockwise=True, origin_mis=(i == 0))
        _, trips = self._process_calculation_step(detailed_trace, n - 1, detailed=False, clockwise=True,
                                                  reversal_mis=True,
                                                  log_info="Processing second pass (right->left) that optimize "
                                                           "departure time")

        # tell the client that we have found the best arrival time
        best_arrival_time = min([x.Arrival.DateTime for x in trips])
        notif = PlanTripExistenceNotificationResponseType(
            RequestId=self._params.clientRequestId,
            ComposedTripId=trace_id,
            DepartureTime=self._params.DepartureTime,
            ArrivalTime=best_arrival_time,
            Duration=best_arrival_time - self._params.DepartureTime,
            providers=providers,
            Departure=self._params.Departure,
            Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        for i in range(n - 2, 0, -1):
            self._process_calculation_step(detailed_trace, i, detailed=False, clockwise=False)
        ret.append(self._process_calculation_step(detailed_trace, 0, detailed=True, clockwise=False,
                                                  reversal_mis=True,
                                                  log_info="Processing third pass (left->right) that give "
                                                           "detailed results"))
        for i in range(1, n):
            ret.append(self._process_calculation_step(detailed_trace, i, detailed=True, clockwise=True))

        return ret

    """
        Compute a trip according to the detailed_trace provided
    """

    def _arrival_at_trip(self, detailed_trace, trace_id, providers):
        ret = []  # [(mis_api, DetailedTrip)]

        self.step = 1
        n = len(detailed_trace)

        logging.info("Processing first pass (right->left) that optimize departure time...")
        for i in range(n - 1, 0, -1):
            self._process_calculation_step(detailed_trace, i, detailed=False, clockwise=False, origin_mis=(i == n - 1))
        _, trips = self._process_calculation_step(detailed_trace, 0, detailed=False, clockwise=False,
                                                  reversal_mis=True,
                                                  log_info="Processing second pass (left->right) that optimize "
                                                           "arrival time")

        # tell the client that we have found the best arrival time
        best_departure_time = min([x.Departure.DateTime for x in trips])
        notif = PlanTripExistenceNotificationResponseType(
            RequestId=self._params.clientRequestId,
            ComposedTripId=trace_id,
            DepartureTime=best_departure_time,
            ArrivalTime=self._params.ArrivalTime,
            Duration=self._params.ArrivalTime - best_departure_time,
            providers=providers,
            Departure=self._params.Departure,
            Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        for i in range(1, n - 1):
            self._process_calculation_step(detailed_trace, i, detailed=False, clockwise=True)
        ret.append(self._process_calculation_step(detailed_trace, n - 1, detailed=True, clockwise=True,
                                                  reversal_mis=True,
                                                  log_info="Processing third pass (right->left) that give "
                                                           "detailed results"))
        for i in range(n - 2, -1, -1):
            ret.append(self._process_calculation_step(detailed_trace, i, detailed=True, clockwise=False))

        ret.reverse()
        return ret

    @benchmark
    def compute_trip(self, mis_trace):
        start_date = datetime.now()
        if not mis_trace:
            raise Exception("Empty MIS trace")

        # Check that first and last MIS support departure/arrival points with
        # geographic coordinates.
        for mis_id in [mis_trace[0], mis_trace[-1]]:
            if not self._db_session.query(metabase.Mis.geographic_position_compliant) \
                    .filter_by(id=mis_id) \
                    .one()[0]:
                raise Exception("First or last MIS is not geographic_position_compliant")

        trace_id = self._generate_trace_id(mis_trace)
        providers = self._get_providers(mis_trace)

        # If there is only one MIS in the trace, just do a detailed request on the
        # given MIS.
        if len(mis_trace) == 1:
            ret = self._single_mis_trip(mis_trace[0], trace_id, providers)
        else:
            detailed_trace = self._detailed_trace(mis_trace)
            self._log_detailed_trace(detailed_trace)

            if self._params.DepartureTime:
                ret = self._departure_at_trip(detailed_trace, trace_id, providers)
            else:
                ret = self._arrival_at_trip(detailed_trace, trace_id, providers)

        notif = create_full_notification(self._params.clientRequestId, trace_id, ret, datetime.now() - start_date)
        self._notif_queue.put(notif)

        return ret
