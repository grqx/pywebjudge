import bcrypt
import sqlite3
import functools
import secrets

from typing import Callable, Any, Concatenate, ParamSpec, Sequence
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
    get_category,
    get_cursor,
    get_problems,
    get_results,
    get_subs,
    get_tags,
    get_userinfo,
    get_tag,
    problem_info,
    public_testcases,
    register,
    submit,
    teardown,
)

P = ParamSpec('P')
registry: list[tuple[RouteCallable, str, dict[str, Any]]] = []


# save route rule and callback into a registry for setting up the flask app
def deferred_route(rule: str, **opt) -> Callable[[RouteCallable], RouteCallable]:
    return lambda func: registry.append((func, rule, opt)) or func


# marks a route as login-required. Guests will be redirected to /login with a redirect flag set
def require_login(cb: Callable[Concatenate[int, P], ResponseReturnValue]) -> Callable[P, ResponseReturnValue]:
    @functools.wraps(cb)
    def wrapped(*a: P.args, **kw: P.kwargs) -> ResponseReturnValue:
        if (u := session.get('u')) is not None:
            return cb(u, *a, **kw)
        session['redirect'] = request.full_path
        return redirect('/login?r=1')

    return wrapped


# calculate the pass rate of a list of submissions, N/A if divided by zero
def passrate(res: Sequence[sqlite3.Row]):
    passes = sum(x['result'] for x in res)
    submissions = len(res)
    try:
        return f'{passes / submissions * 100:.2f}%'
    except OverflowError, ZeroDivisionError:
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
        p = problem_info(p_id, cur=c)
        return render_template(
            'problem.html',
            cat=get_category(p['cat_id'], cur=c),
            # use list comprehension instead of generator expression here
            # otherwise it would result in UAF of the cursor
            tags=[get_tag(tag['tag_id'], cur=c)['name'] for tag in get_tags(p_id, cur=c)],
            problem=p,
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
        if not pw:
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
        confirm = request.form.get('pwa')
        u = request.form.get('u')
        # loop through to reduce code duplication
        for formvar, name in ((u, 'Username'), (pw, 'Password'), (confirm, 'Password confirmation')):
            if not formvar:
                flash(f'{name} empty', 'signup')
                return redirect('/sign-up')
            if len(formvar) < 5:
                flash(f'{name} too short', 'signup')
                return redirect('/sign-up')
            if len(formvar) > 64:
                flash(f'{name} too long', 'signup')
                return redirect('/sign-up')
        # make the type checker happy
        assert u and confirm and pw
        if confirm != pw:
            flash('Password confirmation incorrect', 'signup')
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
    # teardown doesn't accept any arguments
    # use a lambda to work around it
    fapp.teardown_appcontext(lambda _: teardown())
