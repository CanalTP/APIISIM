from mis_api import MisApi
from math import sqrt
from apiisim import metabase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import logging, sys, argparse, ConfigParser, datetime
from geoalchemy2.functions import ST_Distance, ST_DWithin
from geoalchemy2.functions import ST_Intersects, GenericFunction
from geoalchemy2 import Geography
import os
from copy import copy


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

    modified = False
    if db_stop.name != stop.name:
        db_stop.name = stop.name
        modified = True

    if db_stop.lat != stop.lat:
        db_stop.lat = stop.lat
        modified = True

    if db_stop.long != stop.long:
        db_stop.long = stop.long
        modified = True

    return modified


"""
Return True if mis1 and mis2 validity periods overlap, False otherwise.
"""
def mis_dates_overlap(db_session, mis1_id, mis2_id):
    mis1 = db_session.query(metabase.Mis).get(mis1_id)
    mis2 = db_session.query(metabase.Mis).get(mis2_id)
    # If one date is missing, return True
    if not (mis1.start_date and mis1.end_date and mis2.start_date and mis2.end_date):
        return True

    max_start = max(mis1.start_date, mis2.start_date)
    min_end = min(mis1.end_date, mis2.end_date)

    return bool((min_end - max_start) >= datetime.timedelta())


"""
Retrieve MIS capabilities and update database accordingly.
"""
@db_transaction
def retrieve_mis_capabilities(db_session):
    logging.info("Retrieving MIS capabilities...")
    for mis in db_session.query(metabase.Mis).all():
        try:
            logging.info("From <%s>...", mis.name)
            capabilities = MisApi(mis.api_url, mis.api_key).get_capabilties()
            mis.multiple_starts_and_arrivals = capabilities.multiple_starts_and_arrivals
            mis.geographic_position_compliant = capabilities.geographic_position_compliant
            logging.info("OK")
        except Exception as e:
            logging.error("get_capabilities request to <%s> failed: %s", mis.api_url, e)

class ST_GeogFromText(GenericFunction):
    name = 'ST_GeogFromText'
    type = Geography

"""
Retrieve all stops from Mis APIs and update database accordingly (add new stops
and remove obsolete ones).
"""
@db_transaction
def retrieve_all_stops(db_session, stats):
    # First, retrieve stops for all Mis existing in the DB
    logging.info("Retrieving stops...")
    all_stops = {} # {mis_id : [list of stops]}
    for mis in db_session.query(metabase.Mis).all():
        try:
            logging.info("From <%s>...", mis.name)
            all_stops[mis.id] = MisApi(mis.api_url, mis.api_key).get_stops()

            shape = MisApi(mis.api_url, mis.api_key).get_shape(mis.name)
            if shape:
                # Check if stops are included in MIS shape
                stops = copy(all_stops[mis.id])
                nb_ignored = 0
                for s in stops:
                    intersect = db_session.query(ST_Intersects(
                                        ST_GeogFromText('POINT(%s %s)' \
                                            % (s.long, s.lat)),
                                        ST_GeogFromText(shape))).one()[0]
                    if not intersect:
                        nb_ignored += 1
                        all_stops[mis.id].remove(s)
                logging.info("Ignored %s stops not in shape %s", nb_ignored, shape)

            logging.info("OK")
        except Exception as e:
            logging.error("get_stops request to <%s> failed: %s", mis.api_url, e)
            # TODO: do we delete all stops from this MIS?

    logging.debug("All stops: %s", all_stops)

    # Udpate database by adding new stops and removing old ones.
    # Do it Mis by Mis.
    # TODO what if all_stops is empty (delete all stops???)
    logging.info("Merging stops...")
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
            # Ignore stops with no coordinates
            if s.lat == 0 and s.long == 0:
                continue
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
                nb_updated_stops += 1

        nb_stops += len(stop_codes)
        nb_new_stops += len(new_stop_codes)
        nb_extra_stops += len(extra_stop_codes)

    logging.info("%s stops", nb_stops)
    logging.info("%s new stops", nb_new_stops)
    logging.info("%s deleted stops", nb_extra_stops)
    logging.info("%s updated stops", nb_updated_stops)

    stats.nb_stops = nb_stops
    stats.nb_new_stops = nb_new_stops
    stats.nb_deleted_stops = nb_extra_stops
    stats.nb_updated_stops = nb_updated_stops


