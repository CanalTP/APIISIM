#!/usr/bin/python
# -*- encoding: utf8 -*-
import os
import unittest
import logging
import datetime
from random import randint
from datetime import timedelta, date as date_type

from geoalchemy2.functions import ST_AsText
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from apiisim import tests
from apiisim import metabase
from apiisim.back_office.run import compute_transfers, compute_mis_connections, \
    mis_dates_overlap


TEST_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "")


def new_stop(code="stop_code", name="stop_name", mis_id=1):
    stop = metabase.Stop()
    stop.code = code
    stop.mis_id = mis_id
    stop.name = name
    stop.long = 142.396624
    stop.lat = 66.361493
    return stop


def _compute_transfers(db_session, transfer_max_distance):
    return compute_transfers(db_session, transfer_max_distance,
                             db_session.query(metabase.Transfer).count(),
                             metabase.BackOfficeImport())


def _compute_mis_connections(db_session):
    return compute_mis_connections(db_session, metabase.BackOfficeImport())


"""
Test suite for metabase and back_office components
"""


class TestBackOffice(unittest.TestCase):
    def setUp(self):
        try:
            tests.drop_db()
        except:
            pass
        tests.create_db()
        self.db_session = tests.connect_db()

    def tearDown(self):
        tests.disconnect_db(self.db_session)
        tests.drop_db()

    def add_mis(self, name="mis", url="mis_url"):
        mis = metabase.Mis()
        mis.name = name
        mis.api_url = url
        self.db_session.add(mis)
        self.db_session.flush()
        return mis.id

    def add_stop(self, code="stop_code", name="stop_name", mis_id=1):
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
        transfer.active = True
        transfer.modification_state = 'auto'
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
    Check that transfer state is updated accordingly when one of its stop is moved.
    """

    def test_moved_stop(self):
        mis_id = self.add_mis("mis1")

        stop1 = new_stop("code1", "stop1")
        stop1.mis1_id = mis_id
        stop2 = new_stop("code2", "stop2")
        stop2.mis_id = mis_id
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()
        transfer_id = self.add_transfer(stop1.id, stop2.id)

        stop1.lat -= 3
        self.db_session.commit()
        self.db_session.expire_all()
        transfer = self.db_session.query(metabase.Transfer).filter_by(id=transfer_id).one()
        self.assertEqual(transfer.modification_state,
                         'recalculate', "Transfer modification_state should be 'recalculate'")
        self.assertEqual(transfer.active,
                         False, "Transfer should not be active")

        transfer = self.db_session.query(metabase.Transfer).filter_by(id=transfer_id).one()
        transfer.modification_state = 'auto'
        transfer.active = True
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(transfer.modification_state,
                         'auto', "Transfer modification_state should be 'auto'")
        self.assertEqual(transfer.active,
                         True, "Transfer should be active")

        stop2.long += 11.23344
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(transfer.modification_state,
                         'recalculate', "Transfer modification_state should be 'recalculate'")
        self.assertEqual(transfer.active,
                         False, "Transfer should not be active")

        transfer.modification_state = 'manual'
        transfer.active = True
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(transfer.modification_state,
                         'manual', "Transfer modification_state should be 'manual'")
        self.assertEqual(transfer.active,
                         True, "Transfer should be active")

        transfer.modification_state = 'validation_needed'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(transfer.modification_state,
                         'validation_needed', "Transfer modification_state should be 'validation_needed'")
        self.assertEqual(transfer.active,
                         False, "Transfer should not be active")

    """
    Check that mis_connection dates are valid when inserting a new mis_connection
    and check that its dates are updated when dates of one its MIS are modified.
    """

    def test_mis_connection_dates(self):
        mis1_id = self.add_mis("mis1")
        mis2_id = self.add_mis("mis2")
        mis1 = self.db_session.query(metabase.Mis).filter_by(id=mis1_id).one()
        mis2 = self.db_session.query(metabase.Mis).filter_by(id=mis2_id).one()

        mis1.start_date = datetime.date.today()
        mis1.end_date = mis1.start_date + datetime.timedelta(days=1000)
        mis2.start_date = mis1.start_date - datetime.timedelta(days=200)
        mis2.end_date = mis1.start_date + datetime.timedelta(days=600)
        self.db_session.flush()

        mis_connection_id = self.add_mis_connection(mis1_id, mis2_id)
        self.assertEqual(self.db_session.query(metabase.MisConnection.start_date)
                         .filter_by(id=mis_connection_id).one()[0],
                         mis1.start_date, "mis_connection start_date not OK")
        self.assertEqual(self.db_session.query(metabase.MisConnection.end_date)
                         .filter_by(id=mis_connection_id).one()[0],
                         mis2.end_date, "mis_connection end_date not OK")

        mis1.end_date = mis1.start_date + datetime.timedelta(days=400)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.MisConnection.end_date)
                         .filter_by(id=mis_connection_id).one()[0],
                         mis1.end_date, "mis_connection end_date not OK")

        mis2.start_date = mis2.start_date + datetime.timedelta(days=400)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.MisConnection.start_date)
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

        _compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
                         .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")

        _compute_transfers(self.db_session, 100)
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        stop3 = new_stop("code3", "Los Angeles Airport", mis2_id)
        stop3.lat = 33.9434
        stop3.long = -118.4079
        self.db_session.add(stop3)
        self.db_session.flush()

        _compute_transfers(self.db_session, 90000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
                         .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer)
                         .filter(or_(metabase.Transfer.stop1_id == stop3.id,
                                     metabase.Transfer.stop2_id == stop3.id))
                         .count(),
                         0, "This transfer should not exist")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         1, "Found more transfers than expected")

        _compute_transfers(self.db_session, 900000000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
                         .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()[0],
                         720, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
                         .filter_by(stop1_id=stop1.id, stop2_id=stop3.id).one()[0],
                         9127641, "Transfer distance different than expected")
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         2, "Found more transfers than expected")

        _compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
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

        _compute_transfers(self.db_session, 1000)
        for stop1_id, stop2_id, distance in [(stop1.id, stop2.id, 720),
                                             (stop1.id, stop4.id, 0),
                                             (stop2.id, stop4.id, 720)]:
            self.assertEqual(self.db_session.query(metabase.Transfer.distance)
                             .filter_by(stop1_id=stop1_id, stop2_id=stop2_id)
                             .one()[0],
                             distance, "Transfer distance different than expected")
            self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                             3, "Found more transfers than expected")

        self.db_session.delete(stop2)
        self.db_session.delete(stop4)
        self.db_session.flush()
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        _compute_transfers(self.db_session, 1000)
        self.assertEqual(self.db_session.query(metabase.Transfer).count(),
                         0, "Found transfer where there should not be any")

        _compute_transfers(self.db_session, 900000000)
        self.assertEqual(self.db_session.query(metabase.Transfer.distance)
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
        mis_connections = set(mis_connections)  # Remove duplicates

        for s1, s2 in transfers:
            self.add_transfer(s1, s2)

        _compute_mis_connections(self.db_session)
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
        _compute_mis_connections(self.db_session)
        # mis_connection should still be here
        self.assertEqual(self.db_session.query(metabase.MisConnection)
                         .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         1, "MisConnection not found")

        self.db_session.query(metabase.Transfer).filter_by(stop1_id=stop1_id, stop2_id=stop5_id).delete()
        self.db_session.flush()
        _compute_mis_connections(self.db_session)
        # mis_connection should not exist as all transfers between mis1 and mis4 have been deleted
        self.assertEqual(self.db_session.query(metabase.MisConnection)
                         .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         0, "MisConnection should have been deleted")

        self.add_transfer(stop1_id, stop6_id)
        self.db_session.flush()
        _compute_mis_connections(self.db_session)
        # mis_connection should come back now that a transfer has been added
        self.assertEqual(self.db_session.query(metabase.MisConnection)
                         .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         1, "MisConnection not found")

        mis1 = self.db_session.query(metabase.Mis).get(mis1_id)
        mis4 = self.db_session.query(metabase.Mis).get(mis4_id)
        mis1.start_date = date_type(year=2010, month=6, day=4)
        mis1.end_date = date_type(year=2012, month=6, day=4)
        mis4.start_date = date_type(year=2012, month=7, day=1)
        mis4.end_date = date_type(year=2013, month=4, day=1)
        self.db_session.commit()
        _compute_mis_connections(self.db_session)
        # Validity periods don't overlap, so mis_connection should not have been created.
        self.assertEqual(self.db_session.query(metabase.MisConnection)
                         .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         0, "MisConnection should have been deleted")

        mis4.start_date = date_type(year=2011, month=7, day=1)
        self.db_session.commit()
        _compute_mis_connections(self.db_session)
        # Validity periods now overlap, so mis_connection should exist.
        self.assertEqual(self.db_session.query(metabase.MisConnection)
                         .filter_by(mis1_id=mis1_id, mis2_id=mis4_id).count(),
                         1, "MisConnection not found")

    """
    Check that if a transfer modification_state is 'recalculate', the back_office 
    effectively recalculate distance and durations for this transfer.
    """

    def test_recalculate_state(self):
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
        _compute_transfers(self.db_session, 900)

        transfer = self.db_session.query(metabase.Transfer) \
            .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        original_values = [transfer.distance, transfer.duration, transfer.prm_duration]
        transfer.distance = randint(10, 10000)
        transfer.duration = randint(10, 10000)
        transfer.prm_duration = randint(10, 10000)
        transfer.modification_state = "recalculate"
        self.db_session.commit()

        _compute_transfers(self.db_session, 900)

        transfer = self.db_session.query(metabase.Transfer) \
            .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        self.assertEqual(transfer.modification_state, 'auto', "Transfer modification_state should be 'auto'")
        self.assertEqual(transfer.active, True, "Transfer should be active")
        self.assertEqual(original_values,
                         [transfer.distance, transfer.duration, transfer.prm_duration],
                         "Distance and durations have not been recalculated properly ")

    """
        Check that trigger on transfer 'active' column works accordingly.
    """

    def test_transfer_active_trigger(self):
        mis_id = self.add_mis("mis1")

        stop1 = new_stop("code1", "stop1")
        stop1.mis1_id = mis_id
        stop2 = new_stop("code2", "stop2")
        stop2.mis_id = mis_id
        self.db_session.add(stop1)
        self.db_session.add(stop2)
        self.db_session.flush()
        transfer_id = self.add_transfer(stop1.id, stop2.id)
        t = self.db_session.query(metabase.Transfer) \
            .filter_by(id=transfer_id).one()
        self.assertEqual(t.active, True)

        # When modification_state is 'validation_needed', active is automatically
        # set to False.
        t.modification_state = 'validation_needed'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, False)

        t.active = True
        self.db_session.commit()
        self.db_session.expire_all()
        # Because modification_state is still 'validation_needed', active should
        # be forced to False.
        self.assertEqual(t.active, False)

        t.active = True
        t.modification_state = "auto"
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, True)

        t.modification_state = 'manual'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, True)

        # When modification_state is 'recalculate', active is automatically
        # set to False.
        t.modification_state = 'recalculate'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, False)

        t.active = True
        self.db_session.commit()
        self.db_session.expire_all()
        # Because modification_state is still 'recalculate', active should
        # be forced to False.
        self.assertEqual(t.active, False)

        t.modification_state = 'auto'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, False)

        t.active = True
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertEqual(t.active, True)

    """
    Check that back_office doesn't modify transfer when its status is
    'auto', 'validation_needed' or 'manual'.
    """

    def test_transfer_state_unchanged(self):
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
        _compute_transfers(self.db_session, 900)

        transfer = self.db_session.query(metabase.Transfer) \
            .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
        transfer.distance = randint(10, 10000)
        transfer.duration = randint(10, 10000)
        transfer.prm_duration = randint(10, 10000)
        manual_values = [transfer.distance, transfer.duration, transfer.prm_duration]

        for state in ['manual', 'validation_needed', 'auto']:
            transfer.modification_state = state
            self.db_session.flush()
            _compute_transfers(self.db_session, 900)
            transfer = self.db_session.query(metabase.Transfer) \
                .filter_by(stop1_id=stop1.id, stop2_id=stop2.id).one()
            self.assertEqual(transfer.modification_state, state, "Transfer status should be '%s'" % state)
            self.assertEqual(manual_values,
                             [transfer.distance, transfer.duration, transfer.prm_duration],
                             "Distance and durations should not have been modified")

    """
        Check that dates are correctly set when a row is created/updated.
    """

    def test_creation_update_dates_trigger(self):
        approx_creation_date = datetime.datetime.now()
        mis1_id = self.add_mis("mis1")
        mis1 = self.db_session.query(metabase.Mis).get(mis1_id)
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(mis1.created_at - approx_creation_date < timedelta(seconds=4))

        approx_update_date = datetime.datetime.now()
        mis1.name += "abc"
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(mis1.updated_at - approx_update_date < timedelta(seconds=4))

        approx_creation_date = datetime.datetime.now()
        stop1 = new_stop("code1", "Gare de Lyon", mis1_id)
        self.db_session.add(stop1)
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(stop1.created_at - approx_creation_date < timedelta(seconds=4))

        approx_update_date = datetime.datetime.now()
        stop1.lat -= 2
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(stop1.updated_at - approx_update_date < timedelta(seconds=4))

        approx_creation_date = datetime.datetime.now()
        mis2_id = self.add_mis("mis2")
        mis2 = self.db_session.query(metabase.Mis).get(mis2_id)
        stop2 = new_stop("code1", "Gare de Lyon", mis2_id)
        self.db_session.add(stop2)
        self.db_session.commit()
        transfer_id = self.add_transfer(stop1.id, stop2.id)
        transfer = self.db_session.query(metabase.Transfer).get(transfer_id)
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(transfer.created_at - approx_creation_date < timedelta(seconds=4))

        approx_update_date = datetime.datetime.now()
        transfer.duration += 30
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(transfer.updated_at - approx_update_date < timedelta(seconds=4))

        approx_creation_date = datetime.datetime.now()
        mode = metabase.Mode()
        mode.code = 'bus'
        self.db_session.add(mode)
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(mode.created_at - approx_creation_date < timedelta(seconds=4))

        approx_update_date = datetime.datetime.now()
        mode.code = 'tram'
        self.db_session.commit()
        self.db_session.expire_all()
        self.assertTrue(mode.updated_at - approx_update_date < timedelta(seconds=4))

    def test_mis_dates_overlap(self):
        mis1_id = self.add_mis(name="mis1")
        mis2_id = self.add_mis(name="mis2")
        mis1 = self.db_session.query(metabase.Mis).get(mis1_id)
        mis2 = self.db_session.query(metabase.Mis).get(mis2_id)

        mis1.start_date = date_type(year=2010, month=6, day=4)
        mis1.end_date = date_type(year=2012, month=6, day=4)
        mis2.start_date = date_type(year=2009, month=6, day=4)
        mis2.end_date = date_type(year=2012, month=2, day=3)
        self.db_session.commit()
        self.assertTrue(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2010, month=6, day=4)
        mis1.end_date = date_type(year=2012, month=6, day=4)
        mis2.start_date = date_type(year=2012, month=6, day=5)
        mis2.end_date = date_type(year=2013, month=2, day=3)
        self.db_session.commit()
        self.assertFalse(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2010, month=6, day=4)
        mis1.end_date = date_type(year=2012, month=6, day=4)
        mis2.start_date = date_type(year=2013, month=4, day=1)
        mis2.end_date = date_type(year=2016, month=2, day=3)
        self.db_session.commit()
        self.assertFalse(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2008, month=1, day=2)
        mis1.end_date = date_type(year=2010, month=6, day=4)
        mis2.start_date = date_type(year=2009, month=6, day=4)
        mis2.end_date = date_type(year=2012, month=2, day=3)
        self.db_session.commit()
        self.assertTrue(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2008, month=1, day=2)
        mis1.end_date = date_type(year=2010, month=6, day=4)
        mis2.start_date = date_type(year=2010, month=6, day=4)
        mis2.end_date = date_type(year=2012, month=2, day=3)
        self.db_session.commit()
        self.assertTrue(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2008, month=1, day=2)
        mis1.end_date = date_type(year=2010, month=6, day=4)
        mis2.start_date = date_type(year=2010, month=4, day=3)
        mis2.end_date = date_type(year=2012, month=2, day=3)
        self.db_session.commit()
        self.assertTrue(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        mis1.start_date = date_type(year=2010, month=6, day=4)
        mis1.end_date = date_type(year=2012, month=6, day=4)
        mis2.start_date = date_type(year=2013, month=4, day=1)
        mis2.end_date = None
        self.db_session.commit()
        self.assertTrue(mis_dates_overlap(self.db_session, mis1_id, mis2_id))

        #  todo
        # #def test change on max distanance to calculate transfers


if __name__ == '__main__':
    unittest.main()
