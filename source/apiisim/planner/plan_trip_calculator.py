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
import string
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
                             metabase.TransferMis.mis2_id == mis1_id))) \
            .filter(metabase.TransferMis.transfer_active == True) \
            .order_by(metabase.TransferMis.transfer_id) \
            .subquery()
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
    def _get_surrounding_mises(self, position, date):
        ret = set()  # ([mis_id])
        all_mises = self._db_session.query(metabase.Mis).all()

        for mis in all_mises:
            if self._db_session.query(metabase.Stop.id) \
                    .filter(metabase.Stop.mis_id == mis.id) \
                    .filter(
                    ST_DWithin(
                            metabase.Stop.geog,
                            StGeogFromText('POINT(%s %s)' % (position.Longitude, position.Latitude)),
                            self.SURROUNDING_MISES_MAX_DISTANCE)
            ).count() > 0 \
                    and (mis.start_date <= date <= mis.end_date):

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

        logging.info("MISes surrounding point (%s %s): %s",
                     position.Longitude, position.Latitude, ret)
        return ret

    def _get_mis_modes(self, mis_id):
        return set([x[0] for x in
                    self._db_session.query(metabase.Mode.code)
                        .filter(metabase.MisMode.mis_id == mis_id)
                        .filter(metabase.Mode.id == metabase.MisMode.mode_id)
                        .all()])

    @benchmark
    def _get_connected_mises(self, mis_id):
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
            logging.warning("Requesting Mis traces with max_trace_length < 1")
            return ret

        # Add all Mis in common
        for mis in (departure_mises & arrival_mises):
            ret.append([mis])
        if max_trace_length == 1:
            return ret

        for mis_id in departure_mises:
            connected_mises = self._get_connected_mises(mis_id)
            for subtrace in self._get_mis_traces(connected_mises,
                                                 arrival_mises, max_trace_length - 1):
                if not mis_id in subtrace:
                    subtrace.insert(0, mis_id)
                    ret.append(subtrace)

        return ret

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
        departure_mises = self._get_surrounding_mises(self._params.Departure.Position, date)
        # Filter out Mis that don't support at least one of the requested modes
        if self._params.modes and not TransportModeEnum.ALL in self._params.modes:
            departure_mises = set([x for x in departure_mises if (set(self._params.modes) & self._get_mis_modes(x))])
        logging.info("Departure MIS (mode compatibles): %s", departure_mises)

        logging.info("Finding arrival MIS...")
        arrival_mises = self._get_surrounding_mises(self._params.Arrival.Position, date)
        # Filter out Mis that don't support at least one of the requested modes
        if self._params.modes and not TransportModeEnum.ALL in self._params.modes:
            arrival_mises = set([x for x in arrival_mises if (set(self._params.modes) & self._get_mis_modes(x))])
        logging.info("Arrival MIS (mode compatibles): %s", arrival_mises)

        return self._filter_traces(
            self._get_mis_traces(departure_mises, arrival_mises, self.MAX_TRACE_LENGTH))

    def _list_of_location_context_to_str(self, list):
        def location_context_to_str(location):
            if not location.PlaceTypeId:
                return "%s;%s" % (location.Position.Longitude, location.Position.Latitude)
            else:
                return location.PlaceTypeId

        if not list:
            return "None"
        str = ""
        for item in list[0:3]:
            if str:
                str += " - "
            str += location_context_to_str(item)
        if len(list) > 3:
            str += " ... "
        return str

    def _log_detailed_trace(self, mis_trace):
        logging.info("Detailing trace...")
        count = 1
        for mis in mis_trace:
            logging.info("Region %d - MIS %s " % (count, mis[0]._name))
            logging.info(" + Org: %s " % self._list_of_location_context_to_str(mis[1]))
            logging.info(" + Dst: %s " % self._list_of_location_context_to_str(mis[2]))
            logging.info(" + Lnk: %s " % self._list_of_location_context_to_str(mis[3]))
            count += 1

    # (
    # MisApi,
    # [TraceStop], # departures
    # [TraceStop], # arrivals
    # [TraceStop], # linked_stops (stops linked to arrivals via a transfer)
    #     [timedelta]  # transfer_durations
    #   )

    @benchmark
    def _departure_at_detailed_trace(self, mis_trace):
        i = 0
        ret = []
        # [
        # (
        # MisApi,
        # [TraceStop], # departures
        # [TraceStop], # arrivals
        #     [TraceStop], # linked_stops (stops linked to arrivals via a transfer)
        #     [timedelta]  # transfer_durations
        #   )
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

    @benchmark
    def _arrival_at_detailed_trace(self, mis_trace):
        i = 0
        ret = []
        # [
        # (
        # MisApi,
        # [TraceStop], # departures
        # [TraceStop], # arrivals
        #     [TraceStop], # linked_stops (stops linked to departures via a transfer)
        #     [timedelta]  # transfer_durations
        #   )
        # ]

        if len(mis_trace) < 2:
            raise Exception("mis_trace length must be > 1")

        # Since we process an arrival_at request, we'll do the trip backwards,
        # starting from the arrival MIS, heading to the departure MIS.
        mis_trace = list(mis_trace)
        mis_trace.reverse()

        transfers = self._get_trace_transfers(mis_trace)
        while True:
            # Divide trace in chunks of 3 MIS
            chunk = mis_trace[i:i + 3]
            if not chunk:
                break
            logging.debug("CHUNK: %s", chunk)

            # Again, this is an arrival_at request, so we start from the arrival
            # point and finish in the departure point.
            trace_start = self._params.Arrival if i == 0 else None
            trace_end = self._params.Departure if len(mis_trace) <= (i + 3) else None
            mis1_id = chunk[0]
            mis2_id = chunk[1] if len(chunk) > 1 else 0
            mis3_id = chunk[2] if len(chunk) > 2 else 0
            mis1_api = MisApi(self._db_session, mis1_id) if mis1_id else None
            mis2_api = MisApi(self._db_session, mis2_id) if mis2_id else None
            mis3_api = MisApi(self._db_session, mis3_id) if mis3_id else None

            if trace_start:
                ret = [(mis1_api,
                        transfers[mis1_id][mis2_id][1],
                        [trace_start],
                        transfers[mis1_id][mis2_id][2],
                        transfers[mis1_id][mis2_id][0])]

            if mis3_id:
                ret.append(
                    (mis2_api,
                     transfers[mis2_id][mis3_id][1],
                     transfers[mis1_id][mis2_id][2],
                     transfers[mis2_id][mis3_id][2],
                     transfers[mis2_id][mis3_id][0]))

                if trace_end:
                    ret.append(
                        (mis3_api,
                         [trace_end],
                         transfers[mis2_id][mis3_id][2],
                         None,
                         None))
                    break
            else:
                if trace_end:
                    ret.append(
                        (mis2_api,
                         [trace_end],
                         transfers[mis1_id][mis2_id][2],
                         None,
                         None))
                    break
            i += 1

        return ret

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

    def _generate_trace_id(self, mis_trace):
        return "_".join(map(str, mis_trace))

    """
        Update transition stops after receiving itinerary results from a MIS.
            - Departure/Arrival time is updated according to trips data.
            - If no itinerary is found from/to a given departure/arrival stop, this stop (and
              its linked stops) are removed from the whole "meta-trip".
    """

    def _update_transtion_stops(self, transition_stops, linked_stops, stop_field, trips, trip_field):
        logging.debug("Updating transition stops...")
        logging.debug("Requested: %d %s", len(transition_stops), trip_field)
        for stop in transition_stops:
            logging.debug(". Req %s %s", trip_field, stop.PlaceTypeId)
        logging.debug("Returned by MIS: %d trips", len(trips))
        for trip in trips:
            logging.debug(". Ret %s %s", trip_field, getattr(trip, trip_field).TripStopPlace.id)

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
            logging.debug("No itinerary found using stop point %s, deleting it", deleted_stop)
            if linked_stops:
                deleted_stop = linked_stops.pop(i)
                logging.debug("Also deleting its linked stop point %s", deleted_stop)

        if not transition_stops:
            raise NoItineraryFoundException()

    """
        Update arrival stops after receiving itinerary results from a MIS.
            - Arrival time is updated according to trips data.
            - If no itinerary is found to a given arrival stop, this stop (and
              its linked stops) are removed from the whole "meta-trip".
    """

    def _update_arrivals(self, arrivals, linked_stops, trips):
        self._update_transtion_stops(arrivals, linked_stops, "arrival_time", trips, "Arrival")

    """
        Update departure stops after receiving itinerary results from a MIS.
            - Departure time is updated according to trips data.
            - If no itinerary is found from a given departure stop, this stop
              (and its linked stops) are removed from the whole "meta-trip".
    """

    def _update_departures(self, departures, linked_stops, trips):
        self._update_transtion_stops(departures, linked_stops, "departure_time", trips, "Departure")

    """
        Keep the best trip from SIM response
    """

    def _filter_best_trip_response(self, resp, clockwise):
        if len(resp.summedUpTrips) == 0:
            return
        if clockwise:
            best_time = min([x.Arrival.DateTime for x in resp.summedUpTrips])
            to_del = [i for i, x in enumerate(resp.summedUpTrips) if x.Arrival.DateTime != best_time]
        else:
            best_time = max([x.Departure.DateTime for x in resp.summedUpTrips])
            to_del = [i for i, x in enumerate(resp.summedUpTrips) if x.Departure.DateTime != best_time]

        to_del = set(to_del)
        for i in sorted(to_del, reverse=True):
            trip = resp.summedUpTrips[i]
            logging.debug("Remove bad trip from MIS response %s (%s) -> %s (%s)", trip.Departure.TripStopPlace.id,
                          trip.Departure.DateTime, trip.Arrival.TripStopPlace.id, trip.Arrival.DateTime)
            dummy = resp.summedUpTrips.pop(i)

    """
        Compute a trip according to the detailed_trace provided
    """

    def _departure_at_trip(self, detailed_trace, trace_id, providers):
        # Return best "meta-trip", which is a list of detailed trips.
        ret = []  # [(mis_api, DetailedTrip)]

        summed_up_request = SummedUpItinerariesRequestType()
        self._init_request(summed_up_request)
        detailed_request = ItineraryRequestType()
        self._init_request(detailed_request)

        step = 1

        logging.info("Processing first pass (left->right) that optimize arrival time...")

        # Do all non detailed requests
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace[0:-1]:
            summed_up_request.departures = departures
            summed_up_request.arrivals = arrivals
            if not summed_up_request.DepartureTime:
                summed_up_request.DepartureTime = self._params.DepartureTime
            else:
                summed_up_request.DepartureTime = min([x.arrival_time for x in departures])
                for d in departures:
                    d.AccessTime = d.arrival_time - summed_up_request.DepartureTime
            summed_up_request.ArrivalTime = None
            summed_up_request.options = []
            if self._cancelled:
                raise CancelledRequestException()
            resp = mis_api.get_summed_up_itineraries(summed_up_request)
            self._update_arrivals(arrivals, linked_stops, resp.summedUpTrips)
            if len(arrivals) == 0:
                raise NoItineraryFoundException()

            # To have linked_stops arrival_time, just add transfer time to request results
            for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                l.arrival_time = a.arrival_time + t

            # Report intermediate results
            rep_dep = sorted(departures, key=lambda s: s.arrival_time) if step > 1 else departures
            rep_arr, rep_lnk = tuple(zip(*sorted(zip(arrivals, linked_stops), key=lambda pair: pair[0].arrival_time)))
            logging.info("Step %d - %s : dep %s arr %s" % (step, mis_api._name, summed_up_request.DepartureTime, rep_arr[0].arrival_time))
            logging.info("Step %d - %s : Org %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_dep)))
            logging.info("Step %d - %s : Dst %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_arr)))
            logging.info("Step %d - %s : Lnk %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_lnk)))
            step += 1

        # Do non-detailed optimized request (only one, always)
        mis_api, departures, arrivals, _, _ = detailed_trace[-1]
        summed_up_request.departures = departures
        summed_up_request.arrivals = arrivals
        summed_up_request.DepartureTime = min([x.arrival_time for x in departures])
        for d in departures:
            d.AccessTime = d.arrival_time - summed_up_request.DepartureTime
        summed_up_request.ArrivalTime = None
        summed_up_request.options = [PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED]
        if self._cancelled:
            raise CancelledRequestException()
        resp = mis_api.get_summed_up_itineraries(summed_up_request)
        self._filter_best_trip_response(resp, True)
        self._update_departures(departures, detailed_trace[-2][2], resp.summedUpTrips)
        if len(departures) == 0:
            raise NoItineraryFoundException()

        best_arrival_time = min([x.Arrival.DateTime for x in resp.summedUpTrips])

        # Report intermediate results
        mis_api, departures, arrivals, linked_stops, _ = detailed_trace[-1]
        rep_dep = sorted(departures, key=lambda s: s.arrival_time)
        logging.info("Step %d - %s : dep %s arr %s" % (step, mis_api._name, summed_up_request.DepartureTime, best_arrival_time))
        logging.info("Step %d - %s : Org %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_dep)))
        logging.info("Step %d - %s : Dst %s" % (step, mis_api._name, self._list_of_location_context_to_str(arrivals)))
        logging.info("Step %d - %s : Lnk %s" % (step, mis_api._name, self._list_of_location_context_to_str(linked_stops)))
        step += 1

        # tell the client that we have found the best arrival time
        notif = PlanTripExistenceNotificationResponseType(
            RequestId=self._params.clientRequestId,
            ComposedTripId=trace_id,
            DepartureTime=self._params.DepartureTime,
            ArrivalTime=best_arrival_time,
            Duration=best_arrival_time - self._params.DepartureTime,
            providers=providers,
            Departure=self._params.Departure, Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        logging.info("Processing second pass (right->left) that optimize departure time")

        # Substract transfer time from previous request results
        mis_api, departures, arrivals, linked_stops, transfer_durations = detailed_trace[-2]
        for a, l, t in zip(arrivals, linked_stops, transfer_durations):
            a.departure_time = l.departure_time - t

        # Report intermediate results
        mis_api, _, arrivals, _, _= detailed_trace[-1]
        _, _, linked_stops, departures, _ = detailed_trace[-2]
        rep_dep, rep_lnk = tuple(zip(*sorted(zip(departures, linked_stops), key=lambda pair: pair[0].departure_time, reverse=1)))
        rep_arr = arrivals
        logging.info("Step %d - %s : dep %s arr %s" % (step, mis_api._name, rep_dep[0].departure_time, best_arrival_time))
        logging.info("Step %d - %s : Dst %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_arr)))
        logging.info("Step %d - %s : Org %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_dep)))
        logging.info("Step %d - %s : Lnk %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_lnk)))
        step += 1

        # Do arrival_at non-detailed requests
        if len(detailed_trace) > 2:
            for i in reversed(range(1, len(detailed_trace) - 1)):
                mis_api, departures, arrivals, linked_stops, transfer_durations = detailed_trace[i]
                summed_up_request.departures = departures
                summed_up_request.arrivals = arrivals
                summed_up_request.DepartureTime = None
                summed_up_request.ArrivalTime = min([x.departure_time for x in arrivals])
                for a in arrivals:
                    a.AccessTime = a.departure_time - summed_up_request.ArrivalTime
                summed_up_request.options = []
                if self._cancelled:
                    raise CancelledRequestException()
                resp = mis_api.get_summed_up_itineraries(summed_up_request)
                self._update_departures(departures, detailed_trace[i - 1][2], resp.summedUpTrips)

                # Substract transfer time from previous request results
                _, _, arrivals, linked_stops, transfer_durations = detailed_trace[i - 1]
                for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                    a.departure_time = l.departure_time - t

                # Report intermediate results
                # TO DO
                #logging.info("summary for step 3 at %s : departure %s arrival %s", mis_api,
                #             min([x.departure_time for x in departures]), summed_up_request.ArrivalTime)

        # Do all detailed requests.
        # Best arrival stop from previous request, will become the departure
        # point of the next request.
        prev_stop = None
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace:
            detailed_request.ArrivalTime = None
            if not prev_stop:
                # At first, do an arrival_at request.
                prev_stop = departures[0]
                detailed_request.DepartureTime = None
                detailed_request.ArrivalTime = min([x.departure_time for x in arrivals])
                for a in arrivals:
                    a.AccessTime = a.departure_time - detailed_request.ArrivalTime
            else:
                # All other requests are departure_at requests.
                detailed_request.DepartureTime = prev_stop.departure_time
                detailed_request.ArrivalTime = None
                prev_stop.AccessTime = timedelta(seconds=0)
            detailed_request.multiArrivals = multiArrivalsType()
            detailed_request.multiArrivals.Departure = prev_stop
            detailed_request.multiArrivals.Arrival = list(set(arrivals))
            if self._cancelled:
                raise CancelledRequestException()
            resp = mis_api.get_itinerary(detailed_request)
            if not resp.DetailedTrip:
                raise NoItineraryFoundException()
            ret.append((mis_api, resp.DetailedTrip))

            if not linked_stops:
                # We are at the end of the trace.
                break

            # Request result gives us the best arrival stop, the next step
            # is to find all stops that are linked to this stop via a transfer.
            best_stops = []
            for a, l, t in zip(arrivals, linked_stops, transfer_durations):
                if a.PlaceTypeId == resp.DetailedTrip.Arrival.TripStopPlace.id:
                    l.departure_time = resp.DetailedTrip.Arrival.DateTime + t
                    best_stops.append(l)
            # If we find several stops linked to the best arrival stop, choose
            # the one which has best departure_time.
            best_stops.sort(key=lambda x: x.departure_time)
            prev_stop = best_stops[0]

            # Report intermediate results
            if detailed_request.DepartureTime:
                rep_dep = [prev_stop]
                rep_arr, rep_lnk = tuple(zip(*sorted(zip(arrivals, linked_stops), key=lambda pair: pair[0].arrival_time)))
                logging.info("Step %d - %s : dep %s arr %s" % (step, mis_api._name, summed_up_request.DepartureTime, rep_arr[0].arrival_time))
                logging.info("Step %d - %s : Org %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_dep)))
                logging.info("Step %d - %s : Dst %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_arr)))
                logging.info("Step %d - %s : Lnk %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_lnk)))
                step += 1

                #logging.info("summary for step 4 at %s : departure %s arrival %s", mis_api,
                #             detailed_request.DepartureTime, min([x.arrival_time for x in arrivals]))
            else:
                mis_api, _, arrivals, _, _= detailed_trace[-1]
                _, _, linked_stops, departures, _ = detailed_trace[-2]
                rep_dep = [departures[0]]
                rep_arr = sorted(arrivals, key=lambda x: x.arrival_time, reverse=1)
                logging.info("Step %d - %s : dep %s arr %s" % (step, mis_api._name, rep_dep[0].departure_time, best_arrival_time))
                logging.info("Step %d - %s : Dst %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_arr)))
                logging.info("Step %d - %s : Org %s" % (step, mis_api._name, self._list_of_location_context_to_str(rep_dep)))
                step += 1

                logging.info("Processing third pass (left->right) that give detailed results")

                #logging.info("summary for step 4 at %s : departure None arrival %s", mis_api,
                #             min([x.arrival_time for x in arrivals]))

        return ret

    def _arrival_at_trip(self, detailed_trace, trace_id, providers):
        # Maximum departure_time drom departure
        best_departure_time = None

        # Return best "meta-trip", which is a list of detailed trips.
        ret = []  # [(mis_api, DetailedTrip)]

        summed_up_request = SummedUpItinerariesRequestType()
        self._init_request(summed_up_request)
        detailed_request = ItineraryRequestType()
        self._init_request(detailed_request)

        # Do all non detailed requests
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace[0:-1]:
            summed_up_request.departures = departures
            summed_up_request.arrivals = arrivals
            if not summed_up_request.ArrivalTime:
                summed_up_request.ArrivalTime = self._params.ArrivalTime
            else:
                summed_up_request.ArrivalTime = min([x.departure_time for x in arrivals])
                for a in arrivals:
                    a.AccessTime = a.departure_time - summed_up_request.ArrivalTime
            summed_up_request.DepartureTime = None
            summed_up_request.options = []
            if self._cancelled:
                raise CancelledRequestException()
            resp = mis_api.get_summed_up_itineraries(summed_up_request)
            self._update_departures(departures, linked_stops, resp.summedUpTrips)

            # To have linked_stops departure_time, just substract transfer time
            # from request results.
            for d, l, t in zip(departures, linked_stops, transfer_durations):
                l.departure_time = d.departure_time - t

        # Do non-detailed optimized request (only one, always)
        mis_api, departures, arrivals, _, _ = detailed_trace[-1]
        summed_up_request.departures = departures
        summed_up_request.arrivals = arrivals
        summed_up_request.ArrivalTime = min([x.departure_time for x in arrivals])
        for a in arrivals:
            a.AccessTime = a.departure_time - summed_up_request.ArrivalTime
        summed_up_request.DepartureTime = None
        summed_up_request.options = [PlanSearchOptions.DEPARTURE_ARRIVAL_OPTIMIZED]
        if self._cancelled:
            raise CancelledRequestException()
        resp = mis_api.get_summed_up_itineraries(summed_up_request)
        self._update_arrivals(arrivals, detailed_trace[-2][1], resp.summedUpTrips)
        best_departure_time = max([x.Departure.DateTime for x in resp.summedUpTrips])

        # Add transfer time from previous request results
        mis_api, departures, arrivals, linked_stops, transfer_durations = detailed_trace[-2]
        for d, l, t in zip(departures, linked_stops, transfer_durations):
            d.arrival_time = l.arrival_time + t
        notif = PlanTripExistenceNotificationResponseType(
            RequestId=self._params.clientRequestId,
            ComposedTripId=trace_id,
            DepartureTime=best_departure_time,
            ArrivalTime=self._params.ArrivalTime,
            Duration=self._params.ArrivalTime - best_departure_time,
            providers=providers,
            Departure=self._params.Departure, Arrival=self._params.Arrival)
        self._notif_queue.put(notif)

        # Do departure_at non-detailed requests
        if len(detailed_trace) > 2:
            for i in reversed(range(1, len(detailed_trace) - 1)):
                mis_api, departures, arrivals, _, _ = detailed_trace[i]
                summed_up_request.departures = departures
                summed_up_request.arrivals = arrivals
                summed_up_request.ArrivalTime = None
                summed_up_request.DepartureTime = min([x.arrival_time for x in departures])
                for d in departures:
                    d.AccessTime = d.arrival_time - summed_up_request.DepartureTime
                summed_up_request.options = []
                if self._cancelled:
                    raise CancelledRequestException()
                resp = mis_api.get_summed_up_itineraries(summed_up_request)
                self._update_arrivals(arrivals, detailed_trace[i - 1][1], resp.summedUpTrips)

                # Add transfer time from previous request results
                _, departures, _, linked_stops, transfer_durations = detailed_trace[i - 1]
                for d, l, t in zip(departures, linked_stops, transfer_durations):
                    d.arrival_time = l.arrival_time + t

        # Do all detailed requests.
        # Best departure stop from previous request, will become the arrival
        # point of the next request.
        prev_stop = None
        for mis_api, departures, arrivals, linked_stops, transfer_durations in detailed_trace:
            detailed_request.DepartureTime = None
            if not prev_stop:
                # At first, do a departure_at request.
                prev_stop = arrivals[0]
                detailed_request.ArrivalTime = None
                detailed_request.DepartureTime = min([x.arrival_time for x in departures])
                for d in departures:
                    d.AccessTime = d.arrival_time - detailed_request.DepartureTime
            else:
                # All other requests are arrival_at requests.
                detailed_request.ArrivalTime = prev_stop.arrival_time
                detailed_request.DepartureTime = None
                prev_stop.AccessTime = timedelta(seconds=0)
            detailed_request.multiDepartures = multiDeparturesType()
            detailed_request.multiDepartures.Departure = list(set(departures))
            detailed_request.multiDepartures.Arrival = prev_stop
            if self._cancelled:
                raise CancelledRequestException()
            resp = mis_api.get_itinerary(detailed_request)
            if not resp.DetailedTrip:
                raise NoItineraryFoundException()
            ret.append((mis_api, resp.DetailedTrip))

            if not linked_stops:
                # We are at the end of the trace.
                break

            # Request result gives us the best departure stop, the next step
            # is to find all stops that are linked to this stop via a transfer.
            best_stops = []
            for d, l, t in zip(departures, linked_stops, transfer_durations):
                if d.PlaceTypeId == resp.DetailedTrip.Departure.TripStopPlace.id:
                    l.arrival_time = resp.DetailedTrip.Departure.DateTime - t
                    best_stops.append(l)
            # If we find several stops linked to the best departure stop, choose
            # the one which has best arrival_time.
            best_stops.sort(key=lambda x: x.arrival_time)
            prev_stop = best_stops[0]

        ret.reverse()
        return ret

    def _init_request(self, request):
        request.id = self._params.clientRequestId
        request.Algorithm = self._params.Algorithm
        request.modes = self._params.modes
        request.selfDriveConditions = self._params.selfDriveConditions
        request.AccessibilityConstraint = self._params.AccessibilityConstraint
        request.Language = self._params.Language

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
            if self._params.DepartureTime:
                detailed_trace = self._departure_at_detailed_trace(mis_trace)
                self._log_detailed_trace(detailed_trace)
                ret = self._departure_at_trip(detailed_trace, trace_id, providers)
            else:
                detailed_trace = self._arrival_at_detailed_trace(mis_trace)
                self._log_detailed_trace(detailed_trace)
                ret = self._arrival_at_trip(detailed_trace, trace_id, providers)

        notif = create_full_notification(self._params.clientRequestId, trace_id, ret, datetime.now() - start_date)
        self._notif_queue.put(notif)

        return ret

    def stop(self):
        self._cancelled = True

    def __del__(self):
        logging.debug("Deleting PlanTripCalculator instance")
        if self._db_session:
            self._planner.remove_db_session(self._db_session)
