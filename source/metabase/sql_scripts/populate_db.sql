BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('mis1', 'comment1', 'url1', 'key1', TIMESTAMP '2011-05-16 15:36:38', 
     TIMESTAMP '2016-05-16 15:36:38', TRUE, FALSE),
    ('mis2', 'comment2', 'url2', 'key2', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2014-04-16 15:36:38', FALSE, FALSE),
    ('mis3', 'comment3', 'url3', 'key3', TIMESTAMP '2012-12-11 15:36:38', 
     TIMESTAMP '2018-08-01 15:36:38', TRUE, TRUE);

INSERT INTO stop (code, mis_id, name, lat, long) VALUES
    ('stop_code1', 1, 'stop1', 11, 111),
    ('stop_code2', 2, 'stop2', 21, 122),
    ('stop_code3', 3, 'stop3', 33, 133);

INSERT INTO transfer (stop1_id, stop2_id, distance, duration, prm_duration, status) VALUES
    (1, 2, 120, 10, 20,'auto'),
    (2, 3, 140, 1, 40, 'manual'),
    (3, 1, 260, 20, 66,'blocked');

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
