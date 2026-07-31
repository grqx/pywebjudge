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
)

P = ParamSpec('P')
T = TypeVar('T')
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

class Decorated(Protocol[P, Tc]):
    @staticmethod
    def __call__(*a: P.args, **k: P.kwargs) -> Tc: ...
    mode: Literal['fetchall'] | Literal['fetchone'] | None

def db_util(query: LiteralString):
    def wrapper(fn: Decorated[P, T]) -> Callable[P, T]:
        def inner(*a: P.args, **k: P.kwargs) -> T:
            cur = cast(OptCursor, k.pop('cur', None))
            if k:
                raise TypeError('kwargs other than "cur" are not allowed on db utils')
            with get_cursor(cur) as c:
                res = c.execute(query, a)
                if fn.mode is not None:
                    return cast(T, getattr(res, fn.mode)())
                c.connection.commit()
                return cast(T, None)
        return inner
    return wrapper

FetchManyRet = list[sqlite3.Row]
FetchOneRet = sqlite3.Row | None

def fm_all(fn: Callable[P, T]) -> Decorated[P, FetchManyRet]:
    ret = cast(Decorated[P, FetchManyRet], fn)
    ret.mode = 'fetchall'
    return ret

def fm_one(fn: Callable[P, T]) -> Decorated[P, FetchOneRet]:
    ret = cast(Decorated[P, FetchOneRet], fn)
    ret.mode = 'fetchone'
    return ret

def fm_commit(fn: Callable[P, T]) -> Decorated[P, None]:
    ret = cast(Decorated[P, None], fn)
    ret.mode = None
    return ret

@db_util(r'SELECT id, title FROM Problem')
@fm_all
def get_problems(*, cur: OptCursor = None): ...

@db_util(r'SELECT id, title, "desc" FROM Problem WHERE id = ?')
@fm_one
def problem_info(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT test_no, "in", "out", "note" FROM Testcase WHERE problem_id = ? AND type = 0')
@fm_all
def public_testcases(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT user_id, pw_hash, privilege_lvl FROM User WHERE name = ?')
@fm_one
def creds_of(u_name: str, *, cur: OptCursor = None): ...

@db_util(r'INSERT INTO User (name, pw_hash, privilege_lvl) VALUES (?, ?, 1)')
@fm_commit
def register(u_name: str, pw_hash: str, *, cur: OptCursor = None): ...

@db_util(r'INSERT INTO Submission (user_id, problem_id, result) VALUES (?, ?, ?)')
@fm_commit
def submit(u_id: int, p_id: int, result: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT problem_id, result FROM Submission WHERE user_id = ?')
@fm_all
def get_subs(u_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT result FROM Submission WHERE problem_id = ?')
@fm_all
def get_results(p_id: int, *, cur: OptCursor = None): ...

@db_util(r'SELECT name FROM User WHERE user_id = ?')
@fm_one
def get_userinfo(u_id: int, *, cur: OptCursor = None): ...
