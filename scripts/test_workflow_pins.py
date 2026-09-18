#!/usr/bin/env python3
"""Coverage tests for workflow_pins.py — a pin says how far behind it is (Q-R68).

The gate it guards runs in fourteen repositories, so the two answers that matter
most are the ones nobody looks at: *clean* where a pin is current, and *could not
ask* where the checkout cannot answer. A drift check that reports clean because
it failed to resolve anything is the drift check nobody would have noticed was
off — which is how these pins reached fifty-seven commits behind in the first
place.

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_workflow_pins.py
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

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import workflow_pins


def a_pin(workflow: str, sha: str) -> str:
    return f"    uses: lemonfiber/spec/.github/workflows/{workflow}@{sha} # main\n"


class Reading(unittest.TestCase):
    """What a pin is, and what is not one."""

    def test_a_pin_is_found_with_its_trailing_comment(self):
        found = workflow_pins.pins_in(a_pin("dco.yml", "a" * 40))
        self.assertEqual(found, [("dco.yml", "a" * 40)])

    def test_somebody_elses_action_is_not_a_pin_of_ours(self):
        said = "    uses: actions/checkout@" + "b" * 40 + " # v7\n"
        self.assertEqual(workflow_pins.pins_in(said), [])

    def test_a_tag_is_not_read_as_a_commit(self):
        # Only a forty-character hex commit. A tag would be a different pin with
        # a different question — whether it moved — and this does not ask it.
        said = "    uses: lemonfiber/spec/.github/workflows/dco.yml@v1\n"
        self.assertEqual(workflow_pins.pins_in(said), [])

    def test_one_pin_in_several_files_is_one_finding(self):
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / ".github" / "workflows").mkdir(parents=True)

        for name in ("ci.yml", "labels.yml"):
            (root / ".github" / "workflows" / name).write_text(
                a_pin("dco.yml", "c" * 40), encoding="utf-8"
            )

        found = workflow_pins.pins_under(root)
        self.assertEqual(len(found), 1)
        self.assertEqual(len(found[("dco.yml", "c" * 40)]), 2)


class Saying(unittest.TestCase):
    """What a refusal tells somebody."""

    def test_it_names_the_commits_not_taken(self):
        said = workflow_pins.refusal("dco.yml", ["ci.yml"], ["abc1234 a thing", "def5678 another"])
        self.assertIn("has changed 2 time(s)", said)
        self.assertIn("abc1234 a thing", said)
        self.assertIn("ci.yml", said)

    def test_a_long_run_says_what_it_did_not_list(self):
        # A silent cap reads as *that was all of them*, which is the one thing a
        # refusal naming commits must not imply.
        missed = [f"{i:07d} commit {i}" for i in range(25)]
        said = workflow_pins.refusal("dco.yml", ["ci.yml"], missed)
        self.assertIn("has changed 25 time(s)", said)
        self.assertIn("and 15 more, not listed here", said)


class AgainstARepository(unittest.TestCase):
    """The half that needs a real checkout to answer."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.spec = self.root / "spec"
        self.repo = self.root / "repo"
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        self.spec.mkdir()

        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")
        self.first = self.commit("one")
        self.second = self.commit("two")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.spec), *args], check=True, capture_output=True)

    def commit(self, said: str, workflow: str = "dco.yml") -> str:
        where = self.spec / ".github" / "workflows" / workflow
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(said, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", said)
        return subprocess.run(
            ["git", "-C", str(self.spec), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    def pin(self, sha: str):
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            a_pin("dco.yml", sha), encoding="utf-8"
        )

    def run_main(self) -> tuple[int, str]:
        was = pathlib.Path.cwd()
        os.chdir(self.repo)
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said):
                code = workflow_pins.main()
        finally:
            os.chdir(was)
        return code, said.getvalue()

    def test_a_pin_at_head_is_clean(self):
        self.pin(self.second)
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("holds the newest revision of the workflow it names", out)

    def test_a_pin_behind_is_refused_and_names_what_it_missed(self):
        self.pin(self.first)
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("has changed 1 time(s)", out)
        self.assertIn("two", out)
        self.assertIn(self.second, out)

    def test_a_commit_to_another_workflow_leaves_this_pin_current(self):
        # A pin holds one file. Measured against the default branch every pin in
        # the organisation is behind for most of every day, and a check that is
        # always red is one somebody stops requiring — which is the failure this
        # narrowing exists to prevent, not a convenience.
        self.pin(self.second)
        self.commit("three", workflow="sonar.yml")
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 0, out)

    def test_a_commit_to_the_pinned_workflow_still_refuses(self):
        # The other half of the same claim: narrowing must not be a way through.
        self.pin(self.second)
        self.commit("three", workflow="dco.yml")
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("has changed 1 time(s)", out)

    def test_a_pin_this_checkout_cannot_resolve_is_our_fault(self):
        # Code 2, never 1. A shallow clone or a rewritten commit is this side's
        # problem, and refusing somebody's work over it is the failure mode the
        # whole two-code split exists for.
        self.pin("f" * 40)
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("cannot resolve", out)

    def test_a_revision_that_is_not_one_is_never_handed_to_git(self):
        # Nothing in this file's own reading can produce such a value, which is
        # the point: the guard is for the caller that comes later. An argument
        # beginning with `-` is an option to git rather than a revision, and the
        # answer for one is the same "could not ask" everything else here gives.
        self.assertIsNone(
            workflow_pins.commits_between(
                self.spec, "--output=/tmp/x", self.second, "dco.yml"
            )
        )

    def test_no_checkout_is_our_fault_too(self):
        self.pin(self.second)
        sys.argv = ["workflow_pins.py", str(self.root / "nowhere")]
        code, out = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("no spec checkout", out)

    def test_a_repository_pinning_nothing_of_ours_passes(self):
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            "    uses: actions/checkout@" + "b" * 40 + "\n", encoding="utf-8"
        )
        sys.argv = ["workflow_pins.py", str(self.spec)]
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("nothing to check", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
