from typing import Callable
from flask import Flask, render_template
from flask.typing import RouteCallable

from .db import get_problems, problem_info, public_testcases, teardown

registry: list[tuple[RouteCallable, str]] = []

def deferred_route(rule: str) -> Callable[[RouteCallable], RouteCallable]:
    return lambda func: registry.append((func, rule)) or func

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

def setup_flask_routes(fapp: Flask):
    for func, rule in registry:
        fapp.add_url_rule(rule, view_func=func)
    fapp.teardown_request(lambda x: teardown())

