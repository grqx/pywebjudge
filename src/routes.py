"""The core of the web application. This module defines the routes and
is responsible for creating the flask instance at runtime.
"""
import functools
import secrets
import sqlite3
import types
from typing import Callable, Any, Concatenate, Final, ParamSpec, Sequence

import bcrypt
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
FAILURE_JSON: Final = types.MappingProxyType({
    'status': 'failure',
    'error': 'internal',
})
FIELD_PASSED: Final = 'Local judge result'
FIELD_P_ID: Final = 'Problem ID'
FIELD_U: Final = 'User name'
FIELD_PW: Final = 'Password'
registry: list[tuple[RouteCallable, str, dict[str, Any]]] = []


def deferred_route(
    rule: str,
    **opt,
) -> Callable[[RouteCallable], RouteCallable]:
    """Save route rule and callback into a registry for setting up the
    flask app later.
    """
    return lambda func: registry.append((func, rule, opt)) or func


def require_login(
    cb: Callable[Concatenate[int, P], ResponseReturnValue],
) -> Callable[P, ResponseReturnValue]:
    """Marks a route as login-required.
    Precondition: route supports GET
    Guests will be redirected to /login with a redirect flag set.
    """
    @functools.wraps(cb)
    def wrapped(*a: P.args, **kw: P.kwargs) -> ResponseReturnValue:
        if (u := session.get('u')) is not None:
            return cb(u, *a, **kw)
        session['redirect'] = request.full_path
        return redirect('/login?r=1')

    return wrapped


def json_api(fn: Callable[P, Any]) -> Callable[P, ResponseReturnValue]:
    """A decorator that wraps a route so that it always returns data in
    json format, even when an exception is thrown (ShowError is handled
    specially).
    """
    @functools.wraps(fn)
    def wrapped(*a: P.args, **kw: P.kwargs):
        try:
            result = fn(*a, **kw)
        except ShowError as e:
            resp = FAILURE_JSON.copy()
            if e.err_info is not None:
                resp['error'] = e.err_info
            return jsonify(resp), e.code
        except Exception:  # pylint: disable=broad-exception-caught
            return jsonify(FAILURE_JSON), 500
        return jsonify({'status': 'success', 'data': result}), 200

    return wrapped


def passrate(res: Sequence[sqlite3.Row]):
    """Returns the pass rate of a list of submissions, or 'N/A' if it
    could not be calculated. (e.g. there are no submissions at all)
    """
    passes = sum(x['result'] for x in res)
    submissions = len(res)
    try:
        return f'{passes / submissions * 100:.2f}%'
    except (OverflowError, ZeroDivisionError):
        return 'N/A'


@deferred_route('/')
def _root():
    return render_template('index.html')


@deferred_route('/problems')
def _problems():
    with get_cursor() as c:  # Close the cursor on exit.
        problems = get_problems(cur=c)
        return render_template('problems.html', problems=({
            **problem,
            # Smuggle the pass rate in.
            '__passrate': passrate(get_results(problem['id'], cur=c)),
        } for problem in problems))


@deferred_route('/problem/<int:p_id>')
def _problem(p_id: int):
    p_id = chk_int(p_id, FIELD_P_ID)
    with get_cursor() as c:  # Scoped cursor.
        tcs = (public_testcases if session.get(
            'u') is None else all_testcases)(p_id, cur=c)
        p = problem_info(p_id, cur=c)
        if p is None:  # We can't find the problem, so return 404.
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
            # Catch the validation error raised by chk_form and turn it
            # into a flash message.
            if e.err_info is not None:
                flash(e.err_info, 'login')
                return redirect('/login')
            # chk_form should only raise an error with err_info. Reraise
            # otherwise because it isn't really supposed to happen.
            raise

        if (r := creds_of(username)) and bcrypt.checkpw(
                passwd.encode(), r['pw_hash'].encode()):
            session['u'] = r['user_id']
        else:
            # Incorrect user/password lead to the same error message.
            # This makes guessing usernames/passwords harder.
            flash('Login incorrect', 'login')
            return redirect('/login')

    # Redirect if logged-in, no matter which http method is being used.
    # 'u' should already be set in the above block if it's POST.
    if 'u' in session:
        return redirect(
            session.pop('redirect', '/me') if request.args.get('r') else '/me')
    # This is only triggered when request.method == 'GET' and 'u' is not
    # in session (we only send the login template in this case).
    return render_template('login.html')


