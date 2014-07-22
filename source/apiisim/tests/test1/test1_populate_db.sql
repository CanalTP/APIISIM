BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('mis1', 'comment1', 'http://127.0.0.1:5000/test1/v0/', 'key1', TIMESTAMP '2011-05-16 15:36:38', 
     TIMESTAMP '2016-05-16 15:36:38', TRUE, FALSE),
    ('mis2', 'comment2', 'http://127.0.0.1:5000/test2/v0/', 'key2', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2014-04-16 15:36:38', FALSE, FALSE),
    ('mis3', 'comment3', 'url3', 'key3', TIMESTAMP '2012-12-11 15:36:38', 
     TIMESTAMP '2018-08-01 15:36:38', TRUE, TRUE);

COMMIT;
\q
