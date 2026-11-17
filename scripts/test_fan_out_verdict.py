#!/usr/bin/env python3
"""A bump grants a verdict caller exactly what the verdict it moves to asks for — Q-R83.

A reusable job holds no permission its caller's job does not grant, so a pin on
`pin-only.yml` moved to a revision whose job asks for another permission, with
the caller's grants left as they were, fails every pull request in the
repository. These hold the bump to rewriting those grants and nothing else, to
leaving a caller it cannot read to a run that says so, and to reading what the
verdict asks for from `pin-only.yml` itself.

Stdlib unittest.
Run:  python3 scripts/test_fan_out_verdict.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import fan_out_pins
from test_fan_out_pins import LIMITS, NOW, ARepositoryAndASpec, a_pin

#: What the verdict's job asks for before the change and after it.
BEFORE = {"actions": "read", "checks": "write", "contents": "read", "pull-requests": "read"}
AFTER = {"actions": "read", "contents": "read", "pull-requests": "read", "statuses": "write"}


def verdict_asking(asked: dict[str, str]) -> str:
    """`pin-only.yml` as far as the bump reads it: its job's permissions."""
    grants = "".join(f"      {scope}: {level}\n" for scope, level in asked.items())
    return f"jobs:\n  {fan_out_pins.VERDICT_JOB}:\n    runs-on: ubuntu-latest\n    permissions:\n{grants}    steps: []\n"


def caller(sha: str, grants: dict[str, str] | None = None) -> str:
    """A repository's verdict caller pinned at `sha`, granting as given."""
    written = "".join(f"      {scope}: {level}\n" for scope, level in (grants or BEFORE).items())
    return (
        "on:\n  workflow_run:\n    workflows: [pin-only]\n"
        "jobs:\n"
        "  verdict:\n"
        "    permissions:\n"
        f"{written}"
        f"{a_pin('pin-only.yml', sha)}"
        "  other:\n"
        "    permissions:\n"
        "      checks: write\n"
        "    runs-on: ubuntu-latest\n"
    )


class WhatTheVerdictAsksFor(unittest.TestCase):
    def test_its_job_s_permissions_are_read(self):
        self.assertEqual(fan_out_pins.asked_in(verdict_asking(AFTER)), AFTER)

    def test_spec_s_own_verdict_is_read(self):
        workflow = (fan_out_pins.ROOT / ".github" / "workflows" / fan_out_pins.PIN_ONLY).read_text(encoding="utf-8")
        self.assertEqual(fan_out_pins.asked_in(workflow), AFTER)

    def test_a_workflow_it_cannot_read_that_way_asks_for_nothing(self):
        for text in (
            "jobs:\n  other:\n    permissions:\n      contents: read\n",
            "jobs:\n  pin-only:\n    runs-on: x\n  other:\n    permissions:\n      contents: read\n",
            "jobs:\n  pin-only:\n    permissions: read-all\n",
            "jobs:\n  pin-only:\n    permissions:\n      contents: read\n      contents: write\n",
            "jobs:\n  pin-only:\n    permissions:\n    steps: []\n",
        ):
            with self.subTest(text=text):
                self.assertIsNone(fan_out_pins.asked_in(text))


class Granted(unittest.TestCase):
    """The text a bump leaves in a caller, with no repository involved."""

    def test_the_verdict_s_job_is_granted_exactly_what_it_asks_and_no_other_job_changes(self):
        self.assertEqual(
            fan_out_pins.granted(caller("a" * 40), AFTER),
            (caller("a" * 40, AFTER), True),
        )

    def test_a_job_already_granting_it_is_left_as_written(self):
        text = caller("a" * 40, AFTER)
        self.assertEqual(fan_out_pins.granted(text, AFTER), (text, False))

    def test_a_grant_with_a_comment_is_read(self):
        text = caller("a" * 40).replace("checks: write", "checks: write  # the verdict", 1)
        self.assertEqual(fan_out_pins.granted(text, AFTER), (caller("a" * 40, AFTER), True))

    def test_a_caller_granting_nothing_or_otherwise_is_could_not_ask(self):
        pinned = a_pin("pin-only.yml", "a" * 40)
        for text in (
            f"jobs:\n  verdict:\n{pinned}",
            f"jobs:\n  verdict:\n    permissions: write-all\n{pinned}",
            f"jobs:\n  verdict:\n    permissions:\n      checks: {{}}\n{pinned}",
            f"jobs:\n  verdict:\n    permissions:\n{pinned}",
        ):
            with self.subTest(text=text):
                self.assertIsNone(fan_out_pins.granted(text, AFTER))


class ABump(ARepositoryAndASpec, unittest.TestCase):
    """The whole bump over a verdict caller whose pin moves to a job asking for another permission."""

    def setUp(self):
        super().setUp()
        self.before = self.commit(verdict_asking(BEFORE), "pin-only.yml")
        self.after = self.commit(verdict_asking(AFTER), "pin-only.yml")
        self.git("tag", "-f", "-a", "-m", "v1.0.9", "v1.0.9", self.after)

    def bump(self, named: str | None = None):
        return fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", named or self.after, LIMITS, NOW)

    def test_the_pin_moves_and_the_grants_with_it(self):
        where = self.wrote("pin-only-verdict.yml", caller(self.before))
        moved, _ = self.bump()
        self.assertEqual(
            where.read_text(encoding="utf-8"),
            caller(self.after, AFTER).replace("# v1.0.1", "# v1.0.9"),
        )
        self.assertEqual(len(moved), 1)
        self.assertTrue(
            moved[0].endswith(
                "(v1.0.9); its job now grants actions: read, contents: read, pull-requests: read,"
                " statuses: write, as pin-only.yml at v1.0.9 asks"
            ),
            moved[0],
        )

    def test_a_caller_already_granting_it_moves_its_pin_alone(self):
        text = caller(self.before, AFTER)
        where = self.wrote("pin-only-verdict.yml", text)
        moved, _ = self.bump()
        self.assertEqual(
            where.read_text(encoding="utf-8"),
            text.replace(self.before, self.after).replace("# v1.0.1", "# v1.0.9"),
        )
        self.assertTrue(moved[0].endswith("(v1.0.9)"), moved[0])

    def test_a_verdict_or_a_caller_it_cannot_read_is_could_not_ask(self):
        where = self.wrote(
            "pin-only-verdict.yml",
            f"jobs:\n  verdict:\n    permissions: write-all\n{a_pin('pin-only.yml', self.before)}",
        )
        self.assertIsNone(self.bump())
        self.assertIn(self.before, where.read_text(encoding="utf-8"))
        unreadable = self.commit("no job here\n", "pin-only.yml")
        self.git("tag", "-f", "-a", "-m", "v1.0.9", "v1.0.9", unreadable)
        self.wrote("pin-only-verdict.yml", caller(self.before))
        self.assertIsNone(self.bump(unreadable))


if __name__ == "__main__":
    unittest.main(verbosity=2)
