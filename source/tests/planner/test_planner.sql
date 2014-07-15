BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('mis1', 'comment1', 'mis1_url', '', TIMESTAMP '2007-05-16 15:36:38', 
     TIMESTAMP '2016-05-16 15:36:38', TRUE, FALSE),
    ('mis2', 'comment2', 'mis2_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE),
    ('mis3', 'comment3', 'mis3_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, TRUE),
    ('mis4', 'comment4', 'mis4_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, TRUE);

INSERT INTO stop (code, mis_id, name, lat, long) VALUES
    ('stop_code10', 1, '', 1, 1),
    ('stop_code20', 2, '', 2, 2),
    ('stop_code30', 3, '', 3, 3),
    ('stop_code40', 4, '', 4, 4),
    ('stop_code11', 1, '', 0, 0),
    ('stop_code21', 2, '', 0, 0),
    ('stop_code31', 3, '', 0, 0),
    ('stop_code41', 4, '', 0, 0),
    ('stop_code12', 1, '', 0, 0),
    ('stop_code22', 2, '', 0, 0),
    ('stop_code32', 3, '', 0, 0),
    ('stop_code42', 4, '', 0, 0),
    ('stop_code13', 1, '', 0, 0),
    ('stop_code23', 2, '', 0, 0),
    ('stop_code33', 3, '', 0, 0),
    ('stop_code43', 4, '', 0, 0);

INSERT INTO transfer (stop1_id, stop2_id, distance, duration, status) VALUES
    (1, 2, 100, 10, 'auto'),
    (6, 3, 100, 10, 'auto'),
    (10, 3, 100, 10, 'auto'),
    (14, 3, 100, 10, 'auto'),
    (7, 4, 100, 10, 'auto'),
    (11, 4, 100, 10, 'auto'),
    (1, 12, 100, 10, 'auto');

INSERT INTO mis_connection (mis1_id, mis2_id, start_date, end_date) VALUES
    (1, 2, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=2))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=2)))),
    (2, 3,
     (SELECT GREATEST((SELECT start_date from mis where id=2), (SELECT start_date from mis where id=3))), 
     (SELECT LEAST((SELECT end_date from mis where id=2), (SELECT end_date from mis where id=3)))),
    (3, 4, 
     (SELECT GREATEST((SELECT start_date from mis where id=3), (SELECT start_date from mis where id=4))), 
     (SELECT LEAST((SELECT end_date from mis where id=3), (SELECT end_date from mis where id=4)))),
    (1, 4, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=4))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=4))));


COMMIT;
\q
