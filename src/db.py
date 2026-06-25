import contextlib
import os
import sqlite3
import threading
from typing import Callable, Concatenate, ParamSpec, TypeVar

P = ParamSpec('P')
T = TypeVar('T')

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

def opt_cursor(fn: Callable[Concatenate[sqlite3.Cursor, P], T]):
    def inner(*a, cur: OptCursor = None, **kw) -> T:
        with get_cursor(cur) as c:
            return fn(c, *a, **kw)

    return inner

@opt_cursor
def get_problems(c: sqlite3.Cursor) -> list[sqlite3.Row]:
    return c.execute(r'SELECT id, title FROM Problem').fetchall()

@opt_cursor
def problem_info(c: sqlite3.Cursor, p_id: int) -> sqlite3.Row | None:
    return c.execute(r'SELECT id, title, "desc" FROM Problem WHERE id = ?', (p_id, )).fetchone()

@opt_cursor
def public_testcases(c: sqlite3.Cursor, p_id: int) -> list[sqlite3.Row]:
    return c.execute(r'SELECT test_no, "in", "out", "note" FROM Testcase WHERE problem_id = ? AND type = 0', (p_id, )).fetchall()

@opt_cursor
def creds_of(c: sqlite3.Cursor, u_name: str) -> sqlite3.Row | None:
    return c.execute(r'SELECT user_id, pw_hash, privilege_lvl FROM User WHERE name = ?', (u_name, )).fetchone()

@opt_cursor
def register(c: sqlite3.Cursor, u_name: str, pw_hash: str) -> None:
    c.execute(r'INSERT INTO User (name, pw_hash, privilege_lvl) VALUES (?, ?, 1)', (u_name, pw_hash))
    c.connection.commit()
