import bcrypt
import functools
import secrets

from typing import Callable, Any
from flask import Flask, Response, redirect, render_template, request, session
from flask.typing import RouteCallable

from .db import creds_of, get_problems, problem_info, public_testcases, teardown

registry: list[tuple[RouteCallable, str, dict[str, Any]]] = []

def deferred_route(rule: str, **opt) -> Callable[[RouteCallable], RouteCallable]:
    return lambda func: registry.append((func, rule, opt)) or func

def require_login(cb: RouteCallable) -> RouteCallable:
    return functools.wraps(cb)(lambda *a, **k: cb(*a, **k) if 'u' in session else redirect('/login'))

@deferred_route('/')
def _root():
    return render_template('index.html')

@deferred_route('/problems')
def _problems():
    return render_template('problems.html', problems=get_problems())

@deferred_route('/problem/<int:p_id>')
def _problem(p_id: int):
    # TODO: shared cursor
    return render_template('problem.html', problem=problem_info(p_id), testcases=public_testcases(p_id))

@deferred_route('/login', methods=('GET', 'POST'))
def _login():
    if request.method == 'POST':
        pw = request.form.get('pw')
        u = request.form.get('u')
        if not pw or not u:
            return 'EXPECTED u AND pw IN POST REQUEST'

        if (r := creds_of(u)) and bcrypt.checkpw(pw.encode(), r['pw_hash'].encode()):
            session['u'] = u
        else:
            return 'INCORRECT LOGIN'

    if session.get('u'):
        return redirect('/me')
    return render_template('login.html')

@deferred_route('/me')
@require_login
def _me():
    return str(session['u'])

@deferred_route('/logout')
def _logout():
    if session.get('u'):
        del session['u']
    return Response(status=204)

def setup_flask(fapp: Flask):
    fapp.secret_key = secrets.token_bytes(32)
    for func, rule, opt in registry:
        fapp.add_url_rule(rule, view_func=func, **opt)
    fapp.teardown_request(lambda _: teardown())

