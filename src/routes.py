import bcrypt
import functools
import secrets
import sqlite3

from typing import Callable, Any, Concatenate, Final, ParamSpec, Sequence
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
)
from flask.json import jsonify
from flask.typing import ResponseReturnValue, RouteCallable

from .db import (
    all_testcases,
    creds_of,
    get_category,
    get_cursor,
    get_problems,
    get_results,
    get_subs,
    get_tags_joined,
    get_userinfo,
    problem_info,
    public_testcases,
    register,
    submit,
    teardown,
)
from .validate import (
    ShowError,
    chk_int,
    chk_form,
    chk_json,
    chk_is_int,
    make_err,
)

P = ParamSpec('P')
FAILURE_JSON: Final = {'status': 'faiure', 'error': 'internal'}
FIELD_PASSED: Final = 'Local judge result'
FIELD_P_ID: Final = 'Problem ID'
FIELD_U: Final = 'User name'
FIELD_PW: Final = 'Password'
registry: list[tuple[RouteCallable, str, dict[str, Any]]] = []


# save route rule and callback into a registry for setting up the flask app
def deferred_route(rule: str, **opt) -> Callable[[RouteCallable], RouteCallable]:
    return lambda func: registry.append((func, rule, opt)) or func


def require_login(cb: Callable[Concatenate[int, P], ResponseReturnValue]) -> Callable[P, ResponseReturnValue]:
    """
    Marks a route as login-required.
    Precondition: route supports GET
    Guests will be redirected to /login with a redirect flag set
    """
    @functools.wraps(cb)
    def wrapped(*a: P.args, **kw: P.kwargs) -> ResponseReturnValue:
        if (u := session.get('u')) is not None:
            return cb(u, *a, **kw)
        session['redirect'] = request.full_path
        return redirect('/login?r=1')

    return wrapped


def json_api(fn: Callable[P, Any]) -> Callable[P, ResponseReturnValue]:
    @functools.wraps(fn)
    def wrapped(*a: P.args, **kw: P.kwargs):
        try:
            result = fn(*a, **kw)
        except ShowError as e:
            resp = {'status': 'failure'}
            if e.err_info is not None:
                resp['error'] = e.err_info
            return jsonify(resp), e.code
        except Exception as e:
            FAILURE_JSON['error'] = repr(e)
            return jsonify(FAILURE_JSON), 500
        else:
            return jsonify({'status': 'success', 'data': result}), 200

    return wrapped


def passrate(res: Sequence[sqlite3.Row]):
    """
    Returns the pass rate of a list of submissions, or N/A if unavailable.
    """
    passes = sum(x['result'] for x in res)
    submissions = len(res)
    try:
        return f'{passes / submissions * 100:.2f}%'
    except OverflowError, ZeroDivisionError:
        return 'N/A'


@deferred_route('/')
def _root():
    return render_template('index.html')


@deferred_route('/problems')
def _problems():
    with get_cursor() as c:
        problems = get_problems(cur=c)
        return render_template('problems.html', problems=({
            **problem,
            '__passrate': passrate(get_results(problem['id'], cur=c)),
        } for problem in problems))


@deferred_route('/problem/<int:p_id>')
def _problem(p_id: int):
    p_id = chk_int(p_id, FIELD_P_ID)
    with get_cursor() as c:
        tcs = (public_testcases if session.get(
            'u') is None else all_testcases)(p_id, cur=c)
        p = problem_info(p_id, cur=c)
        if p is None:
            raise ShowError(404, err_info=f'Problem {p_id} does not exist')
        return render_template(
            'problem.html',
            cat=get_category(p['cat_id'], cur=c),
            tags=get_tags_joined(p_id, cur=c),
            problem=p,
            testcases=tcs)


@deferred_route('/login', methods=('GET', 'POST'))
def _login():
    if 'u' not in session and request.method == 'POST':
        try:
            username = chk_form('u', FIELD_U, lb=1)
            passwd = chk_form('pw', FIELD_PW, lb=1)
        except ShowError as e:
            if e.err_info is not None:
                flash(e.err_info, 'login')
                return redirect('/login')
            raise

        if (r := creds_of(username)) and bcrypt.checkpw(
                passwd.encode(), r['pw_hash'].encode()):
            session['u'] = r['user_id']
        else:
            flash('Login incorrect', 'login')
            return redirect('/login')

    if 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    return render_template('login.html')


@deferred_route('/sign-up', methods=('GET', 'POST'))
def _sign_up():
    if request.method == 'POST':
        try:
            username = chk_form('u', FIELD_U)
            passwd = chk_form('pw', FIELD_PW)
            confirm = chk_form('pwa', 'Password confirmation')
        except ShowError as e:
            if e.err_info is not None:
                flash(e.err_info, 'signup')
                return redirect('/sign-up')
            raise
        if confirm != passwd:
            flash('Password confirmation incorrect', 'signup')
            return redirect('/sign-up')
        if creds_of(username):
            flash('Username already taken', 'signup')
            return redirect('/sign-up')
        register(username, bcrypt.hashpw(
            passwd.encode(), bcrypt.gensalt()).decode())
        return redirect('/login')
    elif 'u' in session:
        return redirect(session.pop('redirect', '/me') if request.args.get('r') else '/me')
    else:
        return render_template('sign-up.html')


@deferred_route('/me')
@require_login
def _me(user: int):
    with get_cursor() as c:
        subs = get_subs(user, cur=c)
        return render_template(
            'me.html',
            info=get_userinfo(user, cur=c),
            passrate=passrate(subs),
            attempted=set(x['problem_id'] for x in subs))


@deferred_route('/submit', methods=('POST', ))
@json_api
def _submit():
    if (user := session.get('u')) is None:
        raise ShowError(403, err_info='Login required')
    if not request.is_json:
        raise ShowError(400, err_info='POST request not in JSON format')
    passed = chk_int(
        chk_is_int(chk_json('pass'), name=FIELD_PASSED),
        name=FIELD_PASSED, ub=1)
    p_id = chk_int(
        chk_is_int(chk_json('problem'), name=FIELD_P_ID), name=FIELD_P_ID)
    with get_cursor() as c:
        if problem_info(p_id, cur=c) is None:
            raise ShowError(404, err_info=f'Problem {p_id} does not exist')
        submit(user, p_id, passed, cur=c)


@deferred_route('/logout', methods=('POST', ))
def _logout():
    if 'u' in session:
        del session['u']
    return redirect('/')


@deferred_route('/colour', methods=('POST', ))
def _colour():
    colour = request.form.get('colour')
    if not colour:
        raise ShowError(400, err_info='No colour set')
    if colour not in ('0', '1', '2'):
        raise ShowError(400, err_info='Invalid colour')
    session['colour'] = int(colour)
    return '', 204


def setup_flask() -> Flask:
    fapp = Flask('pywebjudge')
    fapp.secret_key = secrets.token_bytes(32)
    fapp.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    for func, rule, opt in registry:
        fapp.add_url_rule(rule, view_func=func, **opt)
    # teardown doesn't accept any arguments
    # use a lambda to work around it
    fapp.teardown_appcontext(lambda _: teardown())
    fapp.errorhandler(ShowError)(make_err)
    for code in (404, 500):
        fapp.errorhandler(code)(lambda e: make_err(ShowError(e.code)))
    return fapp
