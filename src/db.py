import contextlib
import os
import sqlite3
import threading

storage = threading.local()

DB_PATH = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, 'app.db'))

def global_db() -> sqlite3.Connection:
    if (db := getattr(storage, 'db', None)) is None:
        setattr(storage, 'db', db := sqlite3.connect(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

def teardown():
    if (db := getattr(storage, 'db', None)) is not None:
        db.close()

def get_problems(cur: sqlite3.Cursor | None = None) -> list[sqlite3.Row]:
    with contextlib.ExitStack() as sk:
        if cur is None:
            cur = global_db().cursor()
            sk.callback(cur.close)
        return cur.execute(r'SELECT id, title FROM Problem').fetchall()

def problem_info(p_id: int, cur: sqlite3.Cursor | None = None) -> sqlite3.Row:
    with contextlib.ExitStack() as sk:
        if cur is None:
            cur = global_db().cursor()
            sk.callback(cur.close)
        return cur.execute(r'SELECT id, title, "desc" FROM Problem WHERE id = ?', (p_id, )).fetchone()

def public_testcases(p_id: int, cur: sqlite3.Cursor | None = None) -> list[sqlite3.Row]:
    with contextlib.ExitStack() as sk:
        if cur is None:
            cur = global_db().cursor()
            sk.callback(cur.close)
        return cur.execute(r'SELECT test_no, "in", "out", "note" FROM Testcase WHERE problem_id = ? AND type = 0', (p_id, )).fetchall()
