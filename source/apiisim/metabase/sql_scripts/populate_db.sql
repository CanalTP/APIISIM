BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('mis1', 'comment1', 'url1', 'key1', DATE '2011-05-16', 
     DATE '2016-05-16', TRUE, 0),
    ('mis2', 'comment2', 'url2', 'key2', DATE '2008-02-19', 
     DATE '2014-04-16', FALSE, 0),
    ('mis3', 'comment3', 'url3', 'key3', DATE '2012-12-11', 
     DATE '2018-08-01', TRUE, 1);

INSERT INTO stop (code, mis_id, name, lat, long) VALUES
    ('stop_code1', 1, 'stop1', 11, 111),
    ('stop_code2', 2, 'stop2', 21, 122),
    ('stop_code3', 3, 'stop3', 33, 133);

INSERT INTO transfer (stop1_id, stop2_id, distance, duration, prm_duration, active, modification_state) VALUES
    (1, 2, 120, 10, 20, TRUE, 'auto'),
    (2, 3, 140, 1, 40, TRUE, 'manual'),
    (3, 1, 260, 20, 66, TRUE, 'auto');

INSERT INTO mis_connection (mis1_id, mis2_id, start_date, end_date) VALUES
    (1, 2, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=2))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=2)))),
    (2, 3,
     (SELECT GREATEST((SELECT start_date from mis where id=2), (SELECT start_date from mis where id=3))), 
     (SELECT LEAST((SELECT end_date from mis where id=2), (SELECT end_date from mis where id=3)))),
    (1, 3, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=3))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=3))));

INSERT INTO mode (code) VALUES
    ('bus'),
    ('all'),
    ('funicular');

INSERT INTO mis_mode (mis_id, mode_id) VALUES
    (1,1),
    (1,2),
    (2,2);

COMMIT;
\q
