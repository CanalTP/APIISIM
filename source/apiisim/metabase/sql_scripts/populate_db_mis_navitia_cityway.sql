BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('champagneardenne', 'comment1', 'http://127.0.0.1:5000/champagne_ardenne/v0/', '5f55af39-328d-4206-8830-2022212859e9', DATE '2007-05-16', 
     DATE '2016-05-16', TRUE, 1),
    ('transilien', 'comment2', 'http://127.0.0.1:5000/transilien/v0/', 'f8a9befb-6bd9-4620-b942-b6b69a07487d', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1),
    ('sncfnational', 'comment3', 'http://127.0.0.1:5000/sncf_national/v0/', '05a80956-5360-45e1-ba48-ffd3805404e1', DATE '2012-12-11', 
     DATE '2018-08-01', TRUE, 1),
    ('alsace', 'comment4', 'http://preprod.vialsace2.tsi.cityway.fr/webservices/APII-SIM-Connector/1.0/', '', DATE '2012-12-11',
     DATE '2018-08-01', TRUE, 1),
    ('oise', 'comment5', 'http://preprod.sismo.cityway.fr/webservices/APII-SIM-Connector/1.0/', '', DATE '2012-12-11',
     DATE '2018-08-01', TRUE, 1);

COMMIT;
\q
