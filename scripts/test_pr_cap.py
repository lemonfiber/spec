#!/usr/bin/env python3
"""The comment on a pull request past the cap, and the silence otherwise —
GOV-R58.

Stdlib unittest.
Run:  python3 scripts/test_pr_cap.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pr_cap  # noqa: E402
from claims import CAP  # noqa: E402


def pull(number, kind="User", login="p", title="feat: x"):
    return {"number": number, "title": title, "user": {"login": login, "type": kind}}


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv
    sys.argv = ["pr_cap.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pr_cap.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class Comment(unittest.TestCase):
    def test_the_pull_request_that_takes_it_past_the_cap(self):
        pulls = [pull(n, login=f"p{n}") for n in range(1, CAP + 2)]
        pulls.append(pull(99, kind="Bot", login="dependabot[bot]"))
        said = pr_cap.comment(pulls, CAP + 1)
        self.assertTrue(said.startswith(pr_cap.MARKER))
        self.assertIn(f"holds {CAP + 1} open pull requests", said)
        self.assertIn(f"The cap is {CAP}", said)
        self.assertIn("- #1 feat: x (@p1)", said)
        self.assertNotIn(f"#{CAP + 1} feat", said, "the others, not this one")
        self.assertNotIn("#99", said, "a bot's pull request is not one of them")

    def test_nothing_within_the_cap(self):
        pulls = [pull(n) for n in range(1, CAP + 1)] + [pull(9, kind="Bot")] * 3
        self.assertEqual(pr_cap.comment(pulls, 1), "")

    def test_nothing_for_a_bots_pull_request(self):
        pulls = [pull(n) for n in range(1, CAP + 2)] + [pull(99, kind="Bot")]
        self.assertEqual(pr_cap.comment(pulls, 99), "")

    def test_a_pull_request_with_no_title_or_user(self):
        pulls = [pull(n) for n in range(1, CAP + 1)] + [{"number": 50}]
        self.assertIn("- #50 (@?)", pr_cap.comment(pulls, 1))

    def test_a_pull_request_that_is_not_open(self):
        with self.assertRaisesRegex(LookupError, "#7 is not an open pull request"):
            pr_cap.comment([pull(1)], 7)


class Main(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_writes_the_comment(self):
        pathlib.Path("pulls.json").write_text(
            json.dumps([pull(n) for n in range(1, CAP + 2)]), encoding="utf-8")
        code, out, _ = run_main(["--pulls", "pulls.json", "--number", "1"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith(pr_cap.MARKER))

    def test_an_unreadable_file_or_an_unknown_pull_request(self):
        pathlib.Path("pulls.json").write_text("[", encoding="utf-8")
        code, _, err = run_main(["--pulls", "pulls.json", "--number", "1"])
        self.assertEqual(code, 2)
        self.assertIn("::error::", err)
        pathlib.Path("pulls.json").write_text("[]", encoding="utf-8")
        self.assertEqual(run_main(["--pulls", "pulls.json", "--number", "1"])[0], 2)


if __name__ == "__main__":
    unittest.main()
