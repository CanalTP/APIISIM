BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('stub_transilien', 'comment1', 'http://127.0.0.1:5000/stub_transilien/v0/', '', DATE '2007-05-16', 
     DATE '2016-05-16', TRUE, 1),
    ('stub_pays_de_la_loire', 'comment2', 'http://127.0.0.1:5000/stub_pays_de_la_loire/v0/', '', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1),
    ('stub_bourgogne', 'comment2', 'http://127.0.0.1:5000/stub_bourgogne/v0/', '', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 0),
    ('stub_sncf_national', 'comment2', 'http://127.0.0.1:5000/stub_sncf_national/v0/', '', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1);

COMMIT;
\q
