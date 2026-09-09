"""Utility functions helpful for testing."""
import contextlib

from typing import Generator
from src.db import DB_CFG


@contextlib.contextmanager
def db_test() -> Generator[None, None, None]:
    """A context manager that changes the web app's backend to use an
    in-memory sqlite3 database (per thread) over its lifetime. This
    might not be the intended behaviour when running on multiple
    threads.
    """
    old_path = DB_CFG['path']
    DB_CFG['path'] = None
    try:
        yield
    finally:
        DB_CFG['path'] = old_path
