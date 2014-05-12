from mis_api import MisApi
from math import sqrt
import metabase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import logging, sys, argparse, ConfigParser
from geoalchemy2.functions import ST_Distance, ST_DWithin


def init_logging():
    # TODO add possibility to read logging config from a file/variable
    handler = logging.StreamHandler(stream=sys.stdout)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def db_transaction(func):
    def decorator(db_session, *args, **kwargs):
        # TODO maybe use scoped_session if we deal with threads
        try:
            result = func(db_session, *args, **kwargs)
            db_session.commit()
            return result
        except:
            db_session.rollback()
            logging.debug("ROLLBACK")
            raise
    return decorator


"""
Add given Stop object returned by a MisApi to database.
"""
def add_stop(db_session, mis_id, stop):
    new_stop = metabase.Stop()
    new_stop.mis_id = mis_id
    new_stop.code = stop.code
    new_stop.name = stop.name
    new_stop.lat = stop.lat
    new_stop.long = stop.long

    db_session.add(new_stop)


"""
Update stop in database with data contained in given Stop object.
Return True if stop in database has been modified (i.e. given Stop object
was different than stop in database), False otherwise.
"""
def update_stop(db_session, mis_id, stop):
    db_stop = db_session.query(metabase.Stop) \
              .filter_by(mis_id=mis_id, code=stop.code).one()

    _modified = False
    if db_stop.name != stop.name:
        db_stop.name = stop.name
        _modified = True

    if db_stop.lat != stop.lat:
        db_stop.lat = stop.lat
        _modified = True

    if db_stop.long != stop.long:
        db_stop.long = stop.long
        _modified = True

    return _modified


"""
Retrieve all stops from Mis APIs and update database accordingly (add new stops
and remove obsolete ones).
"""
@db_transaction
def retrieve_all_stops(db_session):
    # First, retrieve stops for all Mis existing in the DB
    all_stops = {} # {mis_id : [list of stops]}
    for mis in db_session.query(metabase.Mis).all():
        try:
            all_stops[mis.id] = MisApi(mis.api_url, mis.api_key).get_stops()
        except Exception as e:
            logging.error("get_stops request to <%s> failed: %s", mis.api_url, e)
            # TODO: do we delete all stops from this MIS?

    logging.debug("All stops: %s", all_stops)

    # Udpate database by adding new stops and removing old ones.
    # Do it Mis by Mis.
    # TODO what if all_stops is empty (delete all stops???)
    nb_stops = 0
    nb_new_stops = 0
    nb_extra_stops = 0
    nb_updated_stops = 0
    for mis_id in all_stops.keys():
        codes = db_session.query(metabase.Stop.code).filter_by(mis_id=mis_id).all()
        db_stop_codes = []
        for c in codes:
            # SQLAlchemy returns a list of tuples, even if we asked for only one column
            db_stop_codes.append(c[0])

        stop_codes = []
        for s in all_stops[mis_id]:
            stop_codes.append(s.code)

        db_stop_codes = set(db_stop_codes)
        stop_codes = set(stop_codes)
        new_stop_codes = stop_codes - db_stop_codes
        extra_stop_codes = db_stop_codes - stop_codes
        common_stop_codes = db_stop_codes & stop_codes
        logging.debug("New stop codes for MIS %s: %s" % (mis_id, new_stop_codes))
        logging.debug("Extra stop codes for MIS %s: %s" % (mis_id, extra_stop_codes))
        logging.debug("Common stop codes for MIS %s: %s" % (mis_id, common_stop_codes))

        for code in extra_stop_codes:
            db_session.query(metabase.Stop).filter_by(mis_id=mis_id, code=code).delete()
        for stop in [s for s in all_stops[mis_id] if s.code in new_stop_codes]:
            add_stop(db_session, mis_id, stop)
        for stop in [s for s in all_stops[mis_id] if s.code in common_stop_codes]:
            if update_stop(db_session, mis_id, stop):
                nb_updated_stops = nb_updated_stops + 1

        nb_stops = nb_stops + len(stop_codes)
        nb_new_stops = nb_new_stops + len(new_stop_codes)
        nb_extra_stops = nb_extra_stops + len(extra_stop_codes)

    logging.info("%s stops", nb_stops)
    logging.info("%s new stops", nb_new_stops)
    logging.info("%s deleted stops", nb_extra_stops)
    logging.info("%s updated stops", nb_updated_stops)


