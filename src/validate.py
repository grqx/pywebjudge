"""A module with various utilities to validate untrusted user input."""
import dataclasses
import http

from typing import Any
from flask import request, render_template
from flask.typing import ResponseReturnValue


@dataclasses.dataclass(slots=True)
class ShowError(Exception):
    """An exception subclass raised on invalid input."""
    code: int
    reason: str | None = None
    err_info: str | None = None


def make_err(err: ShowError) -> ResponseReturnValue:
    """Render an error page according to a ShowError instance."""
    code = err.code
    err_info = err.err_info
    reason = err.reason
    try:
        status = http.HTTPStatus(code)
    except ValueError:
        phrase, info = None, None
    else:
        phrase = status.phrase
        info = status.description

    if reason is None:
        reason = phrase
    if err_info is None:
        err_info = info
    rp = str(code)
    if reason is not None:
        rp += f': {reason}'
    return (
        render_template(
            'error.html',
            errc=code, rp=rp, err_info=err_info),
        code,
    )


def chk_int(x: Any, name: str, lb=0, ub=2147483647) -> int:
    """Checks if an integer is within its expected bounds (inclusive).
    Raises ShowError 400 with appropriate err_info when it's
    out-of-bound.
    """
    if x > ub:
        raise ShowError(400, err_info=f'{name} {x} too large')
    if x < lb:
        raise ShowError(400, err_info=f'{name} {x} too small')
    return x


def chk_form(key: str, name: str, lb=5, ub=64) -> str:
    """Gets a key from request.form, validating its length (inclusive).
    Precondition: the current request is a POST request.
    Raises ShowError 400 with appropriate err_info on invalid requests.
    """
    s = request.form.get(key)
    if s is None:
        raise ShowError(400, err_info=f'{key!r} absent from form')
    if len(s) > ub:
        raise ShowError(400, err_info=f'{name} too long')
    if len(s) < lb:
        raise ShowError(400, err_info=f'{name} too short')
    return s


def chk_json(key: str) -> str:
    """
    Gets a key from request.json
    Precondition: the current request is a json POST request
    Raises ShowError 400 with appropriate err_info on invalid requests.
    """
    s = request.json.get(key)
    if s is None:
        raise ShowError(400, err_info=f'{key!r} absent from JSON request')
    return s


def chk_is_int(x: Any, name: str) -> int:
    """Checks whether a value is an int."""
    if isinstance(x, int):
        return x
    raise ShowError(400, err_info=f'{name} should be an int')
