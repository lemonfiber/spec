#!/usr/bin/env python3
"""Coverage tests for status_lint.py — whether a tick in a tracker means anything.

The check runs as a step inside the `spec-check` reusable workflow, against the
`IMPLEMENTATION-STATUS.md` of whichever repository called it, with the spec
checked out beside it as `.spec-canonical`. The fixture here is that same shape,
so what the tests read is what CI reads. A fault here is a fault in every
repository's merge gate, so each refusal is checked by the message a maintainer
would read as well as by the exit code: a gate that fails with the wrong reason
sends someone to the wrong repository.

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_status_lint.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import status_lint  # noqa: E402

SPEC = ".spec-canonical"
TRACKER = "IMPLEMENTATION-STATUS.md"


def run_main(argv):
    """Call status_lint.main() with argv patched; return (exit code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["status_lint", *argv]
    code = 0
    try:
        with contextlib.redirect_stdout(out):
            result = status_lint.main()
        code = result if isinstance(result, int) else 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Workspace(unittest.TestCase):
    """A caller repository holding a tracker, with the spec checked out beside it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path(f"{SPEC}/70-operations/versions").mkdir(parents=True)
        pathlib.Path(f"{SPEC}/10-functional/features").mkdir(parents=True)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def requirements(self, feature="G7", highest=13):
        """A feature document defining R1 up to `highest`, as the spec writes them."""
        pathlib.Path(f"{SPEC}/10-functional/features/f.md").write_text(
            "\n".join(f"| **{feature}-R{n}** | something |" for n in range(1, highest + 1)),
            encoding="utf-8")

    def manifest(self, version, milestone, goals):
        goal_list = ", ".join(f'"{g}"' for g in goals)
        line = f'milestone = "{milestone}"\n' if milestone else ""
        pathlib.Path(f"{SPEC}/70-operations/versions/{version}.toml").write_text(
            f'version = "{version}"\n{line}goals = [{goal_list}]\n', encoding="utf-8")

    def spec_tree(self, feature="G7", highest=13, milestone="M5", version="0.7.0"):
        """One feature's requirements, all of them locked by one version."""
        self.requirements(feature, highest)
        self.manifest(version, milestone, [f"{feature}-R{n}" for n in range(1, highest + 1)])

    def mention(self, text):
        """Prose elsewhere in the spec that names an identifier without defining it.

        An ADR, a roadmap note, a paragraph of reasoning — every one of these
        cites requirements, and none of them declares one.
        """
        docs = pathlib.Path(f"{SPEC}/20-architecture")
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "note.md").write_text(text, encoding="utf-8")

    def tracker(self, body):
        pathlib.Path(TRACKER).write_text(body, encoding="utf-8")
        return TRACKER

    def lint(self, body):
        """The common case: the one-feature spec, and a tracker read against it."""
        self.spec_tree()
        return run_main(["--status", self.tracker(body), "--spec", SPEC])


