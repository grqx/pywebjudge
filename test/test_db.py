import sqlite3
import typing
import unittest

from src.db import (
    all_testcases,
    creds_of,
    db_util,
    get_category,
    get_cursor,
    get_problems,
    get_subs,
    get_results,
    get_tag,
    get_tags,
    get_userinfo,
    problem_info,
    public_testcases,
    register,
    submit,
    teardown,
)


class TestDatabase(unittest.TestCase):
    USER_NAME: typing.Final = 'test'  # 4 chars, impossible to create from web UI
    PW_HASH: typing.Final = 'impossible pw hash'
    TC1 = ({
        'type': 0,
        'test_no': 1,
        'in': '3 5',
        'out': '8',
        'note': '3+5',
    }, {
        'type': 0,
        'test_no': 2,
        'in': '4 6',
        'out': '10',
        'note': None,
    }, {
        'type': 1,
        'test_no': 3,
        'in': '3918257 2484362',
        'out': '6402619',
        'note': 'bigger numbers'
    })
    CURSOR: sqlite3.Cursor

    @classmethod
    def setUpClass(cls) -> None:
        cls.CURSOR = cls.enterClassContext(get_cursor())

    def test_all_testcases(self) -> None:
        self.assertCountEqual(
            list(map(dict, all_testcases(1, cur=self.CURSOR))), self.TC1)

        tc2 = list(map(dict, all_testcases(2, cur=self.CURSOR)))
        self.assertEqual(len(tc2), 4)
        self.assertIn({
            'type': 0,
            'test_no': 1,
            'in': '3 5',
            'out': '-2',
            'note': '3 - 5 is -2',
        }, tc2)

    def test_creds_of(self) -> None:
        admin_creds = creds_of('Super Admin', cur=self.CURSOR)
        assert admin_creds is not None
        self.assertEqual(dict(admin_creds), {
            'user_id': 0,
            'pw_hash': '$2b$12$Pk4KkAVRCM1zoVPQSSDanePfVR1baGyga.OMsXDefQNcOiYZUSkZ.',
            'privilege_lvl': 3,
        })

    def test_get_category(self) -> None:
        expected_cats = 'Basic maths', 'Data structures', 'Language built-ins'
        for ordinal, cat in enumerate(expected_cats, start=1):
            got_cat = get_category(ordinal, cur=self.CURSOR)
            assert got_cat is not None
            self.assertEqual(dict(got_cat), {'name': cat})

    def test_get_problems(self) -> None:
        self.assertIn({
            'id': 1,
            'title': 'A+B',
        }, list(map(dict, get_problems(cur=self.CURSOR))))

    def test_get_tag(self) -> None:
        expected_tags = 'Addition and subtraction', 'Mathematics', 'Stack', 'Strings'
        for idx1, tag in enumerate(expected_tags, start=1):
            got_tag = get_tag(idx1, cur=self.CURSOR)
            assert got_tag is not None
            self.assertEqual(dict(got_tag), {'name': tag})

    def test_get_tags(self) -> None:
        for p_id in range(1, 5):  # problems
            tags = get_tags(p_id, cur=self.CURSOR)
            self.assertNotEqual(len(tags), 0)
            for tag_id in tags:  # for each tag
                self.assertIn(tag_id['tag_id'], range(1, 5))

    def test_get_uesrinfo(self) -> None:
        ui = get_userinfo(0, cur=self.CURSOR)
        assert ui is not None
        self.assertEqual(dict(ui), {'name': 'Super Admin'})

    def test_problem_info(self) -> None:
        info = problem_info(1, cur=self.CURSOR)
        assert info is not None
        self.assertEqual(dict(info), {
            'id': 1,
            'title': 'A+B',
            'desc': 'Calculate the sum of two integers, each less than 10000000, separated by a space.',
            'cat_id': 1,
        })

    def test_public_testcases(self) -> None:
        self.assertCountEqual(
            list(map(dict, public_testcases(1, cur=self.CURSOR))),
            filter(lambda x: x['type'] == 0, self.TC1))

    def test_e2e(self) -> None:
        old_results = list(map(dict, get_results(1, cur=self.CURSOR)))
        register(self.USER_NAME, self.PW_HASH, cur=self.CURSOR)
        creds_row = creds_of(self.USER_NAME, cur=self.CURSOR)
        assert creds_row is not None
        u = creds_row['user_id']
        self.assertEqual(dict(creds_row), {
            'user_id': u,
            'pw_hash': self.PW_HASH,
            'privilege_lvl': 1,
        })
        uinfo = get_userinfo(u, cur=self.CURSOR)
        assert uinfo is not None
        self.assertEqual(dict(uinfo), {'name': self.USER_NAME})
        self.assertEqual(list(map(dict, get_subs(u, cur=self.CURSOR))), [])
        submit(u, 1, 1, cur=self.CURSOR)
        self.assertEqual(list(map(dict, get_subs(u, cur=self.CURSOR))), [
                         {'problem_id': 1, 'result': 1}])
        self.assertEqual(list(map(dict, get_results(1, cur=self.CURSOR))), [
                         *old_results, {'result': 1}])
        db_util(r'DELETE FROM Submission WHERE user_id = ?')(
            lambda _, **__: None)(u, cur=self.CURSOR)
        db_util(r'DELETE FROM User WHERE user_id = ?')(
            lambda _, **__: None)(u, cur=self.CURSOR)


if __name__ == '__main__':
    unittest.main()
