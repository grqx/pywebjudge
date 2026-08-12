import contextlib
import os
import sqlite3
import threading
from typing import (
    Callable,
    Literal,
    LiteralString,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
    overload,
)

P = ParamSpec('P')
Tc = TypeVar('Tc', covariant=True)

storage = threading.local()

def global_db() -> sqlite3.Connection:
    if (db := getattr(storage, 'db', None)) is None:
        setattr(storage, 'db', db := sqlite3.connect(os.path.abspath(os.path.join(
                __file__, os.pardir, os.pardir, 'app.db'))))
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

FetchManyRet = list[sqlite3.Row]
FetchOneRet = sqlite3.Row | None
DBRet = FetchManyRet | FetchOneRet | None

class Decorator(Protocol[Tc]):
    @staticmethod
    def __call__(cb: Callable[P, None], /) -> Callable[P, Tc]: ...

@overload
def db_util(query: LiteralString) -> Decorator[None]: ...
@overload
def db_util(query: LiteralString, mode: Literal['all']) -> Decorator[FetchManyRet]: ...
@overload
def db_util(query: LiteralString, mode: Literal['one']) -> Decorator[FetchOneRet]: ...

def db_util(query: LiteralString, mode: Literal['all'] | Literal['one'] | None = None) -> Decorator[DBRet]:
    def wrapper(_: Callable[P, None]) -> Callable[P, DBRet]:
        def inner(*a: P.args, **k: P.kwargs) -> DBRet:
            cur = cast(OptCursor, k.pop('cur', None))
            if k:
                raise TypeError('kwargs other than "cur" are not allowed on db utils')
            with get_cursor(cur) as c:
                res = c.execute(query, a)
                if mode is None:
                    c.connection.commit()
                    return None
                return cast(DBRet, res.fetchall() if mode == 'all' else res.fetchone())
        return inner
    return wrapper

@db_util(r'SELECT id, title FROM Problem', 'all')
def get_problems(*, cur: OptCursor = None): ...

@db_util(r'SELECT id, title, "desc" FROM Problem WHERE id = ?', 'one')
def problem_info(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT test_no, "in", "out", "note" FROM Testcase WHERE problem_id = ? AND type = 0', 'all')
def public_testcases(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT user_id, pw_hash, privilege_lvl FROM User WHERE name = ?', 'one')
def creds_of(u_name: str, *, cur: OptCursor = None): ...

@db_util(r'INSERT INTO User (name, pw_hash, privilege_lvl) VALUES (?, ?, 1)')
def register(u_name: str, pw_hash: str, *, cur: OptCursor = None): ...

@db_util(r'INSERT INTO Submission (user_id, problem_id, result) VALUES (?, ?, ?)')
def submit(u_id: int, p_id: int, result: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT problem_id, result FROM Submission WHERE user_id = ?', 'all')
def get_subs(u_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT result FROM Submission WHERE problem_id = ?', 'all')
def get_results(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT name FROM User WHERE user_id = ?', 'one')
def get_userinfo(u_id: int, *, cur: OptCursor = None): ...
