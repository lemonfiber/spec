#!/usr/bin/env python3
"""Coverage tests for check_goal_coverage.py — OPS-R30, Q-R66.

The gate is shown refusing each of the three things it exists to refuse, against
a spec tree built in a temporary directory: an accepted requirement no version
locks, a declared entry some version has since locked, and a declared entry no
accepted feature defines any more. The second and third are what stop the
declaration list from outliving the debt it records — without them an entry
written once would sit there after the requirement was scheduled, and the gate
would go on reporting a gap that had been closed.

A draft feature is checked too, because that exemption is the one doing the most
work: `n1`–`n4` are the companion's ninety-eight requirements and they are absent
from every manifest on purpose.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_goal_coverage.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_goal_coverage as gate

FEATURE = """---
status: {status}
maturity: planned
---

# A feature

| ID | Requirement |
|----|-------------|
| **{prefix}-R1** | The first thing. |
| **{prefix}-R2** | The second thing. |
"""

MANIFEST = """version = "0.1.0"
status  = "planned"
goals   = [{goals}]
"""


def tree(status: str = "accepted", goals: str = '"X1-R1", "X1-R2"') -> pathlib.Path:
    """A spec checkout with one feature and one manifest."""
    root = pathlib.Path(tempfile.mkdtemp())
    features = root / gate.FEATURES / "features" / "x-thing"
    features.mkdir(parents=True)
    (features / "x1-thing.md").write_text(
        FEATURE.format(status=status, prefix="X1"), encoding="utf-8"
    )
    versions = root / gate.VERSIONS
    versions.mkdir(parents=True)
    (versions / "0.1.0.toml").write_text(MANIFEST.format(goals=goals), encoding="utf-8")
    return root


def run(root: pathlib.Path) -> tuple[int, str]:
    """The gate's exit code and what a maintainer would read."""
    out = io.StringIO()
    argv = sys.argv
    sys.argv = ["check_goal_coverage.py", "--root", str(root)]
    try:
        with contextlib.redirect_stdout(out):
            code = gate.main()
    finally:
        sys.argv = argv
    return code, out.getvalue()


class TheGate(unittest.TestCase):
    def setUp(self):
        self.declared = dict(gate.AWAITING_A_VERSION)
        gate.AWAITING_A_VERSION.clear()

    def tearDown(self):
        gate.AWAITING_A_VERSION.clear()
        gate.AWAITING_A_VERSION.update(self.declared)

    def test_a_locked_accepted_requirement_passes(self):
        code, said = run(tree())
        self.assertEqual(code, 0, said)
        self.assertIn("2 accepted requirements", said)

    def test_an_unlocked_accepted_requirement_is_refused(self):
        code, said = run(tree(goals='"X1-R1"'))
        self.assertEqual(code, 1)
        self.assertIn("X1-R2 is defined in", said)
        self.assertIn("no version locks it", said)

    def test_a_draft_feature_is_not_asked_to_be_scheduled(self):
        code, said = run(tree(status="draft", goals=""))
        self.assertEqual(code, 1, "a tree with no accepted feature says so")
        self.assertIn("no accepted feature was found", said)

    def test_a_draft_feature_beside_an_accepted_one_is_left_alone(self):
        root = tree(goals='"X1-R1", "X1-R2"')
        draft = root / gate.FEATURES / "features" / "x-thing" / "x2-later.md"
        draft.write_text(FEATURE.format(status="draft", prefix="X2"), encoding="utf-8")
        code, said = run(root)
        self.assertEqual(code, 0, said)

    def test_a_declared_entry_that_is_now_locked_is_refused(self):
        gate.AWAITING_A_VERSION["X1"] = ("a note naming 0.1.0", ["X1-R2"])
        code, said = run(tree())
        self.assertEqual(code, 1)
        self.assertIn("X1-R2 is locked by a version now", said)

    def test_a_declared_entry_nothing_defines_is_refused(self):
        gate.AWAITING_A_VERSION["X9"] = ("a note naming 0.1.0", ["X9-R1"])
        code, said = run(tree())
        self.assertEqual(code, 1)
        self.assertIn("X9-R1 is defined by no accepted feature", said)


class TheRealTree(unittest.TestCase):
    def test_the_spec_itself_passes(self):
        """What the gate says about this repository, which is what CI runs."""
        code, said = run(pathlib.Path(__file__).resolve().parent.parent)
        self.assertEqual(code, 0, said)

    def test_every_declared_entry_carries_where_the_rest_of_its_feature_sits(self):
        """A bare identifier is a debt nobody can act on."""
        for feature, (note, ids) in gate.AWAITING_A_VERSION.items():
            with self.subTest(feature=feature):
                self.assertRegex(note, r"0\.\d+\.0", f"{feature} names no version to decide against")
                self.assertTrue(ids, f"{feature} declares a note and no requirement")

    def test_a_requirement_is_declared_once(self):
        """Two features claiming the same identifier would hide one of them."""
        flat = [rid for _, ids in gate.AWAITING_A_VERSION.values() for rid in ids]
        self.assertEqual(sorted(flat), sorted(set(flat)))


if __name__ == "__main__":
    unittest.main()
