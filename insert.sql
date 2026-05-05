INSERT INTO User (user_id, name, pw_hash, privilege_lvl) VALUES
(0, 'Super Admin', '$2b$12$Pk4KkAVRCM1zoVPQSSDanePfVR1baGyga.OMsXDefQNcOiYZUSkZ.', 3);

INSERT INTO Category (name) VALUES
('Example Category');

INSERT INTO Problem (cat_id, title, "desc", created_by) VALUES
(1, 'A+B', 'Placeholder desc', 0),
(1, 'A-B', 'Placeholder desc', 0);

