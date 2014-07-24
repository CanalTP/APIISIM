BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, 
                 geographic_position_compliant, multiple_start_and_arrivals) VALUES
    ('stub_transilien_light', 'comment1', 'http://127.0.0.1:5000/stub_transilien_light/v0/', '', DATE '2007-05-16', 
     DATE '2016-05-16', TRUE, 1),
    ('stub_pays_de_la_loire_light', 'comment2', 'http://127.0.0.1:5000/stub_pays_de_la_loire_light/v0/', '', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1),
    ('stub_bourgogne_light', 'comment2', 'http://127.0.0.1:5000/stub_bourgogne_light/v0/', '', DATE '2008-02-19', 
     DATE '2016-04-16', TRUE, 1);

COMMIT;
\q
