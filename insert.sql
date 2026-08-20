INSERT INTO User (user_id, name, pw_hash, privilege_lvl) VALUES
(0, 'Super Admin', '$2b$12$Pk4KkAVRCM1zoVPQSSDanePfVR1baGyga.OMsXDefQNcOiYZUSkZ.', 3);

INSERT INTO Tag (name) VALUES
('Addition and subtraction'),
('Mathematics'),
('Stack'),
('Strings');

INSERT INTO Category (name) VALUES
('Basic maths'),
('Data structures'),
('Language built-ins');

INSERT INTO Problem (cat_id, title, "desc", created_by) VALUES
(1, 'A+B', 'Calculate the sum of two integers, each less than 10000000, separated by a space.', 0),
(1, 'A-B', 'Calculate the absolute difference between two integers, each less than 10000000, separated by a space.', 0),
(2, 'Matching parentheses', 'Check if every opening symbol (one of "(", "{", "[") has a correct, properly nested closing symbol ("]", "}", ")").
Write "yes" to output and "no" otherwise.', 0),
(3, 'Prefix match', 'Given two strings joined with a space, check whether the first string is a prefix of the second.
If so, write "yes" to output. Otherwise, write "no". ', 0);

INSERT INTO Problems2tags (problem_id, tag_id) VALUES
(1, 1),
(1, 2),
(2, 1),
(2, 2),
(3, 3),
(3, 4),
(4, 4);

INSERT INTO Testcase (test_no, problem_id, "type", "in", "out", "note") VALUES
(1, 1, 0, '3 5', '8', '3+5'),
(2, 1, 0, '4 6', '10', NULL),
(3, 1, 1, '3918257 2484362', '6402619', 'bigger numbers'),
(1, 2, 0, '3 5', '-2', '3 - 5 is -2'),
(2, 2, 0, '87 12', '75', NULL),
(3, 2, 1, '9971246 127492', '9843754', 'bigger numbers'),
(4, 2, 1, '123456 8926822', '−8803366', 'bigger numbers');
