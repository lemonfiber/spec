#!/usr/bin/env python3
"""A bump drops from a caller's gates lists the groups the gates it moves to no longer know — OPS-R92.

The gates refuse a caller naming a group they do not know, so a pin moved past
a group's removal with the name left in `checks` fails every pull request in
the repository. These hold the bump to dropping that name and nothing else, to
leaving a list it cannot read or would empty to a run that says so, and to
reading what the gates know from the gates themselves.

Stdlib unittest.
Run:  python3 scripts/test_fan_out_checks.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import fan_out_pins
import gen_gates
from test_fan_out_pins import LIMITS, NOW, ARepositoryAndASpec, a_pin


def gates_knowing(*groups: str) -> str:
    """`gates.yml` as far as the bump reads it: its plan step's `KNOWN`."""
    return f"    - name: Which checks this caller runs\n      env:\n        KNOWN: {' '.join(groups)}\n"


def caller(sha: str, with_: str = "") -> str:
    """A repository's gates caller pinned at `sha`, with its `with` block as given."""
    return (
        "jobs:\n"
        "  gates:\n"
        "    permissions:\n"
        "      contents: read\n"
        f"{a_pin('gates.yml', sha)}"
        f"{with_}"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
    )


KNOWN = frozenset({"spec-check", "hygiene", "refs"})


class Pruned(unittest.TestCase):
    """The text a bump leaves in a caller, with no repository involved."""

    def test_a_group_the_gates_dropped_goes_from_checks_and_skip(self):
        said = fan_out_pins.pruned(
            caller("a" * 40, "    with:\n      checks: spec-check refs gone  # ours\n      skip: gone\n"),
            KNOWN,
        )
        self.assertEqual(
            said,
            (
                caller("a" * 40, "    with:\n      checks: spec-check refs  # ours\n      skip: ''\n"),
                ["checks drops gone", "skip drops gone"],
            ),
        )

    def test_known_groups_are_left_as_written(self):
        text = caller("a" * 40, "    with:\n      checks: spec-check   hygiene\n      skip: refs\n")
        self.assertEqual(fan_out_pins.pruned(text, KNOWN), (text, []))

    def test_an_absent_or_empty_list_is_left_alone(self):
        for with_ in (
            "",
            "    with:\n      checks:\n",
            "    with:\n      skip: ''\n",
            '    with:\n      skip: ""\n',
        ):
            with self.subTest(with_=with_):
                text = caller("a" * 40, with_)
                self.assertEqual(fan_out_pins.pruned(text, KNOWN), (text, []))

    def test_another_job_naming_the_same_input_is_not_the_gates(self):
        text = caller("a" * 40) + "    with:\n      checks: gone\n"
        self.assertEqual(fan_out_pins.pruned(text, KNOWN), (text, []))

    def test_a_list_it_cannot_read_or_would_empty_is_refused(self):
        for with_ in (
            "    with:\n      checks: 'spec-check gone'\n",
            "    with:\n      checks: >-\n        spec-check gone\n",
            "    with:\n      checks: gone\n",
        ):
            with self.subTest(with_=with_):
                self.assertIsNone(fan_out_pins.pruned(caller("a" * 40, with_), KNOWN))


class WhatTheGatesKnow(ARepositoryAndASpec, unittest.TestCase):
    """Read off `gates.yml` at the revision the bump moves to."""

    def test_read_from_known_at_that_revision(self):
        at = self.commit(gates_knowing("spec-check", "refs"), "gates.yml")
        self.assertEqual(fan_out_pins.known_at(self.spec, at), frozenset({"spec-check", "refs"}))

    def test_no_gates_or_a_known_list_not_declared_once_is_could_not_ask(self):
        self.assertIsNone(fan_out_pins.known_at(self.spec, self.third))
        twice = self.commit(gates_knowing("refs") * 2, "gates.yml")
        self.assertIsNone(fan_out_pins.known_at(self.spec, twice))

    def test_the_gates_here_know_every_group_their_generator_writes(self):
        self.assertEqual(
            fan_out_pins.known_in(
                (fan_out_pins.ROOT / ".github" / "workflows" / "gates.yml").read_text(encoding="utf-8")
            ),
            frozenset(check.group for check in gen_gates.CHECKS),
        )


class ABump(ARepositoryAndASpec, unittest.TestCase):
    """The whole bump over a caller whose pin moves past a group's removal."""

    def setUp(self):
        super().setUp()
        self.before = self.commit(gates_knowing("spec-check", "refs", "gone"), "gates.yml")
        self.after = self.commit(gates_knowing("spec-check", "refs"), "gates.yml")
        self.git("tag", "-f", "-a", "-m", "v1.0.9", "v1.0.9", self.after)

    def bump(self):
        return fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.after, LIMITS, NOW)

    def test_the_pin_moves_and_the_dropped_group_goes_with_it(self):
        where = self.wrote(
            "gates.yml", caller(self.before, "    with:\n      checks: spec-check refs gone\n")
        )
        moved, _ = self.bump()
        self.assertEqual(
            where.read_text(encoding="utf-8"),
            caller(self.after, "    with:\n      checks: spec-check refs\n").replace("# v1.0.1", "# v1.0.9"),
        )
        self.assertEqual(len(moved), 1)
        self.assertTrue(
            moved[0].endswith("(v1.0.9); checks drops gone, which gates.yml at v1.0.9 does not know")
        )

    def test_a_caller_naming_only_known_groups_moves_its_pin_alone(self):
        text = caller(self.before, "    with:\n      checks: spec-check refs\n")
        where = self.wrote("gates.yml", text)
        moved, _ = self.bump()
        self.assertEqual(
            where.read_text(encoding="utf-8"),
            text.replace(self.before, self.after).replace("# v1.0.1", "# v1.0.9"),
        )
        self.assertEqual(len(moved), 1)

    def test_a_caller_with_no_checks_moves_its_pin_alone(self):
        text = caller(self.before)
        where = self.wrote("gates.yml", text)
        self.bump()
        self.assertEqual(
            where.read_text(encoding="utf-8"),
            text.replace(self.before, self.after).replace("# v1.0.1", "# v1.0.9"),
        )

    def test_gates_it_cannot_read_or_a_list_it_would_empty_is_could_not_ask(self):
        where = self.wrote("gates.yml", caller(self.before, "    with:\n      checks: gone\n"))
        self.assertIsNone(self.bump())
        self.assertIn(self.before, where.read_text(encoding="utf-8"))
        unreadable = self.commit("no list here\n", "gates.yml")
        self.git("tag", "-f", "-a", "-m", "v1.0.9", "v1.0.9", unreadable)
        self.wrote("gates.yml", caller(self.before, "    with:\n      checks: refs\n"))
        self.assertIsNone(fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", unreadable, LIMITS, NOW))


if __name__ == "__main__":
    unittest.main(verbosity=2)
