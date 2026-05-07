INSERT INTO User (user_id, name, pw_hash, privilege_lvl) VALUES
(0, 'Super Admin', '$2b$12$Pk4KkAVRCM1zoVPQSSDanePfVR1baGyga.OMsXDefQNcOiYZUSkZ.', 3);

INSERT INTO Category (name) VALUES
('Example Category');

INSERT INTO Problem (cat_id, title, "desc", created_by) VALUES
(1, 'A+B', 'Calculate the sum of two integers, each less than 10000000, separated by a space', 0),
(1, 'A-B', 'Calculate the absolute difference between two integers, each less than 10000000, separated by a space', 0),
(1, 'Unknown', NULL, 0);

INSERT INTO Testcase (test_no, problem_id, "type", "in", "out", "note") VALUES
(1, 1, 0, '3 5', '8', '3+5'),
(2, 1, 1, '3918257 2484362', '6402619', 'bigger numbers');
