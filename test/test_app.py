import flask
import flask.testing
import re
import unittest

from typing import Final
from src.routes import setup_flask
from src.db import db_util, creds_of


def find_err_info(html: str):
    mobj = re.search(r'<hr/?>\s*<p>\s*(?P<info>[^<]*)\s*</p>', html)
    if mobj is None:
        return None
    return mobj.group('info')


class TestFlaskApp(unittest.TestCase):
    USER_NAME: Final = 'random user'
    PASSWD: Final = 'qwerty'
    app: flask.Flask
    clnt: flask.testing.FlaskClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = setup_flask()
        cls.app.config['TESTING'] = True
        cls.clnt = cls.enterClassContext(cls.app.test_client())

    @classmethod
    def tearDownClass(cls) -> None:
        db_util(r'DELETE FROM Submission WHERE user_id = 0 AND problem_id = 2')(
            lambda: None)()

    def test_colour(self) -> None:
        with self.clnt.session_transaction() as sess:
            if 'colour' in sess:
                del sess['colour']
        for i in range(3):
            resp = self.clnt.post('/colour', data={'colour': str(i)})
            self.assertEqual(resp.status_code, 204)
            self.assertEqual(resp.text, '')
            self.assertIn('colour', flask.session)
            self.assertEqual(flask.session['colour'], i)

    def test_colour_err(self) -> None:
        resp = self.clnt.post('/colour', data={'colour': '3'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(find_err_info(resp.text), 'Invalid colour')
        resp = self.clnt.post('/colour', data={'colour': 'pig'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(find_err_info(resp.text), 'Invalid colour')
        resp = self.clnt.post('/colour', data={})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(find_err_info(resp.text), 'No colour set')
        resp = self.clnt.post('/colour', data={'asdf': 3})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(find_err_info(resp.text), 'No colour set')

    def test_logout(self) -> None:
        with self.clnt.session_transaction() as sess:
            if 'u' in sess:
                del sess['u']
        resp = self.clnt.post('/logout')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location, '/')

        with self.clnt.session_transaction() as sess:
            sess['u'] = 0
        resp = self.clnt.post('/logout')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location, '/')
        self.assertNotIn('u', flask.session)

    def test_submit(self) -> None:
        def do_test(passv):
            resp = self.clnt.post('/submit', json={
                'pass': passv,
                'problem': 2,
            })
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.is_json)
            self.assertEqual(resp.json, {
                'status': 'success',
                'data': None,
            })

        with self.clnt.session_transaction() as sess:
            sess['u'] = 0

        do_test(0)
        do_test(1)

    def test_submit_err(self) -> None:
        def test_err(req: dict | None, err: str, code=400, key='json'):
            kw = {}
            if req is not None:
                kw[key] = req
            resp = self.clnt.post('/submit', **kw)
            self.assertEqual(resp.status_code, code)
            self.assertTrue(resp.is_json)
            self.assertEqual(resp.json, {
                'status': 'failure',
                'error': err,
            })

        with self.clnt.session_transaction() as sess:
            if 'u' in sess:
                del sess['u']
        test_err({
            'pass': 0,
            'problem': 2,
        }, 'Login required', code=403)

        with self.clnt.session_transaction() as sess:
            sess['u'] = 0

        test_err({
            'pass': 0,
            'problem': 2,
        }, 'POST request not in JSON format', key='data')

        test_err({
            'problem': 2,
        }, f'{"pass"!r} absent from JSON request')

        test_err({
            'pass': 'cow',
            'problem': 2,
        }, 'Local judge result should be an int')
        test_err({
            'pass': '0',
            'problem': 2,
        }, 'Local judge result should be an int')

        test_err({
            'pass': 2,
            'problem': 2,
        }, 'Local judge result 2 too large')

        test_err({
            'pass': -1,
            'problem': 2,
        }, 'Local judge result -1 too small')

        test_err({
            'pass': 0,
        }, f'{"problem"!r} absent from JSON request')

        test_err({
            'pass': 0,
            'problem': 'dog',
        }, 'Problem ID should be an int')
        test_err({
            'pass': 0,
            'problem': '2',
        }, 'Problem ID should be an int')

        test_err({
            'pass': 0,
            'problem': -1,
        }, 'Problem ID -1 too small')
        test_err({
            'pass': 0,
            'problem': 2147483648,
        }, 'Problem ID 2147483648 too large')

        test_err({
            'pass': 0,
            'problem': 2147483647,
        }, 'Problem 2147483647 does not exist', code=404)

    def test_login(self) -> None:
        def do_test(path='/me', meth='post', q=True):
            resp = getattr(self.clnt, meth)('/login?r=1' if q else '/login', data={
                'u': 'Super Admin',
                'pw': '12345678',
            })
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, path)
            self.assertIn('u', flask.session)
            self.assertEqual(flask.session['u'], 0)
            if q:
                self.assertNotIn('redirect', flask.session)

        with self.clnt.session_transaction() as sess:
            if 'u' in sess:
                del sess['u']
            if 'redirect' in sess:
                del sess['redirect']
        do_test(q=False)

        with self.clnt.session_transaction() as sess:
            del sess['u']
            sess['redirect'] = '/non-existent'
        do_test(q=False)

        with self.clnt.session_transaction() as sess:
            sess['redirect'] = '/non-existent2'
        do_test('/non-existent2')

        with self.clnt.session_transaction() as sess:
            sess['redirect'] = '/non-existent3'
        do_test('/non-existent3', meth='get')

        with self.clnt.session_transaction() as sess:
            del sess['u']
        do_test()

        with self.clnt.session_transaction() as sess:
            del sess['u']
        self.assertEqual(self.clnt.get('/login').status_code, 200)

    def test_login_err(self) -> None:
        def test_err(req: dict | None, err: str, key='data'):
            # drain flashed messages
            self.assertEqual(self.clnt.get('/login').status_code, 200)

            kw = {}
            if req is not None:
                kw[key] = req
            resp = self.clnt.post('/login', **kw)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, '/login')
            self.assertNotIn('u', flask.session)
            self.assertNotIn('redirect', flask.session)
            self.assertEqual(
                flask.get_flashed_messages(True, ('login', )),
                [('login', err)])

        with self.clnt.session_transaction() as sess:
            if 'u' in sess:
                del sess['u']
            if 'redirect' in sess:
                del sess['redirect']

        test_err({
            'U': 'Super Admin',
            'pw': '12345678',
        }, f'{"u"!r} absent from form')
        test_err({
            'pw': '12345678',
        }, f'{"u"!r} absent from form')
        test_err({}, f'{"u"!r} absent from form')
        test_err(None, f'{"u"!r} absent from form')
        test_err({
            'u': 'Super Admin',
            'pw': '12345678',
        }, f'{"u"!r} absent from form', key='json')

        test_err({
            'u': '',
            'pw': '12345678',
        }, 'User name too short')
        test_err({
            'u': 'l' * 65,
            'pw': '12345678',
        }, 'User name too long')

        test_err({
            'u': 'Super Admin',
        }, f'{"pw"!r} absent from form')
        test_err({
            'u': 'Super Admin',
            'PW': '12345678',
        }, f'{"pw"!r} absent from form')

        test_err({
            'u': 'Super Admin',
            'pw': '',
        }, 'Password too short')
        test_err({
            'u': 'Super Admin',
            'pw': 'l' * 65,
        }, 'Password too long')

        test_err({
            'u': 'Super Admin',
            'pw': 'l' * 64,
        }, 'Login incorrect')
        test_err({
            'u': 'x',
            'pw': '12345678',
        }, 'Login incorrect')

    def test_sign_up(self) -> None:
        def do_test(req: dict | None = None, err: str | None = None, meth='post', code=302, loc='/me', r=False, key='data'):
            # drain flashed messages
            self.assertLess(self.clnt.get('/sign-up').status_code, 400)

            kw = {}
            if req is not None:
                kw[key] = req
            resp = getattr(self.clnt, meth)(
                '/sign-up?r=1' if r else '/sign-up', **kw)
            self.assertEqual(resp.status_code, code)
            if 300 <= code < 400:
                self.assertEqual(resp.location, loc)
            if r:
                self.assertNotIn('redirect', flask.session)
            self.assertEqual(
                flask.get_flashed_messages(True, ('signup', )),
                [('signup', err)] if err else [])

        with self.clnt.session_transaction() as sess:
            sess['u'] = 0
            if 'redirect' in sess:
                del sess['redirect']
        do_test(meth='get')
        do_test(meth='get', r=True)

        with self.clnt.session_transaction() as sess:
            sess['redirect'] = '/non-existent'
        do_test(meth='get', loc='/non-existent', r=True)

        with self.clnt.session_transaction() as sess:
            sess['redirect'] = '/non-existent'
        do_test(meth='get')

        with self.clnt.session_transaction() as sess:
            del sess['u']

        err, path = (
            (None, '/login') if creds_of(self.USER_NAME) is None
            else ('Username already taken', '/sign-up'))
        do_test({
            'u': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, err, loc=path)

        do_test({
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, f'{"u"!r} absent from form', loc='/sign-up')
        do_test({
            'U': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, f'{"u"!r} absent from form', loc='/sign-up')
        do_test({
            'U': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, f'{"u"!r} absent from form', loc='/sign-up', key='json')
        do_test({}, f'{"u"!r} absent from form', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pwa': self.PASSWD,
        }, f'{"pw"!r} absent from form', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': self.PASSWD,
        }, f'{"pwa"!r} absent from form', loc='/sign-up')

        do_test({
            'u': 'test',
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, 'User name too short', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': 'qwer',
            'pwa': self.PASSWD,
        }, 'Password too short', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': 'qwer',
        }, 'Password confirmation too short', loc='/sign-up')

        do_test({
            'u': 't' * 65,
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, 'User name too long', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': 'p' * 65,
            'pwa': self.PASSWD,
        }, 'Password too long', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': 'p' * 65,
        }, 'Password confirmation too long', loc='/sign-up')

        do_test({
            'u': self.USER_NAME,
            'pw': self.PASSWD,
            'pwa': 'p' * 64,
        }, 'Password confirmation incorrect', loc='/sign-up')

        do_test({
            'u': 'Super Admin',
            'pw': self.PASSWD,
            'pwa': self.PASSWD,
        }, 'Username already taken', loc='/sign-up')
