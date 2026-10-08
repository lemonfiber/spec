#!/usr/bin/env python3
"""Reopening a pull request `spec-check` closed, once what it cited resolves —
GOV-R56.

The forge is a fake that answers the calls `gh api` would make and records the
writes, so the suite reads what would be reopened without reopening anything.

Stdlib unittest.
Run:  python3 scripts/test_reopen_resolved.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reopen_resolved as reopen  # noqa: E402

CLOSING = (f"{reopen.CLOSED_BY} cited identifiers do not exist on spec@main: A1-R9, GOV-R70\n\n"
           "This is sequencing, not rejection.")

DIFF = """diff --git a/x.md b/x.md
--- a/x.md
+++ b/x.md
@@ -1,3 +1,4 @@
-| **A1-R1** | The tool MUST start. |
+| **A1-R1** | The tool MUST start quickly. |
+| **A1-R9** | The tool MUST stop. |
+| **GOV-R70** | A rule MUST hold. |
 | **A1-R2** | Kept. |
"""


class Forge:
    """Answers as the REST API would for one closed pull request."""

    def __init__(self, *, state="closed", merged=False, closer=reopen.CLOSER,
                 comments=(CLOSING,), fail_write=False):
        self.pull = {"state": state, "merged": merged}
        self.events = [{"event": "labeled"}, {"event": "closed", "actor": {"login": closer}}]
        self.comments = [{"body": b} for b in comments]
        self.writes = []
        self.fail_write = fail_write

    def __call__(self, args):
        if args[:3] == ["-X", "GET", "search/issues"]:
            return {"items": [{"repository_url": "https://api.github.com/repos/lemonfiber/core",
                               "number": 7}]}
        if args[:1] == ["-X"]:
            if self.fail_write:
                raise subprocess.CalledProcessError(1, "gh", stderr="the branch is gone\n")
            self.writes.append(args)
            return None
        path = args[0]
        if path.endswith("/events?per_page=100"):
            return self.events
        if path.endswith("/comments?per_page=100"):
            return self.comments
        return self.pull


class Spec(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.spec = pathlib.Path("spec")
        (self.spec / "f").mkdir(parents=True)
        (self.spec / "f" / "a1.md").write_text(
            "---\nstatus: accepted\n---\n| **A1-R1** | x |\n| **A1-R9** | The tool MUST stop. |\n",
            encoding="utf-8")
        (self.spec / "rules.md").write_text(
            "**Status:** Accepted\n\n| **GOV-R70** | A rule MUST hold. |\n"
            "| **GOV-R71** | *Withdrawn: gone.* |\n", encoding="utf-8")
        (self.spec / "draft.md").write_text(
            "**Status:** Draft\n\n| **GOV-R72** | A rule MAY hold. |\n", encoding="utf-8")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


class Rules(Spec):
    def test_only_rows_the_diff_adds_and_did_not_remove(self):
        self.assertEqual(reopen.newly_defined(DIFF), {"A1-R9", "GOV-R70"})
        self.assertEqual(reopen.newly_defined("+++ b/x.md\n--- a/x.md\n"), set())

    def test_the_identifiers_a_closing_comment_names(self):
        self.assertEqual(reopen.unknown_in(CLOSING), ["A1-R9", "GOV-R70"])
        self.assertEqual(reopen.unknown_in("Some other comment naming A1-R9"), [])
        self.assertEqual(reopen.unknown_in(f"{reopen.CLOSED_BY} no `Spec:` citation found"), [])

    def test_resolving_as_spec_check_resolves(self):
        self.assertTrue(reopen.resolves(["A1-R9", "GOV-R70"], self.spec))
        self.assertFalse(reopen.resolves(["A1-R9", "Z9-R1"], self.spec), "not defined")
        self.assertFalse(reopen.resolves(["GOV-R71"], self.spec), "retired")
        self.assertFalse(reopen.resolves(["GOV-R72"], self.spec), "Draft")
        self.assertFalse(reopen.resolves([], self.spec))


class Owed(Spec):
    def test_closed_by_spec_check_for_what_now_resolves(self):
        self.assertEqual(reopen.owed("lemonfiber/core", 7, self.spec, Forge()), ["A1-R9", "GOV-R70"])

    def test_left_alone(self):
        cases = {
            "open again": Forge(state="open"),
            "merged": Forge(merged=True),
            "closed since by its author": Forge(closer="someone"),
            "no closing comment": Forge(comments=("thanks",)),
            "still not resolving": Forge(comments=(CLOSING.replace("GOV-R70", "Z9-R1"),)),
        }
        for why, forge in cases.items():
            with self.subTest(why):
                self.assertIsNone(reopen.owed("lemonfiber/core", 7, self.spec, forge))

    def test_no_close_event_at_all(self):
        forge = Forge()
        forge.events = []
        self.assertIsNone(reopen.owed("lemonfiber/core", 7, self.spec, forge))

    def test_the_newest_closing_comment_decides(self):
        older = CLOSING.replace("A1-R9, GOV-R70", "Z9-R1")
        forge = Forge(comments=(older, CLOSING))
        self.assertEqual(reopen.owed("lemonfiber/core", 7, self.spec, forge), ["A1-R9", "GOV-R70"])

    def test_candidates_from_the_search(self):
        found = reopen.candidates({"A1-R9"}, "lemonfiber", Forge())
        self.assertEqual(found, {("lemonfiber/core", 7)})

    def test_reopening_says_why(self):
        forge = Forge()
        reopen.reopen("lemonfiber/core", 7, ["A1-R9"], "abcdef123", forge)
        patch, comment = forge.writes
        self.assertIn("state=open", patch)
        self.assertIn("A1-R9 is defined on spec@main as of abcdef1", comment[-1])
        reopen.reopen("lemonfiber/core", 7, ["A1-R9", "GOV-R70"], "abcdef123", forge)
        self.assertIn("A1-R9, GOV-R70 are defined", forge.writes[-1][-1])


def run_main(argv, forge):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["reopen_resolved.py", *argv]
    try:
        with contextlib.redirect_stdout(out), mock.patch.object(reopen, "gh", forge):
            code = reopen.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Main(Spec):
    def args(self, *extra):
        return ["--spec-dir", "spec", "--diff-file", "push.diff", "--sha", "abcdef123", *extra]

    def setUp(self):
        super().setUp()
        pathlib.Path("push.diff").write_text(DIFF, encoding="utf-8")

    def test_reopens_what_is_owed(self):
        forge = Forge()
        code, said = run_main(self.args(), forge)
        self.assertEqual(code, 0)
        self.assertIn("defined by this push: A1-R9, GOV-R70", said)
        self.assertIn("lemonfiber/core#7: reopened, A1-R9, GOV-R70 now resolving", said)
        self.assertEqual(len(forge.writes), 2)

    def test_a_dry_run_writes_nothing(self):
        forge = Forge()
        _, said = run_main(self.args("--dry-run"), forge)
        self.assertIn("would reopen", said)
        self.assertEqual(forge.writes, [])

    def test_left_alone_and_said(self):
        self.assertIn("lemonfiber/core#7: left alone", run_main(self.args(), Forge(merged=True))[1])

    def test_one_that_cannot_be_reopened_is_named(self):
        code, said = run_main(self.args(), Forge(fail_write=True))
        self.assertEqual(code, 0)
        self.assertIn("::warning::lemonfiber/core#7 could not be reopened: the branch is gone", said)

    def test_a_push_that_defines_nothing(self):
        pathlib.Path("push.diff").write_text("", encoding="utf-8")
        self.assertIn("defines no identifier", run_main(self.args(), Forge())[1])

    def test_what_cannot_be_read(self):
        os.remove("push.diff")
        self.assertEqual(run_main(self.args(), Forge())[0], 2)


class Gh(unittest.TestCase):
    def test_one_call_as_json(self):
        done = mock.Mock(stdout='{"a": 1}')
        with mock.patch("subprocess.run", return_value=done) as ran:
            self.assertEqual(reopen.gh(["repos/x"]), {"a": 1})
        self.assertEqual(ran.call_args.args[0], ["gh", "api", "repos/x"])
        with mock.patch("subprocess.run", return_value=mock.Mock(stdout="")):
            self.assertIsNone(reopen.gh(["-X", "PATCH", "x"]))


if __name__ == "__main__":
    unittest.main()
