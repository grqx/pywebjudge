# TODO: flash error
import bcrypt
import functools
import secrets

from typing import Callable, Any, Concatenate, ParamSpec
from flask import Flask, redirect, render_template, request, session
from flask.typing import ResponseReturnValue, RouteCallable

from .db import creds_of, get_cursor, get_problems, problem_info, public_testcases, register, teardown

P = ParamSpec('P')
registry: list[tuple[RouteCallable, str, dict[str, Any]]] = []

def deferred_route(rule: str, **opt) -> Callable[[RouteCallable], RouteCallable]:
    return lambda func: registry.append((func, rule, opt)) or func

def require_login(cb: Callable[Concatenate[int, P], ResponseReturnValue]) -> Callable[P, ResponseReturnValue]:
    @functools.wraps(cb)
    def wrapped(*a: P.args, **kw: P.kwargs) -> ResponseReturnValue:
        if (u := session.get('u')) is not None:
            return cb(u, *a, **kw)
        session['redirect'] = request.full_path
        return redirect('/login?r=1')

    return wrapped

@deferred_route('/')
def _root():
    return render_template('index.html', u=session.get('u'))

@deferred_route('/problems')
def _problems():
    return render_template('problems.html', problems=get_problems(), u=session.get('u'))

@deferred_route('/problem/<int:p_id>')
def _problem(p_id: int):
    with get_cursor() as c:
        return render_template(
            'problem.html',
            problem=problem_info(p_id, cur=c),
            testcases=public_testcases(p_id, cur=c),
            u=session.get('u'))

@deferred_route('/login', methods=('GET', 'POST'))
def _login():
    if 'u' not in session and request.method == 'POST':
        pw = request.form.get('pw')
        u = request.form.get('u')
        if not pw or not u:
            return 'EXPECTED u AND pw IN POST REQUEST'

        if (r := creds_of(u)) and bcrypt.checkpw(pw.encode(), r['pw_hash'].encode()):
            session['u'] = r['user_id']
        else:
            return 'INCORRECT LOGIN'

    if 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    return render_template('login.html')

@deferred_route('/sign-up', methods=('GET', 'POST'))
def _sign_up():
    if 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    if request.method == 'POST':
        pw = request.form.get('pw')
        pwa = request.form.get('pwa')
        u = request.form.get('u')
        if not pwa or not pw or not u:
            return 'EXPECTED u AND pw AND pwa IN POST REQUEST'

        if pwa != pw:
            return 'pwa INCORRECT'

        if creds_of(u):
            return 'u ALREADY EXISTS'
        register(u, bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        return 'DONE'
    return render_template('sign-up.html')

@deferred_route('/me')
@require_login
def _me(user: int):
    return str(user)

@deferred_route('/logout')
def _logout():
    if 'u' in session:
        del session['u']
    return redirect('/')

def setup_flask(fapp: Flask):
    fapp.secret_key = secrets.token_bytes(32)
    fapp.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    for func, rule, opt in registry:
        fapp.add_url_rule(rule, view_func=func, **opt)
    fapp.teardown_request(lambda _: teardown())