"""
Calculate all transfers by parsing all stops and add them to the database.
Also remove obsolete transfers.
"""
@db_transaction
def compute_transfers(db_session, transfer_max_distance, orig_nb_transfers, stats):
    all_stops = db_session.query(metabase.Stop).all()
    transfers = [] # List of frozensets: [(stop1_id, stop2_id)]

    # For each stop, look for all stops that are within a specified distance
    # (and that are not in the same MIS).
    logging.info("Computing transfers...")
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

        # Final query: For each stop not in current stop MIS, get its "id"
        # if it is within a specified distance from the current stop.
        q = db_session.query(subq2.c.id) \
                      .filter(ST_DWithin(subq2.c.geog,subq.c.geog, transfer_max_distance)) \
                      .all()

        for s in q:
            transfers.append(frozenset([stop.id, s[0]]))

    # Remove duplicates
    transfers = set(transfers)

    # Add new transfers and update existing ones, if needed.
    logging.info("Adding/updating transfers...")
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
        elif transfer.modification_state != 'recalculate':
            # If transfer already exists and its modification_state is not 'recalculate',
            # don't touch it and go the next one.
            # If its modification_state is 'recalculate', just recalculate its distance,
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
        transfer.modification_state = "auto"
        transfer.active = True

        if _new_transfer:
            db_session.add(transfer)
            nb_new += 1
            logging.debug("New Transfer: %s", transfer)
        else:
            nb_updated += 1
            logging.debug("Transfer udpated: %s", transfer)

    # Remove obsolete transfers
    logging.info("Removing obsolete transfers...")
    db_transfers = db_session.query(metabase.Transfer.id,
                                    metabase.Transfer.stop1_id,
                                    metabase.Transfer.stop2_id) \
                             .all()
    for t in db_transfers:
        if set([t[1], t[2]]) not in transfers:
            db_session.query(metabase.Transfer).filter_by(id=t[0]).delete()

    nb_transfers = len(transfers)
    nb_deleted = orig_nb_transfers - nb_transfers
    if nb_deleted < 0:
        nb_deleted = 0
    logging.info("%s transfers", nb_transfers)
    logging.info("%s new transfers", nb_new)
    logging.info("%s updated transfers", nb_updated)
    logging.info("%s deleted transfers", nb_deleted)

    stats.nb_transfers = nb_transfers
    stats.nb_new_transfers = nb_new
    stats.nb_updated_transfers = nb_updated
    stats.nb_deleted_transfers = nb_deleted


