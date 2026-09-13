#!/usr/bin/env python3
"""The no-stub gate is shown refusing an unbuilt requirement — OPS-R54, Q-R66.

`0.14.0` locked five features whose catalogue files said `building`, and the only
thing that caught it was somebody reading six files by hand on the day. So the
first thing asserted here is not that the gate passes: it is that it *refuses*,
and refuses by name, the shape that shipped over it.

The rule asks about the requirements a version carries rather than about whole
features, and both halves of that need driving. A `building` feature whose locked
requirements are all built has to **pass** — that is the narrowing, and without a
case for it the gate would be the unsatisfiable one this replaced. A `planned`
feature whose requirements the tracker ticks has to **fail** — that is the
catalogue and the tracker disagreeing, and it is the one refusal `gate.py` would
not make.

The two silences get the same treatment. A gate that reads an empty catalogue
finds no unbuilt requirement, and a gate whose vocabulary the schema has renamed
finds none either; both would print a pass and mean nothing by it. Each is driven
into the failing state and checked for saying so.

Stdlib unittest, no dependencies. The fixtures are a real directory tree rather
than patched functions, because what the gate reads — a glob, a schema file, a
frontmatter block, a tracker row — is exactly what a patched reader would stop
testing.
Run:  python3 scripts/test_no_stubs.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import catalogue  # noqa: E402
import check_no_stubs  # noqa: E402

SCHEMA = {
    "properties": {
        "id": {"type": "string", "pattern": "^[A-N][0-9]+$"},
        "maturity": {
            "enum": ["planned", "building", "built", "shipped", "withdrawn"]
        },
    }
}

TRACKER = "checkouts/lemonfiber/IMPLEMENTATION-STATUS.md"


def run_main(argv):
    """Call main() with argv patched; return (exit code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["check_no_stubs.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = check_no_stubs.main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Catalogue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path("70-operations/versions").mkdir(parents=True)
        self.schema(SCHEMA)
        self.tracker()

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def schema(self, body):
        path = pathlib.Path(catalogue.SCHEMA_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    def tracker(self, *done):
        """A tracker marking the named requirements done, and nothing else."""
        path = pathlib.Path(TRACKER)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = "".join(f"| a deliverable | `{one}` | ✅ | landed |\n" for one in done)
        path.write_text(f"| Deliverable | Spec | Status | Landing |\n{rows}",
                        encoding="utf-8")

    def feature(self, fid, maturity, title="A feature", requirements=3,
                area="b-running"):
        directory = pathlib.Path(f"10-functional/features/{area}")
        directory.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f"| **{fid}-R{n}** | Something MUST happen. |"
            for n in range(1, requirements + 1)
        )
        (directory / f"{fid.lower()}-thing.md").write_text(
            f"---\nid: {fid}\ntitle: {title}\nmaturity: {maturity}\n---\n\n"
            f"| ID | Requirement |\n|----|----|\n{rows}\n",
            encoding="utf-8",
        )

    def manifest(self, version, goals):
        listed = ", ".join(f'"{g}"' for g in goals)
        pathlib.Path(f"70-operations/versions/{version}.toml").write_text(
            f'version = "{version}"\nstatus = "staged"\nrepos = ["lf"]\n'
            f"goals = [{listed}]\n",
            encoding="utf-8",
        )

    def act(self, version):
        return run_main(["--version", version, "--status", TRACKER])


class TheGateRefusesAnUnbuiltRequirement(Catalogue):
    def test_it_refuses_the_shape_that_shipped_over_it(self):
        """0.14.0's shape: goals locked, the features still `building`, and the
        tracker not claiming the requirements they lock."""
        for fid in ("E1", "E2"):
            self.feature(fid, "building", area="e-maintenance")
        self.tracker("E1-R1")
        self.manifest("0.14.0", ["E1-R1", "E1-R2", "E2-R1"])
        code, said = self.act("0.14.0")
        self.assertEqual(code, 1)
        self.assertIn("not built: E1-R2", said)
        self.assertIn("E2-R1", said)
        self.assertNotIn("not built: E1-R1", said)

    def test_planned_is_refused_as_firmly_as_building(self):
        """The rule's sentence is `not built`, not `not building`. 0.15.0 locks
        features that are `planned`, which is further from built than `building`
        and would pass a gate written to the narrower sentence people quote."""
        self.feature("B6", "planned")
        self.feature("B10", "shipped")
        self.manifest("0.15.0", ["B6-R1", "B10-R1"])
        code, said = self.act("0.15.0")
        self.assertEqual(code, 1)
        self.assertIn("not built: B6-R1", said)
        self.assertNotIn("not built: B10", said)

    def test_a_withdrawn_feature_builds_nothing(self):
        self.feature("L2", "withdrawn", area="l-release")
        self.manifest("2.0.0", ["L2-R1"])
        code, said = self.act("2.0.0")
        self.assertEqual(code, 1)
        self.assertIn("not built: L2-R1", said)


class TheNarrowing(Catalogue):
    def test_a_building_feature_passes_on_the_requirements_it_has_finished(self):
        """`0.5.0`'s case, and the whole point of the narrowing.

        B3 is `building` because seven of its fifteen requirements are unbuilt.
        The eight that `0.5.0` locked are all done, and a released version must
        not be refused for the seven it never carried.
        """
        self.feature("B3", "building", requirements=15)
        self.tracker("B3-R2", "B3-R3")
        self.manifest("0.5.0", ["B3-R2", "B3-R3"])
        code, said = self.act("0.5.0")
        self.assertEqual(code, 0)
        self.assertIn("no-stubs: every requirement this version locks is built", said)

    def test_a_finished_feature_is_not_asked_of_the_tracker(self):
        """`built` and `shipped` answer for every requirement, so an empty tracker
        cannot refuse one. Without this the gate would demand a tick for work that
        shipped before the tracker had a row shape."""
        self.feature("E1", "built", area="e-maintenance")
        self.tracker()
        self.manifest("0.14.0", ["E1-R1", "E1-R2"])
        code, said = self.act("0.14.0")
        self.assertEqual(code, 0)
        self.assertIn("2 of them built", said)

    def test_a_planned_feature_is_refused_even_where_the_tracker_ticks_it(self):
        """The one refusal `gate.py` would not make.

        A catalogue calling a feature untouched and a tracker calling its
        requirements done cannot both be right, and passing it would take the more
        optimistic of two records that disagree.
        """
        self.feature("F1", "planned", area="f-extensibility")
        self.tracker("F1-R1")
        self.manifest("0.15.0", ["F1-R1"])
        code, said = self.act("0.15.0")
        self.assertEqual(code, 1)
        self.assertIn("not built: F1-R1", said)

    def test_the_line_says_how_much_of_the_feature_is_locked_and_how_much_built(self):
        """A version locking two of sixteen is a different problem from one
        locking all sixteen, and the ratio is what let that judgement be made."""
        self.feature("B3", "building", requirements=15)
        self.tracker("B3-R2")
        self.manifest("0.5.0", ["B3-R2", "B3-R3"])
        _, said = self.act("0.5.0")
        self.assertIn("locks 2 of its 15 requirements, 1 of them built", said)


class WhatNoVersionLocks(Catalogue):
    def test_a_requirement_the_train_never_locks_is_named(self):
        """F3-R15, R16, R19 and R20 are locked by no manifest at all. Nothing
        would ever ask about them, and the only run in a position to notice is one
        already looking at the feature that holds them."""
        self.feature("F3", "shipped", requirements=5, area="f-extensibility")
        self.manifest("0.16.0", ["F3-R1", "F3-R2"])
        code, said = self.act("0.16.0")
        self.assertEqual(code, 0)
        self.assertIn("locked by no manifest in the train", said)
        self.assertIn("F3-R3, F3-R4, F3-R5", said)

    def test_it_counts_what_every_manifest_locks_and_not_only_this_one(self):
        """A requirement another version carries is not a hole in the train."""
        self.feature("F3", "shipped", requirements=4, area="f-extensibility")
        self.manifest("0.16.0", ["F3-R1", "F3-R2"])
        self.manifest("0.17.0", ["F3-R3", "F3-R4"])
        code, said = self.act("0.16.0")
        self.assertEqual(code, 0)
        self.assertNotIn("locked by no manifest", said)

    def test_the_template_is_not_a_version(self):
        """It carries example goals, and reading them would hide a real hole."""
        self.feature("F3", "shipped", requirements=2, area="f-extensibility")
        pathlib.Path("70-operations/versions/TEMPLATE.toml").write_text(
            'version = "0.0.0"\ngoals = ["F3-R2"]\n', encoding="utf-8")
        self.manifest("0.16.0", ["F3-R1"])
        _, said = self.act("0.16.0")
        self.assertIn("F3-R2", said)
        self.assertIn("locked by no manifest in the train", said)


class WhatIsNotAFeature(Catalogue):
    def test_another_namespace_is_reported_rather_than_passed_over(self):
        """0.10.0 locks six `ARCH-R` goals. They name no feature and never will;
        a gate silent about them cannot be told from one that approved them."""
        self.feature("C6", "shipped", area="c-trust")
        self.manifest("0.10.0", ["ARCH-R55", "ARCH-R58", "C6-R1"])
        code, said = self.act("0.10.0")
        self.assertEqual(code, 0)
        self.assertIn("outside the feature catalogue", said)
        self.assertIn("ARCH", said)

    def test_a_goal_naming_no_catalogued_feature_cannot_be_judged(self):
        """`N9` is shaped like a feature id and names nothing. A verdict about a
        feature nobody can read is not available, so none is given."""
        self.feature("C6", "shipped", area="c-trust")
        self.manifest("0.10.0", ["N9-R1", "C6-R1"])
        code, said = self.act("0.10.0")
        self.assertEqual(code, 2)
        self.assertIn("the feature catalogue does not hold", said)

    def test_goals_are_grouped_by_feature_in_the_order_they_appear(self):
        self.assertEqual(
            check_no_stubs.grouped(["B6-R1", "B8-R1", "B6-R2"]),
            {"B6": ["B6-R1", "B6-R2"], "B8": ["B8-R1"]},
        )


class TheSilencesAreRefused(Catalogue):
    def test_an_empty_catalogue_is_not_a_pass(self):
        """Run from the wrong directory, the gate finds no unbuilt requirement —
        and a report of success about nothing is the worst answer available."""
        self.manifest("0.15.0", ["B6-R1"])
        code, said = self.act("0.15.0")
        self.assertEqual(code, 2)
        self.assertIn("no feature docs", said)

    def test_a_renamed_maturity_turns_the_gate_off_loudly(self):
        """The rule is written in five words the schema supplies. Rename one and
        a feature standing at it reads as whichever branch catches it last."""
        self.schema({"properties": {
            "id": {"pattern": "^[A-N][0-9]+$"},
            "maturity": {"enum": ["planned", "building", "done", "released"]},
        }})
        self.feature("E1", "done", area="e-maintenance")
        self.manifest("0.14.0", ["E1-R1"])
        code, said = self.act("0.14.0")
        self.assertEqual(code, 2)
        self.assertIn("built, shipped", said)

    def test_the_vocabulary_check_passes_on_the_real_schema(self):
        self.assertIsNone(check_no_stubs.vocabulary_holds(
            {"planned", "building", "built", "shipped", "withdrawn"}))


class BadInput(Catalogue):
    def test_a_missing_manifest_is_named(self):
        self.feature("B6", "planned")
        code, said = self.act("9.9.9")
        self.assertEqual(code, 2)
        self.assertIn("no manifest at", said)

    def test_a_manifest_locking_nothing_is_refused(self):
        self.feature("B6", "planned")
        self.manifest("0.15.0", [])
        code, said = self.act("0.15.0")
        self.assertEqual(code, 2)
        self.assertIn("locks no goals", said)

    def test_a_missing_tracker_is_named(self):
        """Without it a `building` feature cannot be asked about at all, and the
        gate would have to guess in whichever direction its default pointed."""
        self.feature("B6", "planned")
        self.manifest("0.15.0", ["B6-R1"])
        code, said = run_main(["--version", "0.15.0", "--status", "nowhere.md"])
        self.assertEqual(code, 2)
        self.assertIn("no tracker at", said)

    def test_a_version_that_is_not_a_version_is_refused(self):
        code, _ = self.act("../../etc/passwd")
        self.assertEqual(code, 1)


class TheRuleItself(unittest.TestCase):
    """The three answers are the ones the rule names, and no others."""

    def test_the_states_are_partitioned_the_way_the_rule_says(self):
        self.assertEqual(check_no_stubs.FINISHED, ("built", "shipped"))
        self.assertEqual(check_no_stubs.UNSTARTED, ("planned", "withdrawn"))
        self.assertEqual(check_no_stubs.PARTWAY, "building")

    def test_a_finished_feature_answers_for_every_requirement(self):
        for state in ("built", "shipped"):
            self.assertEqual(
                check_no_stubs.unfinished(["X1-R1"], {"maturity": state}, set()), []
            )

    def test_an_unstarted_feature_answers_for_none_of_them(self):
        for state in ("planned", "withdrawn", None, ""):
            self.assertEqual(
                check_no_stubs.unfinished(["X1-R1"], {"maturity": state}, {"X1-R1"}),
                ["X1-R1"],
            )

    def test_building_defers_to_the_tracker_one_requirement_at_a_time(self):
        self.assertEqual(
            check_no_stubs.unfinished(
                ["X1-R1", "X1-R2"], {"maturity": "building"}, {"X1-R1"}
            ),
            ["X1-R2"],
        )


if __name__ == "__main__":
    unittest.main()
