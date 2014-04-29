BEGIN;

CREATE TABLE mis(
    id serial PRIMARY KEY,
    name varchar(50) NOT NULL,
    comment varchar(255),
    api_url varchar(255) NOT NULL,
    api_key varchar(50),
    start_date timestamp,
    end_date timestamp,
    geographic_position_compliant boolean,
    multiple_start_and_arrivals boolean
);

CREATE TYPE transport_mode_enum AS ENUM ('all', 'bus', 'trolleybus', 'tram', 'coach', 'rail',
                               'intercityrail', 'urbanrail', 'metro', 'air', 'water',
                               'cable', 'funicular', 'taxi', 'bike', 'car');

-- These values below are just here for testing purposes, the "real" enum
-- values are yet to be defined.
CREATE TYPE stop_type_enum AS ENUM ('GL', 'LAMU', 'ZE');

CREATE TABLE stop(
    id serial PRIMARY KEY,
    code varchar(50) NOT NULL,
    mis_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    name varchar(255) NOT NULL,
    lat double precision NOT NULL,
    long double precision NOT NULL,
    type stop_type_enum,
    administrative_code varchar(255),
    parent_id integer REFERENCES stop(id),
    transport_mode transport_mode_enum,
    quay_type varchar(255),
    UNIQUE(code, mis_id)
);

CREATE TYPE transfer_status_enum AS ENUM ('auto', 'manual', 'blocked', 'moved');

CREATE TABLE transfer(
    id serial PRIMARY KEY,
    stop1_id integer REFERENCES stop(id) ON DELETE CASCADE NOT NULL,
    stop2_id integer REFERENCES stop(id) ON DELETE CASCADE NOT NULL,
    distance integer NOT NULL,
    duration integer NOT NULL,
    prm_duration integer,
    status transfer_status_enum NOT NULL,
    UNIQUE(stop1_id, stop2_id)
);


CREATE TABLE mis_connection(
    id serial PRIMARY KEY,
    mis1_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    mis2_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    start_date timestamp,
    end_date timestamp,
    UNIQUE(mis1_id, mis2_id)
);

CREATE TABLE mode(
    id serial PRIMARY KEY,
    code transport_mode_enum UNIQUE NOT NULL
);

CREATE TABLE mis_mode(
    id serial PRIMARY KEY,
    mis_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    mode_id integer REFERENCES mode(id) ON DELETE CASCADE NOT NULL,
    UNIQUE(mis_id, mode_id)
);

CREATE TABLE schema_migrations(
    version varchar(255) NOT NULL
);

CREATE UNIQUE INDEX unique_schema_migrations ON schema_migrations USING btree(version);

COMMIT;
\q
