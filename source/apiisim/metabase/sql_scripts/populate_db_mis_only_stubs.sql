BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('stub_transilien', 'comment1', 'http://127.0.0.1:5000/stub_transilien/v0/', '', TIMESTAMP '2007-05-16 15:36:38', 
     TIMESTAMP '2016-05-16 15:36:38', TRUE, FALSE),
    ('stub_pays_de_la_loire', 'comment2', 'http://127.0.0.1:5000/stub_pays_de_la_loire/v0/', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE),
    ('stub_bourgogne', 'comment2', 'http://127.0.0.1:5000/stub_bourgogne/v0/', '', TIMESTAMP '2008-02-19 15:36:38', 
     TIMESTAMP '2016-04-16 15:36:38', TRUE, FALSE);

COMMIT;
\q
