#!/usr/bin/env python3
"""Coverage tests for check_goal_coverage.py — OPS-R30, Q-R66.

The gate is shown refusing each of the three things it exists to refuse, against
a spec tree built in a temporary directory: an accepted requirement no version
locks, a declared entry some version has since locked, and a declared entry no
accepted feature defines any more. The second and third are what stop the
declaration list from outliving the debt it records — without them an entry
written once would sit there after the requirement was scheduled, and the gate
would go on reporting a gap that had been closed.

A draft feature is checked too, because a feature nobody has agreed to is one no
version may lock.

The architecture is read on the same terms, with one addition: an `ARCH-R` row may
be exempted by name for one of three reasons, and each way an exemption stops
being true is refused — the row locked since, the row gone, a reason outside the
three, and a restatement of something no version locks.

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


ARCHITECTURE = """# A contract

**Status:** {status}

| ID | Requirement |
|----|-------------|
| **ARCH-R1** | The first rule. |
| **ARCH-R2** | The second rule. |
"""


def tree(
    status: str = "accepted",
    goals: str = '"X1-R1", "X1-R2"',
    architecture: str | None = None,
) -> pathlib.Path:
    """A spec checkout with one feature and one manifest, and a contract if asked."""
    root = pathlib.Path(tempfile.mkdtemp())
    features = root / gate.FEATURES / "features" / "x-thing"
    features.mkdir(parents=True)
    (features / "x1-thing.md").write_text(
        FEATURE.format(status=status, prefix="X1"), encoding="utf-8"
    )
    if architecture is not None:
        contracts = root / gate.ARCHITECTURE / "contracts"
        contracts.mkdir(parents=True)
        (contracts / "a-contract.md").write_text(
            ARCHITECTURE.format(status=architecture), encoding="utf-8"
        )
    versions = root / gate.VERSIONS
    versions.mkdir(parents=True)
    (versions / "0.1.0.toml").write_text(MANIFEST.format(goals=goals), encoding="utf-8")
    return root


BOTH = '"X1-R1", "X1-R2", "ARCH-R1", "ARCH-R2"'


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


class Isolated(unittest.TestCase):
    """Each test starts with nothing declared and nothing exempt."""

    def setUp(self):
        self.declared = dict(gate.AWAITING_A_VERSION)
        self.exempt = dict(gate.EXEMPT_FROM_A_VERSION)
        gate.AWAITING_A_VERSION.clear()
        gate.EXEMPT_FROM_A_VERSION.clear()

    def tearDown(self):
        gate.AWAITING_A_VERSION.clear()
        gate.AWAITING_A_VERSION.update(self.declared)
        gate.EXEMPT_FROM_A_VERSION.clear()
        gate.EXEMPT_FROM_A_VERSION.update(self.exempt)


class TheGate(Isolated):

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
        self.assertIn("X9-R1 is defined by no accepted document", said)

    def test_a_withdrawn_row_is_not_a_requirement_awaiting_a_version(self):
        """The row survives so the number is never reused; the debt does not.

        OPS-R30 forbids a withdrawn requirement being a goal, so a gate counting
        one as live demands a lock the same rule refuses to allow — a debt whose
        only discharge is the thing that is not permitted.
        """
        root = tree(goals='"X1-R1", "X1-R2"')
        feature = root / gate.FEATURES / "features" / "x-thing" / "x1-thing.md"
        feature.write_text(
            feature.read_text(encoding="utf-8")
            + "| **X1-R3** | *Withdrawn — carried to X2-R1. The number is not reused.* |\n",
            encoding="utf-8",
        )
        code, said = run(root)
        self.assertEqual(code, 0, said)
        self.assertIn("2 accepted requirements", said)

    def test_a_declared_entry_the_spec_has_since_withdrawn_is_refused(self):
        """Which is how the five this check was holding came to be deleted."""
        root = tree(goals='"X1-R1"')
        feature = root / gate.FEATURES / "features" / "x-thing" / "x1-thing.md"
        feature.write_text(
            feature.read_text(encoding="utf-8").replace(
                "| **X1-R2** | The second thing. |",
                "| **X1-R2** | *Withdrawn — carried to X2-R1. The number is not reused.* |",
            ),
            encoding="utf-8",
        )
        gate.AWAITING_A_VERSION["X1"] = ("a note naming 0.1.0", ["X1-R2"])
        code, said = run(root)
        self.assertEqual(code, 1)
        self.assertIn("X1-R2 is defined by no accepted document", said)


class TheArchitecture(Isolated):
    def test_a_locked_architecture_row_passes(self):
        code, said = run(tree(goals=BOTH, architecture="Accepted"))
        self.assertEqual(code, 0, said)
        self.assertIn("2 architecture requirements", said)

    def test_an_unlocked_architecture_row_is_refused(self):
        code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 is defined in 20-architecture/contracts/a-contract.md", said)
        self.assertIn("no version locks it", said)

    def test_a_document_nobody_has_accepted_is_left_alone(self):
        root = tree(goals=BOTH, architecture="Accepted")
        extra = root / gate.ARCHITECTURE / "contracts" / "b-proposed.md"
        extra.write_text(
            ARCHITECTURE.format(status="Proposed")
            .replace("ARCH-R1", "ARCH-R8")
            .replace("ARCH-R2", "ARCH-R9"),
            encoding="utf-8",
        )
        code, said = run(root)
        self.assertEqual(code, 0, said)
        self.assertIn("2 architecture requirements", said)

    def test_an_architecture_with_nothing_accepted_is_a_reading_that_failed(self):
        code, said = run(tree(architecture="Proposed"))
        self.assertEqual(code, 1)
        self.assertIn("no accepted architecture document", said)

    def test_a_withdrawn_architecture_row_is_not_asked_for(self):
        root = tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted")
        contract = root / gate.ARCHITECTURE / "contracts" / "a-contract.md"
        contract.write_text(
            contract.read_text(encoding="utf-8").replace(
                "| **ARCH-R2** | The second rule. |",
                "| **ARCH-R2** | *Withdrawn — carried to ARCH-R1. The number is not reused.* |",
            ),
            encoding="utf-8",
        )
        code, said = run(root)
        self.assertEqual(code, 0, said)

    def test_each_of_the_three_reasons_exempts_a_row(self):
        for reason in ("principle", "dormant until the first release candidate", "restates X1-R1, X1-R2"):
            with self.subTest(reason=reason):
                gate.EXEMPT_FROM_A_VERSION.clear()
                gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = reason
                code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
                self.assertEqual(code, 0, said)
                self.assertIn("1 exempt from one", said)

    def test_a_reason_outside_the_three_is_refused(self):
        gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = "not needed yet"
        code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 is exempted as 'not needed yet'", said)

    def test_a_bare_restatement_is_refused(self):
        """`restates` naming nothing is a reason with its evidence left out."""
        gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = "restates"
        code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 is exempted as 'restates'", said)

    def test_an_exemption_for_a_row_now_locked_is_refused(self):
        gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = "principle"
        code, said = run(tree(goals=BOTH, architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 is locked by a version now — delete its exemption", said)

    def test_an_exemption_for_a_row_nothing_defines_is_refused(self):
        gate.EXEMPT_FROM_A_VERSION["ARCH-R9"] = "principle"
        code, said = run(tree(goals=BOTH, architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R9 is defined by no accepted architecture document", said)

    def test_a_restatement_of_something_no_version_locks_is_refused(self):
        """Exempt because a version reaches it through what it restates — so one must."""
        gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = "restates X1-R2"
        code, said = run(tree(goals='"X1-R1", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 restates X1-R2, which no version locks", said)

    def test_a_restatement_of_something_nothing_defines_is_refused(self):
        gate.EXEMPT_FROM_A_VERSION["ARCH-R2"] = "restates X7-R1"
        code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 restates X7-R1, which no accepted document defines", said)

    def test_an_architecture_row_may_wait_for_a_version(self):
        """Work with a version decided and not yet written into it is a debt, not an exemption."""
        gate.AWAITING_A_VERSION["ARCH"] = ("a note naming 0.1.0", ["ARCH-R2"])
        code, said = run(tree(goals='"X1-R1", "X1-R2", "ARCH-R1"', architecture="Accepted"))
        self.assertEqual(code, 0, said)
        self.assertIn("1 awaiting a version", said)

    def test_a_waiting_architecture_row_since_locked_is_refused(self):
        gate.AWAITING_A_VERSION["ARCH"] = ("a note naming 0.1.0", ["ARCH-R2"])
        code, said = run(tree(goals=BOTH, architecture="Accepted"))
        self.assertEqual(code, 1)
        self.assertIn("ARCH-R2 is locked by a version now — delete its line", said)


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

    def test_every_exemption_gives_one_of_the_three_reasons(self):
        for rid, reason in gate.EXEMPT_FROM_A_VERSION.items():
            with self.subTest(rid=rid):
                self.assertRegex(rid, r"^ARCH-R\d+$")
                self.assertIsNotNone(gate.REASON.match(reason), reason)


if __name__ == "__main__":
    unittest.main()
