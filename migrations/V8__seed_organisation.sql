-- V8: Seed organisation bank details

INSERT INTO organisation (account_name, account_number, sort_code)
VALUES ('NDI IGBO BASINGSTOKE', '49140061', '23-05-80')
ON CONFLICT DO NOTHING;
