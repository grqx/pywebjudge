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

OptCursor = sqlite3.Cursor | None

@contextlib.contextmanager
def get_cursor(cur: OptCursor = None):
    if cur is not None:
        yield cur
        return
    cur = global_db().cursor()
    try:
        yield cur
    finally:
        cur.close()

def get_problems(cur: OptCursor = None) -> list[sqlite3.Row]:
    with get_cursor(cur) as c:
        return c.execute(r'SELECT id, title FROM Problem').fetchall()

def problem_info(p_id: int, cur: OptCursor = None) -> sqlite3.Row | None:
    with get_cursor(cur) as c:
        return c.execute(r'SELECT id, title, "desc" FROM Problem WHERE id = ?', (p_id, )).fetchone()

def public_testcases(p_id: int, cur: OptCursor = None) -> list[sqlite3.Row]:
    with get_cursor(cur) as c:
        return c.execute(r'SELECT test_no, "in", "out", "note" FROM Testcase WHERE problem_id = ? AND type = 0', (p_id, )).fetchall()

def creds_of(u_name: str, cur: OptCursor = None) -> sqlite3.Row | None:
    with get_cursor(cur) as c:
        return c.execute(r'SELECT user_id, pw_hash, privilege_lvl FROM User WHERE name = ?', (u_name, )).fetchone()
