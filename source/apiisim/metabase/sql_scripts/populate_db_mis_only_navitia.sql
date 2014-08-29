BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('paysdelaloire', 'comment1', 'http://127.0.0.1:5000/pays_de_la_loire/v0/', '77bca947-ca67-4f17-92a3-92b716fc3d82', DATE '2007-05-16', 
     DATE '2016-05-16', TRUE, 1),
    ('bretagne', 'comment2', 'http://127.0.0.1:5000/bretagne/v0/', 'f8a9befb-6bd9-4620-b942-b6b69a07487d', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1),
    ('transilien', 'comment2', 'http://127.0.0.1:5000/transilien/v0/', 'f8a9befb-6bd9-4620-b942-b6b69a07487d', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1),
    ('bourgogne', 'comment3', 'http://127.0.0.1:5000/bourgogne/v0/', 'f8a9befb-6bd9-4620-b942-b6b69a07487d', DATE '2012-12-11', 
     DATE '2018-08-01', TRUE, 1),
    ('sncfnational', 'comment3', 'http://127.0.0.1:5000/sncf_national/v0/', '05a80956-5360-45e1-ba48-ffd3805404e1', DATE '2012-12-11', 
     DATE '2018-08-01', TRUE, 1);

COMMIT;
\q
