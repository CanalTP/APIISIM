from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, Boolean, Float, \
                       ForeignKey, Index, UniqueConstraint, TEXT, DATE
from sqlalchemy.orm import relationship, backref, Session
from apiisim.common import OUTPUT_ENCODING
import datetime
from geoalchemy2 import Geography, Geometry

###############################################################################

Base = declarative_base()

class Mis(Base):
    __tablename__ = 'mis'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    comment = Column(TEXT)
    api_url = Column(String(255), nullable=False)
    api_key = Column(String(50))
    start_date = Column(DATE)
    end_date = Column(DATE)
    geographic_position_compliant = Column(Boolean)
    multiple_starts_and_arrivals = Column(Integer)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    stops = relationship("Stop", backref="mis")

    def __repr__(self):
        return (u"<Mis(id='%s', name='%s', api_url='%s', start_date='%s', end_date='%s')>" % \
                (self.id, self.name, self.api_url, self.start_date, self.end_date)) \
                .encode(OUTPUT_ENCODING)

class Stop(Base):
    __tablename__ = 'stop'
    __table_args__ = (
        Index(u'stop_code_mis_id_key', u'code', u'mis_id'),
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False)
    mis_id = Column(ForeignKey('mis.id'), nullable=False)
    name = Column(String(255), nullable=False)
    lat = Column(Float(53), nullable=False)
    long = Column(Float(53), nullable=False)
    stop_type = Column(Enum(u'GL', u'LAMU', u'ZE', name=u'stop_type_enum'))
    administrative_code = Column(String(255))
    parent_id = Column(ForeignKey('stop.id'))
    transport_mode = Column(Enum(u'all', u'bus', u'trolleybus', u'tram', u'coach',
                                 u'rail', u'intercityrail', u'urbanrail', u'metro',
                                 u'air', u'water', u'cable', u'funicular', u'taxi',
                                 u'bike', u'car', name=u'transport_mode_enum'))
    quay_type = Column(String(255))
    geog = Column(Geography(geometry_type="POINT", srid=4326,
                            spatial_index=True))
    geom = Column(Geometry)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    def __repr__(self):
        return (u"<Stop(id='%s', name='%s', code='%s', mis_id='%s', lat=%s, long=%s)>" % \
                (self.id, self.name, self.code, self.mis_id, self.lat, self.long)) \
                .encode(OUTPUT_ENCODING)

class MisConnection(Base):
    __tablename__ = u'mis_connection'
    __table_args__ = (
        Index(u'mis_connection_mis1_id_mis2_id_key', u'mis1_id', u'mis2_id'),
    )

    id = Column(Integer, primary_key=True)
    mis1_id = Column(ForeignKey('mis.id'), nullable=False)
    mis2_id = Column(ForeignKey('mis.id'), nullable=False)
    start_date = Column(DATE)
    end_date = Column(DATE)

    mis1 = relationship(u'Mis', primaryjoin='MisConnection.mis1_id == Mis.id')
    mis2 = relationship(u'Mis', primaryjoin='MisConnection.mis2_id == Mis.id')
    UniqueConstraint('mis1_id', 'mis2_id')

    def __repr__(self):
        return (u"<MisConnection(id='%s', mis1_id='%s', mis2_id='%s', start_date=%s, end_date=%s)>" % \
                (self.id, self.mis1_id, self.mis2_id, self.start_date, self.end_date)) \
                .encode(OUTPUT_ENCODING)

class Transfer(Base):
    __tablename__ = u'transfer'
    __table_args__ = (
        Index(u'transfer_stop1_id_stop2_id_key', u'stop1_id', u'stop2_id'),
    )

    id = Column(Integer, primary_key=True)
    stop1_id = Column(ForeignKey('stop.id'), nullable=False)
    stop2_id = Column(ForeignKey('stop.id'), nullable=False)
    distance = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    prm_duration = Column(Integer)
    active = Column(Boolean, nullable=False, default=True)
    modification_state = Column(
                            Enum(u'auto', u'manual', u'validation_needed',
                                 u'recalculate', name=u'transfer_state_enum'),
                            nullable=False)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)


    stop1 = relationship(u'Stop', primaryjoin='Transfer.stop1_id == Stop.id')
    stop2 = relationship(u'Stop', primaryjoin='Transfer.stop2_id == Stop.id')
    UniqueConstraint('stop1_id', 'stop2_id')

    def __repr__(self):
        return (u"<Transfer(id='%s', stop1_id='%s', stop2_id='%s', distance='%s', " \
                "duration='%s', prm_duration='%s', active='%s', modification_state='%s')>" % \
                (self.id, self.stop1_id, self.stop2_id, self.distance,
                 self.duration, self.prm_duration, self.active, self.modification_state)) \
                .encode(OUTPUT_ENCODING)


class Mode(Base):
    __tablename__ = u'mode'

    id = Column(Integer, primary_key=True)
    code = Column(
            Enum(u'all', u'bus', u'trolleybus', u'tram', u'coach', u'rail',
                 u'intercityrail', u'urbanrail', u'metro', u'air', u'water',
                 u'cable', u'funicular', u'taxi', u'bike', u'car', name=u'mode_enum'),
                 nullable=False, unique=True)
    description = Column(TEXT)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    def __repr__(self):
        return (u"<Mode(id='%s', code='%s')>" % \
                (self.id, self.code)).encode(OUTPUT_ENCODING)

class MisMode(Base):
    __tablename__ = u'mis_mode'
    __table_args__ = (
        Index(u'mis_mode_mis_id_mode_id_key', u'mis_id', u'mode_id'),
    )

    id = Column(Integer, primary_key=True)
    mis_id = Column(ForeignKey('mis.id'), nullable=False)
    mode_id = Column(ForeignKey('mode.id'), nullable=False)

    mis = relationship(u'Mis')
    mode = relationship(u'Mode')

    UniqueConstraint('mis_id', 'mode_id')

    def __repr__(self):
        return (u"<MisMode(id='%s', mis_id='%s', mode_id='%s')>" % \
                (self.id, self.mis_id, self.mode_id)).encode(OUTPUT_ENCODING)

class TransferMis(Base):
    __tablename__ = 'transfer_mis'

    transfer_id = Column(Integer, primary_key=True)
    mis1_id = Column(Integer, nullable=False)
    mis2_id = Column(Integer, nullable=False)
    transfer_active = Column(Boolean)
