BEGIN;

CREATE TABLE mis(
    id serial PRIMARY KEY,
    name varchar(50) NOT NULL,
    comment text,
    api_url varchar(255) NOT NULL,
    api_key varchar(50),
    start_date date,
    end_date date,
    geographic_position_compliant boolean,
    multiple_start_and_arrivals integer,
    created_at timestamp,
    updated_at timestamp
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
    stop_type stop_type_enum,
    administrative_code varchar(255),
    parent_id integer REFERENCES stop(id),
    transport_mode transport_mode_enum,
    quay_type varchar(255),
    -- We'll use PostGIS geography type to calculate distance between stop points.
    geog GEOGRAPHY(Point),
    geom geometry,
    created_at timestamp,
    updated_at timestamp,
    UNIQUE(code, mis_id)
);

CREATE TYPE transfer_state_enum AS ENUM ('auto', 'manual', 'validation_needed',
                                         'recalculate');

CREATE TABLE transfer(
    id serial PRIMARY KEY,
    stop1_id integer REFERENCES stop(id) ON DELETE CASCADE NOT NULL,
    stop2_id integer REFERENCES stop(id) ON DELETE CASCADE NOT NULL,
    distance integer NOT NULL,
    duration integer NOT NULL,
    prm_duration integer,
    active boolean DEFAULT TRUE NOT NULL,
    modification_state transfer_state_enum NOT NULL,
    created_at timestamp,
    updated_at timestamp,
    UNIQUE(stop1_id, stop2_id)
);


CREATE TABLE mis_connection(
    id serial PRIMARY KEY,
    mis1_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    mis2_id integer REFERENCES mis(id) ON DELETE CASCADE NOT NULL,
    start_date date,
    end_date date,
    UNIQUE(mis1_id, mis2_id)
);

