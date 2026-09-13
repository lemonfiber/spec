#!/usr/bin/env python3
"""Coverage tests for check_order.py — OPS-R30, Q-R66.

The gate is shown refusing each thing it exists to refuse, against a spec tree
built in a temporary directory: a feature scheduled before something it requires,
and a feature requiring something no version schedules at all.

And shown *not* refusing the two it deliberately lets through. An inversion a
released version carries is history — nothing can be moved into or out of a
shipped release, so it is a fact to record rather than a fault to fix — and
`relates:` is the link that is worth reading and not needed to build. Both are
holes by design, and a hole nothing tests is a hole that closes by accident or
widens by accident, and nobody finds out which.

It is also shown refusing a tree it did not read. `FEATURES` and `VERSIONS` are
relative paths, so from any directory but the checkout root the globs yielded
nothing and the gate printed *order ok: 0 scheduled features, none before what it
requires* and exited 0.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_order.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_order as gate

FEATURE = """---
id: {fid}
status: accepted
{extra}---

# {fid}
"""

MANIFEST = """version = "{version}"
status  = "{status}"
goals   = [{goals}]
"""


def tree(features: list[tuple[str, str]], versions: list[tuple[str, str, str]]) -> pathlib.Path:
    """A spec checkout holding exactly these features and these manifests."""
    root = pathlib.Path(tempfile.mkdtemp())
    where = root / gate.FEATURES / "x-area"
    where.mkdir(parents=True)
    for fid, extra in features:
        (where / f"{fid.lower()}.md").write_text(
            FEATURE.format(fid=fid, extra=extra), encoding="utf-8"
        )
    plans = root / gate.VERSIONS
    plans.mkdir(parents=True)
    for version, status, goals in versions:
        (plans / f"{version}.toml").write_text(
            MANIFEST.format(version=version, status=status, goals=goals), encoding="utf-8"
        )
    return root


def run(root: pathlib.Path) -> tuple[int, str]:
    """The gate against this tree, as an exit code and everything it said."""
    said = io.StringIO()
    argv = sys.argv
    sys.argv = ["check_order.py", "--root", str(root)]
    try:
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
            code = gate.main()
    finally:
        sys.argv = argv
    return code, said.getvalue()


# Every tree carries the feature the gate checks it read, scheduled first so it is
# never itself the inversion under test.
KNOWN = (gate.KNOWN, "")
FIRST = ("0.1.0", "planned", f'"{gate.KNOWN}-R1"')


class ReadingTheTree(unittest.TestCase):
    def test_a_tree_it_did_not_read_is_refused_rather_than_passed(self):
        code, said = run(pathlib.Path(tempfile.mkdtemp()))
        self.assertEqual(code, 1)
        self.assertIn("read the wrong tree", said)

    def test_a_tree_with_features_but_no_schedule_is_refused_too(self):
        root = tree([KNOWN], [])
        code, said = run(root)
        self.assertEqual(code, 1)
        self.assertIn(gate.KNOWN, said)

    def test_a_tree_it_did_read_says_how_many_it_found(self):
        code, said = run(tree([KNOWN], [FIRST]))
        self.assertEqual(code, 0)
        self.assertIn("1 scheduled features", said)


class WhatItRefuses(unittest.TestCase):
    def test_a_feature_scheduled_before_what_it_requires(self):
        code, said = run(
            tree(
                [KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "planned", '"X2-R1"'), ("0.3.0", "planned", '"X3-R1"')],
            )
        )
        self.assertEqual(code, 1)
        self.assertIn("X2 ships in 0.2.0 but requires X3, which lands in 0.3.0", said)

    def test_a_feature_requiring_one_no_version_schedules(self):
        code, said = run(
            tree([KNOWN, ("X2", "requires: [X9]\n")], [FIRST, ("0.2.0", "planned", '"X2-R1"')])
        )
        self.assertEqual(code, 1)
        self.assertIn("requires X9, which no version schedules", said)

    def test_every_inversion_is_named_not_the_first(self):
        code, said = run(
            tree(
                [KNOWN, ("X2", "requires: [X3, X4]\n"), ("X3", ""), ("X4", "")],
                [
                    FIRST,
                    ("0.2.0", "planned", '"X2-R1"'),
                    ("0.3.0", "planned", '"X3-R1"'),
                    ("0.4.0", "planned", '"X4-R1"'),
                ],
            )
        )
        self.assertEqual(code, 1)
        self.assertIn("requires X3", said)
        self.assertIn("requires X4", said)
        self.assertIn("2 feature(s)", said)

    def test_versions_are_ordered_by_number_and_not_by_name(self):
        # `0.10.0` sorts before `0.2.0` as a string and after it as a version, and
        # the whole check is a comparison of two positions in that order.
        code, said = run(
            tree(
                [KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "planned", '"X2-R1"'), ("0.10.0", "planned", '"X3-R1"')],
            )
        )
        self.assertEqual(code, 1)
        self.assertIn("which lands in 0.10.0", said)


class WhatItLetsThrough(unittest.TestCase):
    def test_a_feature_scheduled_with_what_it_requires(self):
        code, _ = run(
            tree(
                [KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "planned", '"X2-R1", "X3-R1"')],
            )
        )
        self.assertEqual(code, 0)

    def test_a_feature_scheduled_after_what_it_requires(self):
        code, _ = run(
            tree(
                [KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "planned", '"X3-R1"'), ("0.3.0", "planned", '"X2-R1"')],
            )
        )
        self.assertEqual(code, 0)

    def test_an_inversion_a_released_version_carries_is_recorded_not_refused(self):
        code, said = run(
            tree(
                [KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "released", '"X2-R1"'), ("0.3.0", "planned", '"X3-R1"')],
            )
        )
        self.assertEqual(code, 0)
        self.assertIn("already shipped, recorded not enforced", said)
        self.assertIn("X2 ships in 0.2.0 but requires X3", said)

    def test_relates_is_read_by_nobody(self):
        code, _ = run(
            tree(
                [KNOWN, ("X2", "relates: [X3]\n"), ("X3", "")],
                [FIRST, ("0.2.0", "planned", '"X2-R1"'), ("0.3.0", "planned", '"X3-R1"')],
            )
        )
        self.assertEqual(code, 0)

    def test_a_feature_no_version_schedules_is_not_an_inversion(self):
        # It is `check_goal_coverage.py` that asks whether everything is scheduled.
        # This one asks only about order, and answering about both would be two
        # gates wearing one name.
        code, _ = run(
            tree([KNOWN, ("X2", "requires: [X3]\n"), ("X3", "")], [FIRST, ("0.3.0", "planned", '"X3-R1"')])
        )
        self.assertEqual(code, 0)

    def test_the_template_is_not_a_version(self):
        root = tree([KNOWN], [FIRST])
        (root / gate.VERSIONS / "TEMPLATE.toml").write_text(
            MANIFEST.format(version="x", status="planned", goals='"X9-R1"'), encoding="utf-8"
        )
        code, said = run(root)
        self.assertEqual(code, 0)
        self.assertIn("1 scheduled features", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