class Passing(Workspace):
    """Every tracker the gate must let through. A gate that grows stricter by
    accident blocks work that is correct, which is the more expensive failure."""

    def test_a_clean_tracker_passes(self):
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n")
        self.assertEqual(code, 0, out)
        self.assertIn("backed by the spec", out)

    def test_a_range_stopping_at_the_last_requirement_passes(self):
        # The boundary itself: R13 of thirteen is the last one there is, not one past.
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `G7-R13..R13` | ✅ | y |\n")
        self.assertEqual(code, 0, out)

    def test_a_mention_past_the_last_definition_leaves_an_honest_claim_alone(self):
        # The ceiling reads definitions. Prose that names `G7-R20` says nothing
        # about G7's thirteen requirements, in either direction.
        self.spec_tree()
        self.mention("A roadmap note that mentions G7-R20 in passing.\n")
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 0, out)

    def test_naming_an_extra_version_is_allowed(self):
        # A milestone whose groundwork shipped early under another's version
        # should be free to say so.
        code, out = self.lint(
            "## M5 — Trust · `0.7.0`, and `0.5.0` before it\n\n| x | `G7-R1..R13` | ✅ | y |\n")
        self.assertEqual(code, 0, out)

    def test_a_heading_for_a_milestone_no_manifest_claims_is_left_alone(self):
        code, out = self.lint("## M9 — Later · no version yet\n\n| x | `G7-R1..R13` | ✅ | y |\n")
        self.assertEqual(code, 0, out)

    def test_a_milestone_shipping_in_two_versions_may_name_both(self):
        self.spec_tree()
        self.manifest("0.8.0", "M5", ["G7-R1"])
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0` and `0.8.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n"),
            "--spec", SPEC])
        self.assertEqual(code, 0, out)

    def test_an_unticked_row_claims_nothing(self):
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R13` | ☐ | y |\n")
        self.assertEqual(code, 0, out)

    def test_a_tracker_with_no_claims_at_all_passes(self):
        code, out = self.lint("# nothing here yet\n")
        self.assertEqual(code, 0, out)

    def test_the_template_manifest_is_not_a_version(self):
        # TEMPLATE.toml is the shape a new manifest is copied from, not a release —
        # counting its milestone would invent a version nothing ships in.
        self.spec_tree()
        pathlib.Path(f"{SPEC}/70-operations/versions/TEMPLATE.toml").write_text(
            'version = "X.Y.Z"\nmilestone = "M5"\ngoals = ["G7-R1"]\n', encoding="utf-8")
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 0, out)

    def test_a_manifest_naming_no_milestone_still_locks_its_goals(self):
        # `milestone` is optional; `goals` is what a tick is measured against.
        self.requirements(highest=1)
        self.manifest("0.7.0", None, ["G7-R1"])
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · no version\n\n| x | `G7-R1` | ✅ |\n"), "--spec", SPEC])
        self.assertEqual(code, 0, out)


class Refusals(Workspace):
    """Every way the tracker can claim something the spec does not back, read by
    the message as well as the code."""

    def test_a_range_past_the_last_requirement_is_a_fault(self):
        # G7 defines thirteen; claiming fourteen mints one and ticks it at once,
        # so both refusals fire — the row overshoots and the tick is unbacked.
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R14` | ✅ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("claims G7-R14, but G7 defines up to R13", out)
        self.assertIn(f"{TRACKER}:3:", out)          # the row, so it can be found
        self.assertIn("2 claim(s) the spec does not back", out)

    def test_an_overshoot_is_faulted_even_unticked(self):
        # A row naming a requirement nobody wrote is wrong before it is ticked,
        # and on its own it is the only thing said.
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R14` | ☐ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("defines up to R13", out)
        self.assertNotIn("locked by no version", out)
        self.assertIn("1 claim(s) the spec does not back", out)

    def test_a_mention_past_the_last_definition_does_not_raise_the_ceiling(self):
        """The ceiling is what the spec defines, not what it happens to say.

        Built from citations, one line of prose naming `G7-R20` lifted G7 from
        thirteen to twenty and took the overshoot check with it — silently, for
        every number in between. `integrity.py` refuses stray citations in the
        spec repository, so the hole rarely had anything to feed on; two gates
        holding each other up is not the same as a gate that works.

        Unticked, so the overshoot is the only thing that can fire and the exit
        code answers for it alone.
        """
        self.spec_tree()
        self.mention("A roadmap note that mentions G7-R20 in passing.\n")
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R14` | ☐ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 1, out)
        self.assertIn("claims G7-R14, but G7 defines up to R13", out)
        self.assertIn("1 claim(s) the spec does not back", out)

    def test_a_definition_under_dot_git_is_not_read(self):
        # `integrity.py` and `spec_refs.py` both skip `.git`, so a row there is
        # vetted by nothing — the one place the two gates cannot cover between them.
        self.spec_tree()
        pathlib.Path(f"{SPEC}/.git").mkdir()
        pathlib.Path(f"{SPEC}/.git/x.md").write_text(
            "| **G7-R14** | invented |\n", encoding="utf-8")
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R14` | ☐ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 1, out)
        self.assertIn("defines up to R13", out)

    def test_a_heading_that_omits_one_of_its_versions_is_a_fault(self):
        code, out = self.lint("## M5 — Trust · `0.9.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("M5 ships in 0.7.0 but does not name 0.7.0", out)
        self.assertIn(f"{TRACKER}:1:", out)

    def test_an_omitted_version_is_named_even_when_another_is_right(self):
        self.spec_tree()
        self.manifest("0.8.0", "M5", ["G7-R1"])
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `G7-R1..R13` | ✅ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 1)
        self.assertIn("ships in 0.7.0, 0.8.0 but does not name 0.8.0", out)

    def test_a_tick_no_version_locks_is_a_fault(self):
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `Z9-R1` | ✅ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("marked done but locked by no version: Z9-R1", out)

    def test_a_missing_manifest_entry_is_not_reported_as_a_bad_row(self):
        # The failure this test exists for: a tick on a requirement the spec
        # defines but no manifest locks. The cause is the manifest, not the
        # tracker row, and the message has to send the reader to the manifest.
        self.requirements(feature="ARCH", highest=48)
        self.manifest("0.7.0", "M5", ["ARCH-R47"])
        code, out = run_main(["--status", self.tracker(
            "## M5 — Trust · `0.7.0`\n\n| x | `ARCH-R48` | ✅ | y |\n"), "--spec", SPEC])
        self.assertEqual(code, 1)
        self.assertIn("locked by no version: ARCH-R48", out)
        self.assertNotIn("defines up to", out)      # not an overshoot; do not say it is

    def test_a_feature_the_spec_never_defines_is_only_faulted_once(self):
        # Nothing to overshoot when nothing is defined, so only the tick is faulted.
        code, out = self.lint("## M5 — Trust · `0.7.0`\n\n| x | `ZZ1-R1..R5` | ✅ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("locked by no version: ZZ1-R1, ZZ1-R2, ZZ1-R3, ZZ1-R4, ZZ1-R5", out)
        self.assertNotIn("defines up to", out)

    def test_every_fault_is_reported_not_just_the_first(self):
        code, out = self.lint(
            "## M5 — Trust · `0.9.0`\n\n| x | `G7-R1..R14` | ✅ | y |\n"
            "| x | `Z9-R1` | ✅ | y |\n")
        self.assertEqual(code, 1)
        self.assertIn("does not name 0.7.0", out)
        self.assertIn("defines up to R13", out)
        self.assertIn("locked by no version: G7-R14, Z9-R1", out)
        self.assertIn("3 claim(s) the spec does not back", out)


class Unlocked(Workspace):
    """`unlocked()` is the refusal that fires most, and it is set arithmetic.
    Both sets empty, either one empty, and every overlap."""

    def ticks(self, *ids):
        return [f"| x | `{i}` | ✅ | y |" for i in ids]

    def test_nothing_ticked_and_nothing_locked(self):
        self.assertEqual(status_lint.unlocked("S", [], set()), [])

    def test_nothing_ticked_but_something_locked(self):
        self.assertEqual(status_lint.unlocked("S", [], {"A1-R1"}), [])

    def test_locked_and_unticked(self):
        lines = self.ticks("A1-R1")
        self.assertEqual(status_lint.unlocked("S", lines, {"A1-R1", "A1-R2"}), [])

    def test_ticked_and_locked(self):
        self.assertEqual(status_lint.unlocked("S", self.ticks("A1-R1"), {"A1-R1"}), [])

    def test_ticked_and_unlocked(self):
        faults = status_lint.unlocked("S", self.ticks("A1-R1"), set())
        self.assertEqual(faults, ["S: marked done but locked by no version: A1-R1"])

    def test_ticked_with_only_some_of_it_locked(self):
        faults = status_lint.unlocked("S", self.ticks("A1-R1", "A1-R2"), {"A1-R1"})
        self.assertEqual(faults, ["S: marked done but locked by no version: A1-R2"])

    def test_several_orphans_are_named_in_order(self):
        faults = status_lint.unlocked("S", self.ticks("B1-R2", "A1-R1"), set())
        self.assertEqual(faults, ["S: marked done but locked by no version: A1-R1, B1-R2"])

    def test_a_row_without_a_tick_claims_nothing(self):
        self.assertEqual(status_lint.unlocked("S", ["| x | `A1-R1` | ☐ | y |"], set()), [])

    def test_a_ticked_range_counts_every_requirement_it_spans(self):
        faults = status_lint.unlocked("S", ["| x | `A1-R1..R3` | ✅ |"], {"A1-R1", "A1-R3"})
        self.assertEqual(faults, ["S: marked done but locked by no version: A1-R2"])

    def test_a_range_written_with_both_prefixes_reads_the_same(self):
        faults = status_lint.unlocked("S", ["| x | `A1-R1..A1-R3` | ✅ |"], {"A1-R1"})
        self.assertEqual(faults, ["S: marked done but locked by no version: A1-R2, A1-R3"])


class Headings(Workspace):
    """How far a heading's prose reaches when it names its versions."""

    def test_a_version_named_within_the_preamble_is_read(self):
        found = status_lint.headings(["## M5 — Trust", *[""] * 7, "ships in `0.7.0`"])
        self.assertEqual(found, [(1, "M5", {"0.7.0"})])

    def test_a_version_named_past_the_preamble_is_not(self):
        # Nine lines is the window; a version twenty rows into the table is a
        # citation in a row, not the heading's claim about itself.
        found = status_lint.headings(["## M5 — Trust", *[""] * 20, "row about `0.7.0`"])
        self.assertEqual(found, [(1, "M5", set())])

    def test_a_line_that_is_not_a_heading_contributes_nothing(self):
        self.assertEqual(status_lint.headings(["### M5 — Trust", "text `0.7.0`"]), [])


class Usage(Workspace):
    """The two arguments come from a workflow's inputs; both are checked."""

    def test_a_path_outside_the_working_tree_is_refused(self):
        # A check that will read any file it is pointed at is a way to read any file.
        self.spec_tree()
        code, out = run_main(["--status", "/etc/hosts", "--spec", SPEC])
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", out)

    def test_a_spec_outside_the_working_tree_is_refused(self):
        self.spec_tree()
        code, out = run_main(["--status", self.tracker("# x\n"), "--spec", "/etc"])
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", out)

    def test_a_missing_tracker_is_a_usage_error(self):
        self.spec_tree()
        code, out = run_main(["--status", "absent.md", "--spec", SPEC])
        self.assertEqual(code, 2)
        self.assertIn("no tracker", out)

    def test_a_spec_without_manifests_is_a_usage_error(self):
        # The shared fixture always makes the versions directory; this is the one
        # test about it being absent, so it takes it away again.
        shutil.rmtree(f"{SPEC}/70-operations")
        code, out = run_main(["--status", self.tracker("# nothing\n"), "--spec", SPEC])
        self.assertEqual(code, 2)
        self.assertIn("no version manifests", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
