CREATE TABLE User (
  user_id INTEGER UNIQUE NOT NULL,
  name TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL,
  privilege_lvl INTEGER NOT NULL,
  PRIMARY KEY (user_id AUTOINCREMENT)
);

CREATE TABLE Category (
  id INTEGER UNIQUE NOT NULL,
  name TEXT NOT NULL,
  PRIMARY KEY (id AUTOINCREMENT)
);

CREATE TABLE Problem (
  id INTEGER UNIQUE NOT NULL,
  cat_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  "desc" TEXT,
  created_by INTEGER NOT NULL,
  PRIMARY KEY (id AUTOINCREMENT),
  FOREIGN KEY (created_by) REFERENCES User(user_id),
  FOREIGN KEY (cat_id) REFERENCES Category(id)
);

CREATE TABLE Testcase (
  test_no INTEGER NOT NULL,
  problem_id INTEGER NOT NULL,
  "type" INTEGER NOT NULL,
  "in" TEXT NOT NULL,
  "out" TEXT NOT NULL,
  "note" TEXT,
  PRIMARY KEY (test_no, problem_id),
  FOREIGN KEY (problem_id) REFERENCES Problem(id)
);

CREATE TABLE Tag (
  id INTEGER UNIQUE NOT NULL,
  name TEXT NOT NULL,
  PRIMARY KEY (id AUTOINCREMENT)
);

CREATE TABLE Problems2tags (
  problem_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (problem_id, tag_id),
  FOREIGN KEY (tag_id) REFERENCES Tag(id),
  FOREIGN KEY (problem_id) REFERENCES Problem(id)
);

