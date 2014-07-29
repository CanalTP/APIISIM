BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('mis1', 'comment1', 'http://127.0.0.1:5000/test1/v0/', 'key1', DATE '2011-05-16', 
     DATE '2016-05-16', TRUE, 0),
    ('mis2', 'comment2', 'http://127.0.0.1:5000/test2/v0/', 'key2', DATE '2008-02-19', 
     DATE '2014-04-16', FALSE, 0),
    ('mis3', 'comment3', 'url3', 'key3', DATE '2012-12-11', 
     DATE '2018-08-01', TRUE, 1);

COMMIT;
\q