"""
Calculate all mis_connections by parsing all transfers and add them to the
database (if they don't already exist).
Also remove obsolete mis_connections (i.e. mis_connections where the 2 MIS
don't have any transfer between them).
"""
@db_transaction
def compute_mis_connections(db_session, stats):
    mis_connections = []
    db_transfers = db_session.query(metabase.Transfer).all()
    nb_new = 0

    logging.info("Computing mis_connections...")
    # Add new mis_connections
    for t in db_transfers:
        m1 = t.stop1.mis_id
        m2 = t.stop2.mis_id
        # Ensure that mis1_id is always < mis2_id, this makes mis_connection
        # identification easier.
        mis1_id = min(m1, m2)
        mis2_id = max(m1, m2)

        # Ignore MIS which will never be active at the same time.
        if not mis_dates_overlap(db_session, mis1_id, mis2_id):
            continue

        mis_connections.append(frozenset([mis1_id, mis2_id]))
        if db_session.query(metabase.MisConnection) \
                     .filter_by(mis1_id=mis1_id, mis2_id=mis2_id) \
                     .first() is not None:
            continue

        nb_new += 1
        new_mis_connection = metabase.MisConnection()
        new_mis_connection.mis1_id = mis1_id
        new_mis_connection.mis2_id = mis2_id
        # start_date and end_date attributes are automatically set by SQL triggers
        # when a new mis_connection is inserted, so need to set them here.

        db_session.add(new_mis_connection)
        logging.info("New mis_connection: %s", new_mis_connection)

    # Remove obsolete mis_connections
    db_mis_connections = db_session.query(metabase.MisConnection.id,
                                          metabase.MisConnection.mis1_id,
                                          metabase.MisConnection.mis2_id) \
                                   .all()
    mis_connections = set(mis_connections) # Remove duplicates
    nb_deleted = 0
    for m in db_mis_connections:
        if set([m[1], m[2]]) not in mis_connections:
            db_session.query(metabase.MisConnection).filter_by(id=m[0]).delete()
            nb_deleted += 1

    nb_mis_connections = len(mis_connections)
    logging.info("%s mis_connections", nb_mis_connections)
    logging.info("%s new mis_connections", nb_new)
    logging.info("%s deleted mis_connections", nb_deleted)

    stats.nb_mis_connections = nb_mis_connections
    stats.nb_new_mis_connections = nb_new
    stats.nb_deleted_mis_connections = nb_deleted


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file")
    args = parser.parse_args()
    if args.config:
        config_file = args.config
    else:
        parser.error("No configuration file given")
    if not os.path.isabs(config_file):
        config_file = os.getcwd() + "/" + config_file
    if not os.path.isfile(config_file):
        logging.error("Configuration file <%s> does not exist", config_file)
        exit(1)

    logging.info("Configuration retrieved from '%s':", config_file)
    config = ConfigParser.RawConfigParser()
    config.read(config_file)

    return config

@db_transaction
def add_import_stats(db_session, stats):
    db_session.add(stats)


def main():
    init_logging()

    import_stats = metabase.BackOfficeImport()
    import_stats.start_date = datetime.datetime.now().isoformat()
    logging.info("Back Office start: %s", import_stats.start_date)

    config = get_config()
    db_url = config.get('General', 'db_url')
    transfer_max_distance = config.getint('General', 'transfer_max_distance')
    request_mis_capabilities = config.getboolean('General', 'request_mis_capabilities')
    logging.info("db_url: %s", db_url)
    logging.info("transfer_max_distance: %s", transfer_max_distance)

    # Create engine used to connect to database
    db_engine = create_engine(db_url, echo=False)
    db_session = Session(bind=db_engine, expire_on_commit=False)

    try:
        add_import_stats(db_session, import_stats)
        # orig_nb_transfers is used for stats only. We need it to have a
        # reliable number of deleted transfers. Indeed, some transfers are
        # automatically deleted by SQL triggers when one of their stops is deleted,
        # so the only way to know how many transfers were deleted is to compare
        # total number of transfers, before and after back_office processing.
        orig_nb_transfers = db_session.query(metabase.Transfer).count()
        if request_mis_capabilities:
            retrieve_mis_capabilities(db_session)
        retrieve_all_stops(db_session, import_stats)
        compute_transfers(db_session, transfer_max_distance, orig_nb_transfers, import_stats)
        compute_mis_connections(db_session, import_stats)
    except:
        db_session.rollback()
        import_stats.result = "fail"
        raise
    else:
        import_stats.result = "success"
    finally:
        import_stats.end_date = datetime.datetime.now().isoformat()
        db_session.commit()
        db_session.close()
        db_session.bind.dispose()

    logging.info("Back Office end: %s", import_stats.end_date)


if __name__ == '__main__':
    main()
