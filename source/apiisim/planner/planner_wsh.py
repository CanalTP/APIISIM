# -*- coding: utf8 -*-

import Queue, logging, os
import json, traceback
from datetime import datetime
import threading
from mod_python import apache
from apiisim.common.plan_trip import PlanTripRequestType, SelfDriveConditionType, \
                                     EndingSearch, PlanTripNotificationResponseType, \
                                     PlanTripExistenceNotificationResponseType, \
                                     PlanTripResponse, StartingSearch, ErrorType
from apiisim.common import AlgorithmEnum, SelfDriveModeEnum, TripPartEnum, string_to_bool, \
                           TransportModeEnum, PlanTripStatusEnum, parse_location_context
from apiisim.common.marshalling import DATE_FORMAT
from apiisim.planner import benchmark, PlanTripCancellationResponse, BadRequestException, \
                            Planner
from apiisim.planner.plan_trip_calculator import PlanTripCalculator
from logging.handlers import RotatingFileHandler


def init_logging(log_file):
    handler = RotatingFileHandler(log_file, maxBytes=8*1024*1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s <%(thread)d> [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

def log_error(func):
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logging.error("Class <%s>: %s\n%s", self.__class__.__name__,
                          e, traceback.format_exc())
            raise

    return decorator

class WorkerThread(threading.Thread):
    def __init__(self, params, job_queue, notif_queue):
        threading.Thread.__init__(self)
        self._params = params
        self._job_queue = job_queue
        self._notif_queue = notif_queue
        self.exit_code = 1

    @log_error
    def run(self):
        logging.debug("Worker Thread started")
        trace = self._job_queue.get()
        trip_calculator = PlanTripCalculator(planner, self._params, self._notif_queue)
        try:
            trip_calculator.compute_trip(trace)
            self.exit_code = 0
        except Exception as e:
            logging.error("compute_trip(%s): %s\n%s", trace, e, traceback.format_exc())
        logging.debug("Worker Thread finished")


"""
    Parse request dict and return a new PlanTripRequestType object with its
    attributes set accordingly.
"""
def parse_request(request):
    ret = PlanTripRequestType()

    # Required
    departure_time = request.get("DepartureTime", "")
    arrival_time = request.get("ArrivalTime", "")
    if departure_time and arrival_time:
        raise BadRequestException("Request cannot have both departure and arrival times")
    if not departure_time and not arrival_time:
        raise BadRequestException("No departure/arrival time given")
    try:
        if departure_time:
            ret.DepartureTime = datetime.strptime(departure_time, DATE_FORMAT)
        if arrival_time:
            ret.ArrivalTime = datetime.strptime(arrival_time, DATE_FORMAT)
    except ValueError as exc:
        bad_field = "DepartureTime" if departure_time else "ArrivalTime"
        raise BadRequestException("DateTime format error: %s" % exc, bad_field)

    if ('Departure' not in request) or ('Arrival' not in request):
        raise BadRequestException("Missing departure or arrival")
    try:
        ret.Departure = parse_location_context(request["Departure"], has_AccessTime=False)
    except Exception as exc:
        raise BadRequestException("Could not parse Departure: %s" % exc, "Departure")
    try:
        ret.Arrival = parse_location_context(request["Arrival"], has_AccessTime=False)
    except Exception as exc:
        raise BadRequestException("Could not parse Arrival: %s" % exc, "Arrival")

    # Optional
    ret.MaxTrips = request.get('MaxTrips', 0)
    ret.Algorithm = request.get('Algorithm', AlgorithmEnum.CLASSIC)
    if not AlgorithmEnum.validate(ret.Algorithm):
        raise BadRequestException("Invalid algorithm", "Algorithm")

    ret.modes = request.get('modes', [TransportModeEnum.ALL])
    for m in ret.modes:
        if not TransportModeEnum.validate(m):
            raise BadRequestException("Invalid transport mode: %s" % m, "modes")

    ret.selfDriveConditions = []
    for c in request.get('selfDriveConditions', []):
        condition = SelfDriveConditionType(TripPart=c.get("TripPart", ""),
                                SelfDriveMode=c.get("SelfDriveMode", ""))
        if not TripPartEnum.validate(condition.TripPart) or \
           not SelfDriveModeEnum.validate(condition.SelfDriveMode):
           raise BadRequestException("Invalid self drive condition", "selfDriveConditions")
        ret.selfDriveConditions.append(condition)

    ret.AccessibilityConstraint = string_to_bool(request.get('AccessibilityConstraint', "False"))
    ret.Language = request.get('Language', "")

    return ret


# Check if we've received a cancellation request
class CancellationListener(threading.Thread):
    def __init__(self, connection, params, queue):
        threading.Thread.__init__(self)
        self._connection = connection
        self._params = params
        self._queue = queue

    @log_error
    def run(self):
        logging.info("<CancellationListener> Thread started")
        while True:
            msg = self._connection.ws_stream.receive_message()
            logging.debug("<CancellationListener> Received message %s", msg)
            # if msg is None:
            #     # Connection has been closed
            #     break
            try:
                msg = json.loads(msg)
                if "PlanTripCancellationRequest" in msg \
                    and msg["PlanTripCancellationRequest"]["RequestId"] == self._params.clientRequestId:
                    self._queue.put("CANCEL")
                    break
            except:
                pass
        logging.info("<CancellationListener> Thread finished")


class CalculationManager(threading.Thread):
    def __init__(self, params, traces, notif_queue, termination_queue):
        threading.Thread.__init__(self)
        self._params = params
        self._traces = traces
        self._termination_queue = termination_queue
        self._notif_queue = notif_queue

    @log_error
    def run(self):
        logging.info("<CalculationManager> thread started")
        job_queue = Queue.Queue()
        i = 0
        workers = []
        for trace in self._traces:
            i += 1
            worker = WorkerThread(self._params, job_queue, self._notif_queue)
            workers.append(worker)
            job_queue.put(trace)
            worker.start()
            # Uncomment the line below to run workers sequentially.
            # This slows down performance but makes debugging much easier.
            # worker.join()
            if i == self._params.MaxTrips:
                break
        for w in workers:
            w.join()
        self._termination_queue.put("FINISHED")
        logging.info("<CalculationManager> thread finished")


class NotificationThread(threading.Thread):
    def __init__(self, connection, queue):
        threading.Thread.__init__(self)
        self._connection = connection
        self._queue = queue

    @log_error
    def run(self):
        start_date = datetime.now()
        existence_notifications_sent = 0
        notifications_sent = 0
        while True:
            logging.debug("Waiting for notification...")
            notif = self._queue.get()
            if notif is None:
                self._queue.task_done()
                logging.debug("Notification Thread finished")
                break
            if isinstance(notif, EndingSearch):
                notif.ExistenceNotificationsSent = existence_notifications_sent
                notif.NotificationsSent = notifications_sent
                notif.Runtime = datetime.now() - start_date
            elif isinstance(notif, PlanTripNotificationResponseType):
                notifications_sent += 1
            elif isinstance(notif, PlanTripExistenceNotificationResponseType):
                existence_notifications_sent += 1
            logging.debug("Sending notification <%s>...", notif.__class__.__name__)
            self._connection.ws_stream.send_message(json.dumps(notif.marshal()), binary=False)
            logging.debug("Notification sent")
            self._queue.task_done()

    def stop(self):
        self._queue.put(None)


class ConnectionHandler(object):
    def __init__(self, connection):
        self._connection = connection
        self._request_id = 0
        self._notif_queue = None
        self._notif_thread = None
        self._calculation_thread = None
        self._cancellation_thread = None

    def _send_status(self, status, error=None):
        logging.info("Sending <%s> status", status)
        notif = PlanTripResponse()
        notif.Status = status
        notif.clientRequestId = self._request_id
        if error:
            notif.errors = [error]
        self._notif_queue.put(notif)

    @log_error
    def process(self):
        termination_queue = Queue.Queue()
        notif_queue = Queue.Queue()
        self._notif_queue = notif_queue

        request = self._connection.ws_stream.receive_message()
        self._notif_thread = NotificationThread(self._connection, notif_queue)
        self._notif_thread.start()
        logging.debug("REQUEST: \n%s", request)
        # logging.debug(content)
        request = json.loads(request)
        try:
            request = request.get("PlanTripRequestType", None)
            if not request:
                raise BadRequestException("PlanTripRequestType field not found")
            self._request_id = request["clientRequestId"]
            params = parse_request(request)
            params.clientRequestId = self._request_id
        except Exception as exc:
            error = ErrorType(Message=exc.message)
            if isinstance(exc, BadRequestException):
                error.Field = exc.field
            self._send_status(PlanTripStatusEnum.BAD_REQUEST, error)
            raise

        try:
            trip_calculator = PlanTripCalculator(planner, params, notif_queue)
            traces = trip_calculator.compute_traces()
        except Exception as exc:
            logging.error("compute_traces: %s %s", exc, traceback.format_exc())
            error = ErrorType(Field="Error", Message=exc.message)
            self._send_status(PlanTripStatusEnum.SERVER_ERROR, error)
            return

        logging.info("MIS TRACES: %s", traces)
        self._send_status(PlanTripStatusEnum.OK)
        notif_queue.put(StartingSearch(MaxComposedTripSearched=len(traces), RequestId=self._request_id))
        self._cancellation_thread = CancellationListener(self._connection, params, termination_queue)
        # self._cancellation_thread.start()
        self._calculation_thread = CalculationManager(params, traces, notif_queue, termination_queue)
        self._calculation_thread.start()

        msg = termination_queue.get()
        if msg == "CANCEL":
            notif_queue.put(PlanTripCancellationResponse(RequestId=self._request_id))
            logging.debug("Request cancelled by client")
        else:
            notif_queue.put(EndingSearch(MaxComposedTripSearched=len(traces),
                                         RequestId=self._request_id,
                                         Status=PlanTripStatusEnum.OK))
            logging.info("Request finished")


    def __del__(self):
        logging.debug("Deleting ConnectionHandler instance")
        if self._notif_thread:
            self._notif_thread.stop()
            self._notif_thread.join()
        if self._calculation_thread:
            self._calculation_thread.join()


def web_socket_do_extra_handshake(connection):
    pass  # Always accept connection.


@benchmark
def web_socket_transfer_data(connection):
    connection_handler = ConnectionHandler(connection)
    connection_handler.process()
    del connection_handler


apache_options = apache.main_server.get_options()
init_logging(apache_options.get("PLANNER_LOG_FILE", "") or "/tmp/meta_planner.log")
planner = Planner(apache_options.get("PLANNER_DB_URL", "") or \
                  "postgresql+psycopg2://postgres:postgres@localhost/afimb_db")
