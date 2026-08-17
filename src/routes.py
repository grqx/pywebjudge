import bcrypt
import functools
import secrets

from typing import Callable, Any, Concatenate, ParamSpec
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
)
from flask.typing import ResponseReturnValue, RouteCallable

from .db import (
    all_testcases,
    creds_of,
    get_cursor,
    get_problems,
    get_results,
    get_subs,
    get_userinfo,
    problem_info,
    public_testcases,
    register,
    submit,
    teardown,
)

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


def passrate(res):
    passes = sum(x['result'] for x in res)
    submissions = len(res)
    try:
        return f'{passes / submissions * 100:.2f}%'
    except ZeroDivisionError:
        return 'N/A'


@deferred_route('/')
def _root():
    return render_template('index.html', u=session.get('u'))


@deferred_route('/problems')
def _problems():
    with get_cursor() as c:
        problems = get_problems(cur=c)
        return render_template('problems.html', problems=({
            **problem,
            '__passrate': passrate(get_results(problem['id'], cur=c)),
        } for problem in problems), u=session.get('u'))


@deferred_route('/problem/<int:p_id>')
def _problem(p_id: int):
    with get_cursor() as c:
        get_tc = public_testcases if session.get(
            'u') is None else all_testcases
        return render_template(
            'problem.html',
            problem=problem_info(p_id, cur=c),
            testcases=get_tc(p_id, cur=c),
            u=session.get('u'))


@deferred_route('/login', methods=('GET', 'POST'))
def _login():
    if 'u' not in session and request.method == 'POST':
        pw = request.form.get('pw')
        u = request.form.get('u')
        if not u:
            flash('Username empty', 'login')
            return redirect('/login')
        if not pw or not u:
            flash('Password empty', 'login')
            return redirect('/login')

        if (r := creds_of(u)) and bcrypt.checkpw(pw.encode(), r['pw_hash'].encode()):
            session['u'] = r['user_id']
        else:
            flash('Login incorrect', 'login')
            return redirect('/login')

    if 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    return render_template('login.html', u=session.get('u'))


@deferred_route('/sign-up', methods=('GET', 'POST'))
def _sign_up():
    if 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    if request.method == 'POST':
        pw = request.form.get('pw')
        pwa = request.form.get('pwa')
        u = request.form.get('u')
        if not pwa:
            flash('Password confirmation empty', 'signup')
            return redirect('/sign-up')
        if not pw:
            flash('Password empty', 'signup')
            return redirect('/sign-up')
        if not u:
            flash('Username empty', 'signup')
            return redirect('/sign-up')
        if pwa != pw:
            flash('Password confirmation empty', 'signup')
            return redirect('/sign-up')
        if len(u) < 5:
            flash('Username too short', 'signup')
            return redirect('/sign-up')
        if len(pw) < 5:
            flash('Password too short', 'signup')
            return redirect('/sign-up')
        if creds_of(u):
            flash('Username already taken', 'signup')
            return redirect('/sign-up')
        register(u, bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
        return redirect('/login')
    return render_template('sign-up.html', u=session.get('u'))


@deferred_route('/me')
@require_login
def _me(user: int):
    with get_cursor() as c:
        subs = get_subs(user, cur=c)
        return render_template(
            'me.html',
            info=get_userinfo(user, cur=c),
            passrate=passrate(subs),
            attempted=set(x['problem_id'] for x in subs),
            u=user)


@deferred_route('/submit', methods=('POST', ))
@require_login
def _submit(user: int):
    passed = int(request.json['pass'])
    p_id = int(request.json['problem'])
    submit(user, p_id, 1 if passed else 0)
    return ''


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
