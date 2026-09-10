"""This module provides utilities related to a sqlite3 database and
stores the structure of the database in the form of the SQL queries that
the application uses at runtime. The connection to the database is
thread-local. The teardown function should be called for each thread
calling global_db().
"""
import contextlib
import os
import sqlite3
import threading
from typing import (
    Any,
    Literal,
    LiteralString,
    ParamSpec,
    TypeVar,
    cast,
)

P = ParamSpec('P')
T_co = TypeVar('T_co', covariant=True)

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
DB_CFG: dict[Literal['path'], str | None] = {
    'path': os.path.join(PROJECT_ROOT, 'app.db'),
}
storage = threading.local()


def global_db() -> sqlite3.Connection:
    """Thread-local singleton database connection getter."""
    # Use getattr to work around pyright's type check.
    if (db := getattr(storage, 'db', None)) is None:
        path = DB_CFG['path']
        if path is None:  # For testing.
            db = sqlite3.connect(':memory:')
            # We require that these files be present when running tests.
            # Note that the order of them matters.
            for sql in 'create.sql', 'insert.sql':
                with open(
                    os.path.join(PROJECT_ROOT, sql),
                    encoding='utf-8'
                ) as f:
                    db.executescript(f.read())
        else:
            # Normally, we just need to connect to the file on disk.
            db = sqlite3.connect(path)
        # The other parts of this project relies on this.
        db.row_factory = sqlite3.Row
        setattr(storage, 'db', db)
    return db


def teardown():
    """Gracefully shuts down the database connection of the current
    thread.
    """
    # Use getattr to work around pyright's type check.
    if (db := getattr(storage, 'db', None)) is not None:
        db.close()
        # Delete to avoid UAF.
        delattr(storage, 'db')


OptCursor = sqlite3.Cursor | None


@contextlib.contextmanager
def get_cursor(cur: OptCursor = None):
    """Grab a new cursor if cur is None, and gracefully close it as soon
    as the context manager is exited.
    """
    if cur is not None:
        # If we already have a cursor, just yield it and return early.
        yield cur
        return
    # Otherwise, get a new cursor.
    cur = global_db().cursor()
    try:
        yield cur
    finally:
        # We want to close this no matter what exception occurs.
        cur.close()


def db_util(
    query: LiteralString,
    mode: Literal['all'] | Literal['one'] | None = None,
) -> Any:
    """Generate a db_util function."""
    def inner(*a: Any, **k: Any) -> Any:
        cur = cast(OptCursor, k.pop('cur', None))
        # cur is popped so there shouldn't be anything left in k.
        if k:
            raise TypeError(
                'only "cur" is allowed in the db_util kwargs')
        with get_cursor(cur) as c:
            res = c.execute(query, a)
            if mode is None:
                # This is for insertion and update queries. In this
                # case, we need to commit the changes and return
                # nothing, as we don't depend on the inserted row.
                c.connection.commit()
                return None
            # Make the type checker happy.
            return res.fetchall() if mode == 'all' else res.fetchone()
    return inner


get_problems = db_util(r'SELECT id, title FROM Problem', 'all')


problem_info = db_util(r'SELECT id, title, "desc", cat_id FROM Problem WHERE id = ?', 'one')


get_category = db_util(r'SELECT name FROM Category WHERE id = ?', 'one')


# Use JOIN to efficiently query a Many2Many table
get_tags_joined = db_util(
    r"""
    SELECT Tag.name
    FROM Tag
    JOIN Problems2tags ON Tag.id = Problems2tags.tag_id
    WHERE problem_id = ?
    """,
    'all')


public_testcases = db_util(
    r"""
    SELECT type, test_no, "in", "out", "note"
    FROM Testcase
    WHERE problem_id = ? AND type = 0
    """,
    'all')


all_testcases = db_util(
    r"""
    SELECT type, test_no, "in", "out", "note"
    FROM Testcase
    WHERE problem_id = ?
    """,
    'all')


creds_of = db_util(
    r"""
    SELECT user_id, pw_hash, privilege_lvl
    FROM User
    WHERE name = ?
    """,
    'one')


register = db_util(r'INSERT INTO User (name, pw_hash, privilege_lvl) VALUES (?, ?, 1)')


submit = db_util(
    r"""
    INSERT INTO Submission (user_id, problem_id, result)
    VALUES (?, ?, ?)
    """)


get_subs = db_util(r'SELECT problem_id, result FROM Submission WHERE user_id = ?', 'all')


get_results = db_util(r'SELECT result FROM Submission WHERE problem_id = ?', 'all')


get_userinfo = db_util(r'SELECT name FROM User WHERE user_id = ?', 'one')