@deferred_route('/sign-up', methods=('GET', 'POST'))
def _sign_up():
    if request.method == 'POST':
        try:
            username = chk_form('u', FIELD_U)
            passwd = chk_form('pw', FIELD_PW)
            # Do the field name inline because it isn't referenced
            # anywhere else (i.e. only the sign-up route confirms
            # the password).
            confirm = chk_form('pwa', 'Password confirmation')
        except ShowError as e:
            if e.err_info is not None:
                # Same as above, except we use the 'signup' category
                # instead. Separate error categories so that GETting
                # /login right after POSTing /sign-up shouldn't give an
                # unrelated message.
                flash(e.err_info, 'signup')
                return redirect('/sign-up')
            raise
        if confirm != passwd:
            # Verify password confirmation to eliminate user error.
            flash('Password confirmation incorrect', 'signup')
            return redirect('/sign-up')
        if creds_of(username):  # Another user of the same name exists.
            flash('Username already taken', 'signup')
            return redirect('/sign-up')
        register(username, bcrypt.hashpw(
            passwd.encode(), bcrypt.gensalt()).decode())
        # NOTE: /sign-up doesn't set 'u'. This is deliberate.
        return redirect('/login')
    if 'u' in session:
        # Redirect only if reaching via GET and the user is already
        # logged-in.
        return redirect(
            session.pop('redirect', '/me') if request.args.get('r') else '/me')
    # If GET, and not logged-in already.
    return render_template('sign-up.html')


@deferred_route('/me')
@require_login
def _me(user: int):
    # Get the cursor as it's used more than once.
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
    # manually require login, becuase we don't want require_login's
    # automatic redirection. If the user tries to access the endpoint as
    # a guest, we return a 403.
    if (user := session.get('u')) is None:
        raise ShowError(403, err_info='Login required')
    # The request might not be in json.
    if not request.is_json:
        raise ShowError(400, err_info='POST request not in JSON format')
    # The upper bound is set to 1 so that only 0 and 1 are valid values.
    passed = chk_int(
        chk_is_int(chk_json('pass'), name=FIELD_PASSED),
        name=FIELD_PASSED, ub=1)
    # We don't set a upper bound here, though it must not be negative as
    # chk_int's default lower bound is 0 (inclusive).
    p_id = chk_int(
        chk_is_int(chk_json('problem'), name=FIELD_P_ID), name=FIELD_P_ID)
    with get_cursor() as c:
        # Again, we are using the cursor multiple times.
        if problem_info(p_id, cur=c) is None:
            raise ShowError(404, err_info=f'Problem {p_id} does not exist')
        submit(user, p_id, passed, cur=c)


@deferred_route('/logout', methods=('POST', ))
def _logout():
    # Simply delete 'u' from this session.
    if 'u' in session:
        del session['u']
    # We can't return a 204 here because that way the "log out" button
    # remains on the page. Redirect to force re-rendering.
    return redirect('/')


@deferred_route('/colour', methods=('POST', ))
def _colour():
    # set the user's preferred colour scheme.
    colour = request.form.get('colour')
    if not colour:
        raise ShowError(400, err_info='No colour set')
    if colour not in ('0', '1', '2'):
        raise ShowError(400, err_info='Invalid colour')
    # Session var 'colour' is referenced in template files. It must be
    # an int. The conversion here shouldn't fail, as colour is limited
    # to Literal['0'] | Literal['1'] | Literal['2'].
    session['colour'] = int(colour)
    return '', 204


def setup_flask() -> Flask:
    """A factory function for flask apps. Applies some basic settings
    and adds the routes to it.
    """
    fapp = Flask('pywebjudge')
    # Done for security purposes.
    fapp.secret_key = secrets.token_bytes(32)
    fapp.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Apply the registry to the app.
    for func, rule, opt in registry:
        fapp.add_url_rule(rule, view_func=func, **opt)
    # Remember to close the database! teardown doesn't accept any
    # arguments so we use a lambda to work around it.
    fapp.teardown_appcontext(lambda _: teardown())
    # If we'd thrown a ShowError ourselves
    fapp.errorhandler(ShowError)(make_err)
    # We catch 404 (usually missing route)
    # and 500 (usually python exception)
    for code in (404, 500):
        fapp.errorhandler(code)(lambda e: make_err(ShowError(e.code)))
    return fapp
