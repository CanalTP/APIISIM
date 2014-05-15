"""
Test suite for metabase and back_office components
"""
import os, tests, unittest, logging, datetime
from random import randint
import metabase
from geoalchemy2.functions import ST_AsText
from sqlalchemy.exc import IntegrityError
from back_office import compute_transfers, compute_mis_connections
from sqlalchemy import or_

TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"

def new_stop(code ="stop_code", name="stop_name", mis_id=1):
    stop = metabase.Stop()
    stop.code   = code
    stop.mis_id = mis_id
    stop.name   = name
    stop.long   = 142.396624
    stop.lat    = 66.361493

    return stop

class TestSuite(unittest.TestCase):

    def setUp(self):
        tests.create_db()
        self.db_session = tests.connect_db()

    def add_mis(self, name="mis", url="mis_url"):
        mis = metabase.Mis()
        mis.name = name
        mis.api_url = url
        self.db_session.add(mis)
        self.db_session.flush()

        return mis.id

    def add_stop(self, code ="stop_code", name="stop_name", mis_id=1):
        stop = new_stop(code, name, mis_id)
        self.db_session.add(stop)
        self.db_session.flush()

        return stop.id

    def add_transfer(self, stop1_id, stop2_id):
        transfer = metabase.Transfer()
        transfer.stop1_id = stop1_id
        transfer.stop2_id = stop2_id
        transfer.distance = 100
        transfer.duration = 10
        transfer.status = 'auto'
        self.db_session.add(transfer)
        self.db_session.flush()

        return transfer.id

    def add_mis_connection(self, mis1_id, mis2_id):
        mis_connection = metabase.MisConnection()
        mis_connection.mis1_id = mis1_id
        mis_connection.mis2_id = mis2_id
        self.db_session.add(mis_connection)
        self.db_session.flush()

        return mis_connection.id


    """
    Check that geog attribute is correctly set when a stop is inserted and
    when long/lat attributes are modified.
    """
    def test_geography_trigger(self):
        self.db_session.query()

        mis_id = self.add_mis()

        stop = new_stop()
        stop.mis_id = mis_id
        self.db_session.add(stop)
        self.db_session.flush()

        point = self.db_session.query(ST_AsText(metabase.Stop.geog)).filter_by(id=stop.id).one()[0]
        self.assertEqual(point, u"POINT(%s %s)" % (stop.long, stop.lat),
                         "geog attribute not coherent with long/lat attributes")
        logging.debug("POINT %s", point)

        stop = self.db_session.query(metabase.Stop).filter_by(id=stop.id).one()
        stop.long = 92.321269
        self.db_session.flush()
        point = self.db_session.query(ST_AsText(metabase.Stop.geog)).filter_by(id=stop.id).one()[0]
        self.assertEqual(point, u"POINT(%s %s)" % (stop.long, stop.lat),
                         "geog attribute not coherent with long/lat attributes")
        logging.debug("POINT %s", point)

        stop = self.db_session.query(metabase.Stop).filter_by(id=stop.id).one()
        stop.lat = 37.123123
        self.db_session.flush()
        point = self.db_session.query(ST_AsText(metabase.Stop.geog)).filter_by(id=stop.id).one()[0]
        self.assertEqual(point, u"POINT(%s %s)" % (stop.long, stop.lat),
                         "geog attribute not coherent with long/lat attributes")
        logging.debug("POINT %s", point)


    """
    Check that we cannot create a Stop with no associated MIS.
    """
    def test_stop_with_no_mis(self):
        stop = new_stop()
        stop.mis_id = 37
        self.db_session.add(stop)
        self.assertRaises(IntegrityError, self.db_session.flush)


    """
    Check that we cannot have 2 stops with the same code and the same MIS.
    """
    def test_duplicate_stop_code(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")

        stop1 = new_stop("code", "stop1")
        stop1.mis1_id = mis1_id

        stop2 = new_stop("code", "stop2")
        stop2.mis_id = mis2_id

        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()

        stop2.mis_id = mis1_id
        self.assertRaises(IntegrityError, self.db_session.flush)


    """
    Check that transfer status is set to moved when one of its stop is moved.
    """
    def test_moved_status(self):
        mis_id = self.add_mis("mis1")

        stop1 = new_stop("code1", "stop1")
        stop1.mis1_id = mis_id
        stop2 = new_stop("code2", "stop2")
        stop2.mis_id = mis_id
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()
        transfer_id = self.add_transfer(stop1.id, stop2.id)

        stop1.lat = stop1.lat - 3
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.Transfer.status) \
                                        .filter_by(id=transfer_id).one()[0],
                        'moved', "Transfer status should be 'moved'")

        transfer = self.db_session.query(metabase.Transfer).filter_by(id=transfer_id).one()
        transfer.status = 'auto'
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.Transfer.status) \
                                        .filter_by(id=transfer_id).one()[0],
                        'auto', "Transfer status should be 'auto'")

        stop2.long = stop2.long + 11.23344
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.Transfer.status) \
                                        .filter_by(id=transfer_id).one()[0],
                        'moved', "Transfer status should be 'moved'")


    """
    Check that mis_connection dates are valid when inserting a new mis_connection
    and check that its dates are updated when dates of one its MIS are modified.
    """
    def test_mis_connection_dates(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")
        mis1 = self.db_session.query(metabase.Mis).filter_by(id=mis1_id).one()
        mis2 = self.db_session.query(metabase.Mis).filter_by(id=mis2_id).one()

        mis1.start_date = datetime.datetime.utcnow()
        mis1.end_date = mis1.start_date + datetime.timedelta(days=1000)
        mis2.start_date = mis1.start_date - datetime.timedelta(days=200)
        mis2.end_date = mis1.start_date + datetime.timedelta(days=600)
        self.db_session.flush()

        mis_connection_id = self.add_mis_connection(mis1_id, mis2_id)
        self.assertEqual(self.db_session.query(metabase.MisConnection.start_date) \
                                        .filter_by(id=mis_connection_id).one()[0],
                        mis1.start_date, "mis_connection start_date not OK")
        self.assertEqual(self.db_session.query(metabase.MisConnection.end_date) \
                                        .filter_by(id=mis_connection_id).one()[0],
                        mis2.end_date, "mis_connection end_date not OK")

        mis1.end_date = mis1.start_date + datetime.timedelta(days=400)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.MisConnection.end_date) \
                                        .filter_by(id=mis_connection_id).one()[0],
                         mis1.end_date, "mis_connection end_date not OK")

        mis2.start_date = mis2.start_date + datetime.timedelta(days=400)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.MisConnection.start_date) \
                                        .filter_by(id=mis_connection_id).one()[0],
                         mis2.start_date, "mis_connection start_date not OK")


    """
    Test transfer calculation feature by adding/deleting stops and changing
    maximum transfer distance. Each time we make a change, we launch a transfer
    calculation and check that results are as expected.
    """
    def test_compute_transfers(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")

        stop1 = new_stop("code1", "Gare de Lyon", mis1_id)
        stop1.lat = 48.84556
        stop1.long = 2.373449
        stop2 = new_stop("code2", "Gare d'Austerlitz", mis2_id)
        stop2.lat = 48.843414
        stop2.long = 2.364188
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()

        compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                        .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")

        compute_transfers(self.db_session, 100)
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        stop3 = new_stop("code3", "Los Angeles Airport", mis2_id)
        stop3.lat = 33.9434
        stop3.long = -118.4079
        self.db_session.add(stop3)
        self.db_session.flush()

        compute_transfers(self.db_session, 90000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                        .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer) \
                                        .filter(or_(metabase.Transfer.stop1_id == stop3.id,
                                                    metabase.Transfer.stop2_id == stop3.id)) \
                                        .count(),
                                        0, "This transfer should not exist")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")

        compute_transfers(self.db_session, 900000000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                .filter_by(stop1_id=stop1.id, stop2_id=stop3.id).one()[0],
                         9127641, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         2, "Found more transfers than expected")

        compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                        .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")


        mis3_id = self.add_mis("mis3")
        stop4 = new_stop("code4", "Gare de Lyon 2", mis3_id)
        stop4.lat = 48.84556
        stop4.long = 2.373449
        self.db_session.add(stop4)
        self.db_session.flush()

        compute_transfers(self.db_session, 1000)
        for stop1_id, stop2_id, distance in [(stop1.id, stop2.id, 720),
                                             (stop1.id, stop4.id, 0),
                                             (stop2.id, stop4.id, 720)]:
            self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                            .filter_by(stop1_id=stop1_id, stop2_id=stop2_id) \
                                            .one()[0],
                             distance, "Transfer distance different than expected")
            self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                             3, "Found more transfers than expected")

        self.db_session.delete(stop2)
        self.db_session.delete(stop4)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        compute_transfers(self.db_session, 900000000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance) \
                                .filter_by(stop1_id=stop1.id, stop2_id=stop3.id).one()[0],
                         9127641, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")


    """
    Test mis_connection calculation by creating/removing transfers and checking
    that we get expected mis_connections.
    """
    def test_compute_mis_connection(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")
        mis3_id = self.add_mis("mis3")
        mis4_id = self.add_mis("mis4")

        stop1_id = self.add_stop(code="code1", mis_id=mis1_id)
        stop2_id = self.add_stop(code="code2", mis_id=mis1_id)
        stop3_id = self.add_stop(mis_id=mis2_id)
        stop4_id = self.add_stop(mis_id=mis3_id)
        stop5_id = self.add_stop(code="code1", mis_id=mis4_id)
        stop6_id = self.add_stop(code="code2", mis_id=mis4_id)
        stop7_id = self.add_stop(code="code3", mis_id=mis4_id)

        transfers = [(stop1_id, stop3_id), (stop1_id, stop4_id),
                     (stop1_id, stop5_id), (stop2_id, stop6_id),
                     (stop2_id, stop5_id), (stop3_id, stop4_id),
                     (stop3_id, stop7_id)]

        mis_connections = []
        for t in transfers:
            mis_connections.append(tuple([self.db_session.query(metabase.Stop.mis_id).filter_by(id=t[0]).one()[0],
                                          self.db_session.query(metabase.Stop.mis_id).filter_by(id=t[1]).one()[0]]))
        mis_connections = set(mis_connections) # Remove duplicates

        for s1, s2 in transfers:
            self.add_transfer(s1, s2)

        compute_mis_connections(self.db_session)
        db_mis_connections = self.db_session.query(metabase.MisConnection.mis1_id,
                                                   metabase.MisConnection.mis2_id) \
                                            .all()

        # Check that there are no duplicates in the mis_connection table.
        self.assertEqual(len(db_mis_connections), len(set(db_mis_connections)),
                         "Found duplicates in the mis_connection table")
        self.assertEqual(set(db_mis_connections), mis_connections,
                         "MisConnection calculation results not as expected")

        self.db_session.query(metabase.Transfer).filter_by(stop1_id=stop2_id, stop2_id=stop5_id).delete()
        self.db_session.query(metabase.Transfer).filter_by(stop1_id=stop2_id, stop2_id=stop6_id).delete()
        self.db_session.flush()
        compute_mis_connections(self.db_session)
        # mis_connection should still be here
        self.assertEqual(self.db_session.query(metabase.MisConnection) \
                                        .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         1, "MisConnection not found")

        self.db_session.query(metabase.Transfer).filter_by(stop1_id=stop1_id, stop2_id=stop5_id).delete()
        self.db_session.flush()
        compute_mis_connections(self.db_session)
        # mis_connection should not exist as all transfers between mis1 and mis4 have been deleted
        self.assertEqual(self.db_session.query(metabase.MisConnection) \
                                        .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         0, "MisConnection should have been deleted")

        self.add_transfer(stop1_id, stop6_id)
        self.db_session.flush()
        compute_mis_connections(self.db_session)
        # mis_connection should come back now that a transfer has been added
        self.assertEqual(self.db_session.query(metabase.MisConnection) \
                                        .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         1, "MisConnection not found")


    """
    Check that if a transfer status is 'recalculate', the back_office effectively
    recalculate distance and durations for this transfer.
    """
    def test_recalculate_status(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")
        stop1 = new_stop("code1", "Gare de Lyon", mis1_id)
        stop1.lat = 48.84556
        stop1.long = 2.373449
        stop2 = new_stop("code2", "Gare d'Austerlitz", mis2_id)
        stop2.lat = 48.843414
        stop2.long = 2.364188
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()
        compute_transfers(self.db_session, 900)

        transfer = self.db_session.query(metabase.Transfer) \
                       .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        original_values = [transfer.distance, transfer.duration, transfer.prm_duration]
        transfer.distance = randint(10, 10000)
        transfer.duration = randint(10, 10000)
        transfer.prm_duration = randint(10, 10000)
        transfer.status = "recalculate"
        self.db_session.flush()

        compute_transfers(self.db_session, 900)
        transfer = self.db_session.query(metabase.Transfer) \
                       .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        self.assertEqual(transfer.status, 'auto', "Transfer status should be 'auto'")
        self.assertEqual(original_values,
                         [transfer.distance, transfer.duration, transfer.prm_duration],
                         "Distance and durations have not been recalculated properly ")


    """
    Check that back_office doesn't modify transfer when its status is
    'moved', 'blocked' or 'manual'.
    """
    def test_manual_blocked_moved_status(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")
        stop1 = new_stop("code1", "Gare de Lyon", mis1_id)
        stop1.lat = 48.84556
        stop1.long = 2.373449
        stop2 = new_stop("code2", "Gare d'Austerlitz", mis2_id)
        stop2.lat = 48.843414
        stop2.long = 2.364188
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()
        compute_transfers(self.db_session, 900)

        transfer = self.db_session.query(metabase.Transfer) \
                       .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        transfer.distance = randint(10, 10000)
        transfer.duration = randint(10, 10000)
        transfer.prm_duration = randint(10, 10000)
        manual_values = [transfer.distance, transfer.duration, transfer.prm_duration]

        for status in ['manual', 'blocked', 'moved']:
            transfer.status = status
            self.db_session.flush()
            compute_transfers(self.db_session, 900)
            transfer = self.db_session.query(metabase.Transfer) \
                           .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
            self.assertEqual(transfer.status, status, "Transfer status should be '%s'" % status)
            self.assertEqual(manual_values,
                             [transfer.distance, transfer.duration, transfer.prm_duration],
                             "Distance and durations should not have been modified")


    def tearDown(self):
        tests.disconnect_db(self.db_session)
        tests.drop_db()


if __name__ == '__main__':
    unittest.main()
