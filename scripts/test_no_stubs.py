#!/usr/bin/env python3
"""The no-stub gate is shown refusing a stub — OPS-R54, Q-R66.

`0.14.0` locked five features whose catalogue files said `building`, and the only
thing that caught it was somebody reading six files by hand on the day. So the
first thing asserted here is not that the gate passes: it is that it *refuses*,
and refuses by name, the exact shape that shipped over it.

The two silences get the same treatment. A gate that reads an empty catalogue
finds no unfinished feature, and a gate whose vocabulary the schema has renamed
finds none either; both would print a pass and mean nothing by it. Each is driven
into the failing state and checked for saying so.

Stdlib unittest, no dependencies. The fixtures are a real directory tree rather
than patched functions, because what the gate reads — a glob, a schema file, a
frontmatter block — is exactly what a patched reader would stop testing.
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

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def schema(self, body):
        path = pathlib.Path(catalogue.SCHEMA_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    def feature(self, fid, maturity, title="A feature", requirements=3, area="b-running"):
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


class TheCatalogueIsReadOnce(Catalogue):
    def test_a_feature_doc_is_found_by_its_frontmatter(self):
        self.feature("B6", "planned", title="Remote control")
        found = catalogue.features()
        self.assertEqual(sorted(found), ["B6"])
        self.assertEqual(found["B6"]["title"], "Remote control")
        self.assertTrue(found["B6"]["path"].endswith("b6-thing.md"))

    def test_a_page_with_no_frontmatter_is_not_a_feature(self):
        """A README sitting in an area directory is not a stub of anything."""
        directory = pathlib.Path("10-functional/features/b-running")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "b0-readme.md").write_text("# Running it\n", encoding="utf-8")
        (directory / "b7-withdrawn.md").write_text(
            "---\ntitle: no id here\n---\n", encoding="utf-8"
        )
        self.assertEqual(catalogue.features(), {})

    def test_the_enums_come_from_the_schema(self):
        self.assertEqual(catalogue.enum("maturity"), set(SCHEMA["properties"]["maturity"]["enum"]))
        self.assertEqual(catalogue.id_pattern(), "^[A-N][0-9]+$")


class TheGateRefusesAStub(Catalogue):
    def test_it_refuses_the_shape_that_shipped_over_it(self):
        """0.14.0's shape: goals locked, four of the features still `building`.

        Named individually rather than counted, because the refusal OPS-R54 asks
        for is one somebody can act on without opening five files.
        """
        for fid in ("E1", "E2", "E3", "E4"):
            self.feature(fid, "building" if fid != "E1" else "built", area="e-maintenance")
        self.manifest("0.14.0", [f"{f}-R1" for f in ("E1", "E2", "E3", "E4")])
        code, said = run_main(["--version", "0.14.0"])
        self.assertEqual(code, 1)
        for fid in ("E2", "E3", "E4"):
            self.assertIn(f"{fid} (building)", said)
        self.assertNotIn("E1 (", said)

    def test_planned_is_refused_as_firmly_as_building(self):
        """The rule's sentence is `neither built nor shipped`, not `not building`.

        0.15.0 locks four features that are `planned`, which is further from
        finished than `building` and would pass a gate written to the narrower
        sentence people tend to quote.
        """
        self.feature("B6", "planned")
        self.feature("B10", "shipped")
        self.manifest("0.15.0", ["B6-R1", "B6-R2", "B10-R1"])
        code, said = run_main(["--version", "0.15.0"])
        self.assertEqual(code, 1)
        self.assertIn("B6 (planned)", said)
        self.assertNotIn("B10 (", said)

    def test_a_finished_feature_passes_and_says_which(self):
        self.feature("E1", "built")
        self.feature("G8", "shipped", area="g-ux")
        self.manifest("0.14.0", ["E1-R1", "E1-R2", "G8-R1"])
        code, said = run_main(["--version", "0.14.0"])
        self.assertEqual(code, 0)
        self.assertIn("no-stubs: every feature this version locks is finished", said)
        self.assertIn("E1", said)
        self.assertIn("G8", said)

    def test_the_refusal_says_how_much_of_the_feature_is_locked(self):
        """A version locking two of sixteen requirements is a different problem
        from one locking all sixteen, and the refusal has to tell them apart."""
        self.feature("B3", "building", requirements=15)
        self.manifest("0.5.0", ["B3-R2", "B3-R3"])
        code, said = run_main(["--version", "0.5.0"])
        self.assertEqual(code, 1)
        self.assertIn("locks 2 of its 15 requirements", said)


class WhatIsNotAFeature(Catalogue):
    def test_another_namespace_is_reported_rather_than_passed_over(self):
        """0.10.0 locks six `ARCH-R` goals. They name no feature and never will;
        a gate silent about them cannot be told from one that approved them."""
        self.feature("C6", "shipped", area="c-trust")
        self.manifest("0.10.0", ["ARCH-R55", "ARCH-R58", "C6-R1"])
        code, said = run_main(["--version", "0.10.0"])
        self.assertEqual(code, 0)
        self.assertIn("outside the feature catalogue", said)
        self.assertIn("ARCH", said)

    def test_a_goal_naming_no_catalogued_feature_cannot_be_judged(self):
        """`N9` is shaped like a feature id and names nothing. A verdict about a
        feature nobody can read is not available, so none is given."""
        self.feature("C6", "shipped", area="c-trust")
        self.manifest("0.10.0", ["N9-R1", "C6-R1"])
        code, said = run_main(["--version", "0.10.0"])
        self.assertEqual(code, 2)
        self.assertIn("the feature catalogue does not hold", said)

    def test_a_repeated_feature_is_listed_once(self):
        self.assertEqual(
            check_no_stubs.goal_features(["B6-R1", "B6-R2", "B8-R1", "B6-R3"]),
            ["B6", "B8"],
        )


class TheSilencesAreRefused(Catalogue):
    def test_an_empty_catalogue_is_not_a_pass(self):
        """Run from the wrong directory, the gate finds no unfinished feature —
        and a report of success about nothing is the worst answer available."""
        self.manifest("0.15.0", ["B6-R1"])
        code, said = run_main(["--version", "0.15.0"])
        self.assertEqual(code, 2)
        self.assertIn("no feature docs", said)

    def test_a_renamed_maturity_turns_the_gate_off_loudly(self):
        """The rule is written in two words the schema supplies. Rename either and
        every feature reads as unfinished — or, if the rule were written the other
        way round, as finished. Refuse instead of deciding."""
        self.schema({"properties": {
            "id": {"pattern": "^[A-N][0-9]+$"},
            "maturity": {"enum": ["planned", "building", "done", "released"]},
        }})
        self.feature("E1", "done", area="e-maintenance")
        self.manifest("0.14.0", ["E1-R1"])
        code, said = run_main(["--version", "0.14.0"])
        self.assertEqual(code, 2)
        self.assertIn("built, shipped", said)

    def test_the_vocabulary_check_passes_on_the_real_schema(self):
        self.assertIsNone(check_no_stubs.vocabulary_holds({"built", "shipped", "planned"}))


class BadInput(Catalogue):
    def test_a_missing_manifest_is_named(self):
        self.feature("B6", "planned")
        code, said = run_main(["--version", "9.9.9"])
        self.assertEqual(code, 2)
        self.assertIn("no manifest at", said)

    def test_a_manifest_locking_nothing_is_refused(self):
        self.feature("B6", "planned")
        self.manifest("0.15.0", [])
        code, said = run_main(["--version", "0.15.0"])
        self.assertEqual(code, 2)
        self.assertIn("locks no goals", said)

    def test_a_version_that_is_not_a_version_is_refused(self):
        code, _ = run_main(["--version", "../../etc/passwd"])
        self.assertEqual(code, 1)


class TheRuleItself(unittest.TestCase):
    """The gate's two accepted states are the two the rule names, and no others."""

    def test_only_built_and_shipped_are_finished(self):
        self.assertEqual(check_no_stubs.FINISHED, ("built", "shipped"))
        for state in ("planned", "building", "withdrawn", None, ""):
            self.assertTrue(check_no_stubs.unfinished(state), state)
        for state in ("built", "shipped"):
            self.assertFalse(check_no_stubs.unfinished(state), state)


if __name__ == "__main__":
    unittest.main()
