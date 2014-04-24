-- CREATE USER afimb_user password 'afimb_user';
CREATE DATABASE afimb_db owner postgres;
\connect afimb_db
BEGIN;

CREATE TABLE mis(
    id serial PRIMARY KEY,
    name varchar(50) NOT NULL,
    comment varchar(255),
    api_url varchar(255) NOT NULL,
    api_key varchar(50),
    start_date timestamp,
    end_date timestamp,
    accessibility boolean,
    car_feeder boolean,
    bike_feeder boolean,
    multiple_start_and_arrivals boolean
);

CREATE TABLE stop(
    id serial PRIMARY KEY,
    code varchar(50) NOT NULL,
    mis_id integer REFERENCES mis(id) NOT NULL,
    name varchar(255) NOT NULL,
    lat double precision NOT NULL,
    long double precision NOT NULL
);

CREATE TYPE transfer_status_enum AS ENUM ('auto', 'manual', 'blocked', 'moved');

CREATE TABLE transfer(
    id serial PRIMARY KEY,
    stop1_id integer REFERENCES stop(id) NOT NULL,
    stop2_id integer REFERENCES stop(id) NOT NULL,
    distance integer NOT NULL,
    duration integer NOT NULL,
    prm_duration integer,
    status transfer_status_enum NOT NULL,
    UNIQUE(stop1_id, stop2_id)
);


CREATE TABLE mis_connection(
    id serial PRIMARY KEY,
    mis1_id integer REFERENCES mis(id) NOT NULL,
    mis2_id integer REFERENCES mis(id) NOT NULL,
    start_date timestamp,
    end_date timestamp,
    coeffcient real,
    UNIQUE(mis1_id, mis2_id)
);

CREATE TYPE mode_enum AS ENUM ('all', 'bus', 'trolleybus', 'tram', 'coach', 'rail',
                               'intercityrail', 'urbanrail', 'metro', 'air', 'water',
                               'cable', 'funicular', 'taxi', 'bike', 'car');

CREATE TABLE mode(
    id serial PRIMARY KEY,
    code mode_enum UNIQUE NOT NULL,
    description varchar(255)
);

CREATE TABLE mis_mode(
    id serial PRIMARY KEY,
    mis_id integer REFERENCES mis(id) NOT NULL,
    mode_id integer REFERENCES mode(id) NOT NULL,
    UNIQUE(mis_id, mode_id)
);

CREATE TABLE schema_migrations(
    version varchar(255) NOT NULL
);

CREATE UNIQUE INDEX unique_schema_migrations ON schema_migrations USING btree(version);

COMMIT;
\q