"""
Calculate all transfers by parsing all stops and add them to the database.
"""
@db_transaction
def compute_transfers(db_session, transfer_max_distance):
    all_stops = db_session.query(metabase.Stop).all()
    transfers = [] # List of frozensets: [(stop1_id, stop2_id)]

    # For each stop, look for all stops that are within a specified distance
    # (and that are not in the same MIS).
    for stop in all_stops:
        # We're using two subqueries to filter out some rows and columns that
        # we don't need, and then we do a query using these two subqueries to do
        # the actual distance calculation.

        # First subquery: select current stop "geog" attribute. We'll be looking
        # at all stops that are within a specified from this position.
        subq = db_session.query(metabase.Stop.geog) \
                         .filter(metabase.Stop.id == stop.id) \
                         .subquery()

        # Second subquery: select "geog" attribute from all stops that are not in
        # the same MIS as the current stop.
        subq2 = db_session.query(metabase.Stop.id, metabase.Stop.geog) \
                          .filter(metabase.Stop.mis_id != stop.mis_id) \
                          .subquery()

        # q = db_session.query(subq2.c.id, ST_Distance(subq2.c.geog,subq.c.geog)).all()
        # logging.debug(len(q))
        # for s in q:
        #     logging.info("Distance from %s to %s: %sm",stop.id, s[0], s[1])

        # Final query: For each stop not in current stop MIS, get its "id"
        # if it is within a specified distance from the current stop.
        q = db_session.query(subq2.c.id) \
                      .filter(ST_DWithin(subq2.c.geog,subq.c.geog, transfer_max_distance)) \
                      .all()

        for s in q:
            # logging.debug("%s close to %s", stop.id, s[0])
            transfers.append(frozenset([stop.id, s[0]]))

    # Remove duplicates
    transfers = set(transfers)
    # logging.debug("Transfers: %s", transfers)

    # Add new transfers and update existing ones, if needed.
    nb_new = 0
    nb_updated = 0
    for t in transfers:
        # Ensure that stop1_id is always < stop2_id, this makes transfer
        # identification easier.
        s1, s2 = t
        stop1_id = min(s1, s2)
        stop2_id = max(s1, s2)

        _new_transfer = False
        transfer = db_session.query(metabase.Transfer) \
                             .filter_by(stop1_id=stop1_id, stop2_id=stop2_id) \
                             .first()
        if transfer is None:
            _new_transfer = True
            transfer = metabase.Transfer()
            transfer.stop1_id = stop1_id
            transfer.stop2_id = stop2_id
        elif transfer.status != 'recalculate':
            # If transfer already exists and its status is not 'recalculate',
            # don't touch it and go the next one.
            # If its status is 'recalculate', just recalculate its distance,
            # duration, and prm_duration attributes.
            continue

        subq = db_session.query(metabase.Stop.geog) \
                         .filter(metabase.Stop.id == stop1_id) \
                         .subquery()
        subq2 = db_session.query(metabase.Stop.geog) \
                         .filter(metabase.Stop.id == stop2_id) \
                         .subquery()
        d = db_session.query(ST_Distance(subq2.c.geog,subq.c.geog)).first()[0]

        transfer.distance = int(d)
        # We assume that we walk at 4 Km/h (~1m/s), also multiply by sqrt(2)
        # as path is never straight from point to point.
        transfer.duration = int((d/60) * sqrt(2))
        transfer.prm_duration = transfer.duration * 2
        transfer.status = "auto"

        if _new_transfer:
            db_session.add(transfer)
            nb_new = nb_new + 1
            logging.debug("New Transfer: %s", transfer)
        else:
            nb_updated = nb_updated + 1
            logging.debug("Transfer udpated: %s", transfer)


    # Remove obsolete transfers
    db_transfers = db_session.query(metabase.Transfer.id,
                                    metabase.Transfer.stop1_id,
                                    metabase.Transfer.stop2_id) \
                             .all()
    nb_deleted = 0
    for t in db_transfers:
        if set([t[1], t[2]]) not in transfers:
            db_session.query(metabase.Transfer).filter_by(id=t[0]).delete()
            nb_deleted = nb_deleted + 1

    logging.info("%s transfers", len(transfers))
    logging.info("%s new transfers", nb_new)
    logging.info("%s updated transfers", nb_updated)
    logging.info("%s deleted transfers", nb_deleted)


"""
Calculate all mis_connections by parsing all transfers and add them to the
database (if they don't already exist).
"""
@db_transaction
def compute_mis_connections(db_session):

    transfers = db_session.query(metabase.Transfer).all()
    for t in transfers:
        m1 = t.stop1.mis_id
        m2 = t.stop2.mis_id
        # Ensure that mis1_id is always < mis2_id, this makes mis_connection
        # identification easier.
        mis1_id = min(m1, m2)
        mis2_id = max(m1, m2)
        if db_session.query(metabase.MisConnection) \
                     .filter_by(mis1_id=mis1_id, mis2_id=mis2_id) \
                     .first() is not None:
            continue

        new_mis_connection = metabase.MisConnection()
        new_mis_connection.mis1_id = mis1_id
        new_mis_connection.mis2_id = mis2_id
        # start_date and end_date attributes are automatically set by SQL triggers
        # when a new mis_connection is inserted, so need to set them here.

        db_session.add(new_mis_connection)
        logging.info("New mis_connection: %s", new_mis_connection)


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file", help="Configuration file")
    config_file = "default.conf"
    args = parser.parse_args()
    if args.config_file:
        config_file = args.config_file

    logging.info("Configuration retrieved from '%s':", config_file)
    config = ConfigParser.RawConfigParser()
    config.read(config_file)

    return config


def main():
    init_logging()

    config = get_config()
    db_url = config.get('General', 'db_url')
    transfer_max_distance = config.getint('General', 'transfer_max_distance')
    logging.info("db_url: %s", db_url)
    logging.info("transfer_max_distance: %s", transfer_max_distance)

    # Create engine used to connect to database
    db_engine = create_engine(db_url, echo=False)
    db_session = Session(bind=db_engine, expire_on_commit=False)

    retrieve_all_stops(db_session)
    compute_transfers(db_session, transfer_max_distance)
    compute_mis_connections(db_session)


if __name__ == '__main__':
    main()