CREATE TABLE mode(
    id serial PRIMARY KEY,
    code transport_mode_enum UNIQUE NOT NULL,
    description text,
    created_at timestamp,
    updated_at timestamp
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
CREATE INDEX stop_geog_gist ON stop USING GIST (geog);

-- Triggers

-- If "lat" or "long" attributes change, update PostGIS geography column accordingly.
CREATE OR REPLACE FUNCTION stop_pre_update_handler()
RETURNS trigger AS $$
BEGIN
    -- When inserting, OLD is not defined so we have to make a special case for INSERT
    IF (TG_OP = 'INSERT') THEN
        NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
    ELSE 
        IF NEW.lat != OLD.lat OR NEW.long != OLD.long THEN
            NEW.geog:='POINT('||NEW.long||' '||NEW.lat||')';
        END IF;
    END IF; 

    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';  

CREATE TRIGGER stop_pre_update BEFORE INSERT OR UPDATE ON stop
FOR EACH ROW 
EXECUTE PROCEDURE stop_pre_update_handler();


-- If "lat" or "long" attributes are modified, update modification_state
-- of all transfers that use this stop.
CREATE OR REPLACE FUNCTION stop_post_update_handler()
RETURNS trigger AS $$
BEGIN
    IF NEW.lat != OLD.lat OR NEW.long != OLD.long THEN
        UPDATE transfer
        SET modification_state='validation_needed'
        WHERE ((stop1_id=NEW.id) OR (stop2_id=NEW.id))
              AND modification_state='manual';
        UPDATE transfer
        SET modification_state='recalculate'
        WHERE ((stop1_id=NEW.id) OR (stop2_id=NEW.id))
              AND modification_state='auto';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER stop_post_update AFTER UPDATE ON stop
FOR EACH ROW 
EXECUTE PROCEDURE stop_post_update_handler();


-- If transfer is not in a consistent state, disable it.
CREATE OR REPLACE FUNCTION disable_inconsistent_transfer()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.modification_state = 'validation_needed' OR
       NEW.modification_state = 'recalculate' THEN
        NEW.active := FALSE;
    END IF;
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER transfer_pre_update BEFORE INSERT OR UPDATE ON transfer
FOR EACH ROW
EXECUTE PROCEDURE disable_inconsistent_transfer();


-- Functions to calculate start_date and end_date for a given mis_connection.
-- start_date is the maximum between start_date of mis1 and start_date of mis2.
-- end_date is the minimum between end_date of mis1 and end_date of mis2.
CREATE OR REPLACE FUNCTION mis_connection_calculate_start_date(mis1_id integer, mis2_id integer)
RETURNS date AS $$
BEGIN
    RETURN (SELECT GREATEST(
                (SELECT start_date from mis where id=mis1_id), 
                (SELECT start_date from mis where id=mis2_id)));
END;
$$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION mis_connection_calculate_end_date(mis1_id integer, mis2_id integer)
RETURNS date AS $$
BEGIN
    RETURN (SELECT LEAST(
                (SELECT end_date from mis where id=mis1_id), 
                (SELECT end_date from mis where id=mis2_id)));
END;
$$ LANGUAGE 'plpgsql';

-- If dates are modified on a given mis, update dates for all
-- mis_connections using this mis.
CREATE OR REPLACE FUNCTION mis_post_update_handler()
RETURNS trigger AS $$
BEGIN

    IF NEW.start_date != OLD.start_date OR NEW.end_date != OLD.end_date THEN
        UPDATE mis_connection 
        SET start_date = (SELECT mis_connection_calculate_start_date(mis1_id, mis2_id)),
            end_date = (SELECT mis_connection_calculate_end_date(mis1_id, mis2_id))
        WHERE (mis1_id=NEW.id) OR (mis2_id=NEW.id);
    END IF; 

    RETURN NULL;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER mis_post_update AFTER UPDATE ON mis
FOR EACH ROW 
EXECUTE PROCEDURE mis_post_update_handler();


-- When inserting a new mis_connection, calculate its dates based on the dates
-- of the 2 linked MIS.
CREATE OR REPLACE FUNCTION mis_connection_pre_insert_handler()
RETURNS trigger AS $$
BEGIN

    NEW.start_date := (SELECT mis_connection_calculate_start_date(NEW.mis1_id, NEW.mis2_id));
    NEW.end_date := (SELECT mis_connection_calculate_end_date(NEW.mis1_id, NEW.mis2_id));

    RETURN NEW;

END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER mis_connection_pre_insert BEFORE INSERT ON mis_connection
FOR EACH ROW 
EXECUTE PROCEDURE mis_connection_pre_insert_handler();


-- Set creation date when table is created
CREATE OR REPLACE FUNCTION set_created_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at := now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER mis_connection_pre_insert2 BEFORE INSERT ON mis
FOR EACH ROW
EXECUTE PROCEDURE set_created_at_timestamp();

CREATE TRIGGER stop_pre_insert BEFORE INSERT ON stop
FOR EACH ROW
EXECUTE PROCEDURE set_created_at_timestamp();

CREATE TRIGGER transfer_pre_insert BEFORE INSERT ON transfer
FOR EACH ROW
EXECUTE PROCEDURE set_created_at_timestamp();

CREATE TRIGGER mode_pre_insert BEFORE INSERT ON mode
FOR EACH ROW
EXECUTE PROCEDURE set_created_at_timestamp();


-- Set update date when table is updated
CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER mis_connection_pre_update BEFORE UPDATE ON mis
FOR EACH ROW
EXECUTE PROCEDURE set_updated_at_timestamp();

CREATE TRIGGER stop_pre_update2 BEFORE UPDATE ON stop
FOR EACH ROW
EXECUTE PROCEDURE set_updated_at_timestamp();

CREATE TRIGGER transfer_pre_update2 BEFORE UPDATE ON transfer
FOR EACH ROW
EXECUTE PROCEDURE set_updated_at_timestamp();

CREATE TRIGGER mode_pre_update BEFORE UPDATE ON mode
FOR EACH ROW
EXECUTE PROCEDURE set_updated_at_timestamp();


-- Views

CREATE VIEW transfer_mis AS 
SELECT t.id transfer_id, m1.id mis1_id, m2.id mis2_id, t.active transfer_active
FROM transfer t, stop s1, stop s2, mis m1, mis m2
WHERE s1.mis_id=m1.id AND s2.mis_id=m2.id AND t.stop1_id=s1.id AND t.stop2_id=s2.id;
COMMIT;
\q
