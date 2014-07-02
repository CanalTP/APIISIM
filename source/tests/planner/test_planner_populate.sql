BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('mis1', 'comment1', 'mis1_url', '', TIMESTAMP '2007-05-16 15:36:38', 
     TIMESTAMP '2016-05-16 15:36:38', TRUE, FALSE),
    ('mis2', 'comment2', 'mis2_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE),
    ('mis3', 'comment3', 'mis3_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE),
    ('mis4', 'comment4', 'mis4_url', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE);

INSERT INTO stop (code, mis_id, name, lat, long) VALUES
    ('stop_code10', 1, '', 0, 0),
    ('stop_code20', 2, '', 0, 0),
    ('stop_code30', 3, '', 0, 0),
    ('stop_code40', 4, '', 0, 0),
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
    (7, 4, 100, 10, 'auto');

COMMIT;
\q
