#!/usr/bin/env python3
"""Coverage tests for spec_check.py — the gate that decides whether a change may
merge anywhere in the org.

The check runs inside the `spec-check` reusable workflow, against a text file
holding the calling repository's pull request body and commit messages, with the
spec checked out beside it. The fixtures here are that same shape.

Each refusal is checked by the message a maintainer would read as well as by the
exit code: a gate that fails with the wrong reason sends someone to the wrong
repository. The Dependabot cases are checked in both directions — allowed for the
account GitHub names, refused for anyone claiming to be it (Q-R66).

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_spec_check.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec_check  # noqa: E402

SPEC = ".spec-canonical"
TEXT = ".pr-text.txt"
DIFF = ".pr-diff.txt"

# A requirement is defined by its table row, and an ADR by its filename.
ROWS = """# Governance

| ID | Requirement |
|----|-------------|
| **GOV-R12** | Routine maintenance MUST cite a governance identifier. |
| **Q-R55** | Dependency-update automation MUST satisfy spec-check unattended. |
| **GOV-R90** | *Withdrawn — carried to [GOV-R12](governance.md) when the rule moved. The number is not reused.* |
| **GOV-R91** | *Superseded by [GOV-R12](governance.md).* |
"""


def run_main(argv):
    """Call spec_check.main() with argv patched; return (exit code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["spec_check", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = spec_check.main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
    return code, out.getvalue()


class GateCase(unittest.TestCase):
    """A temporary repo root with a spec checkout beside a pull request's text."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.saved_cwd = os.getcwd()
        os.chdir(self.root)
        (self.root / SPEC).mkdir()
        (self.root / SPEC / "governance.md").write_text(ROWS, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.saved_cwd)

    def check(self, text, *extra, spec_dir=SPEC, text_file=TEXT):
        (self.root / TEXT).write_text(text, encoding="utf-8")
        return run_main(
            ["--spec-dir", spec_dir, "--text-file", text_file, *extra]
        )

    def check_diff(self, diff, text="Spec: GOV-R12\n", *extra, diff_file=DIFF):
        """The same gate, handed a change's diff as well as its text."""
        (self.root / DIFF).write_text(diff, encoding="utf-8")
        return self.check(text, "--diff-file", diff_file, *extra)


def a_diff(*added, path="tests/SomeTest.php"):
    """A unified diff adding the given lines, shaped as git writes one."""
    body = "".join(f"+{line}\n" for line in added)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(added)} @@\n"
        f"{body}"
    )


class Citations(GateCase):
    def test_a_known_identifier_passes(self):
        code, out = self.check("Spec: GOV-R12\n")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)

    def test_no_trailer_is_refused(self):
        code, out = self.check("Just a change, no trailer here.\n")
        self.assertEqual(code, 1)
        self.assertIn("no `Spec:` citation found", out)

    def test_an_identifier_that_does_not_exist_is_refused(self):
        code, out = self.check("Spec: GOV-R999\n")
        self.assertEqual(code, 1)
        self.assertIn("do not exist on spec@main: GOV-R999", out)

    def test_an_adr_filename_defines_an_identifier(self):
        decisions = self.root / SPEC / "00-overview" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "0016-dependabot-over-renovate.md").write_text("x", encoding="utf-8")
        (decisions / "notes.txt").write_text("not an ADR", encoding="utf-8")
        code, out = self.check("Spec: ADR-0016\n")
        self.assertEqual(code, 0)
        self.assertIn("cites ADR-0016", out)

    def test_a_withdrawn_identifier_is_refused_and_says_where_it_went(self):
        code, out = self.check("Spec: GOV-R90\n")
        self.assertEqual(code, 1)
        self.assertIn("GOV-R90 is retired", out)
        self.assertIn("carried to [GOV-R12]", out)

    def test_a_superseded_identifier_is_refused(self):
        code, out = self.check("Spec: GOV-R91\n")
        self.assertEqual(code, 1)
        self.assertIn("GOV-R91 is retired", out)

    def test_a_live_identifier_beside_a_retired_one_does_not_rescue_it(self):
        code, out = self.check("Spec: GOV-R12, GOV-R90\n")
        self.assertEqual(code, 1)
        self.assertIn("GOV-R90 is retired", out)

    def test_a_git_directory_is_not_read_for_identifiers(self):
        git = self.root / SPEC / ".git"
        git.mkdir()
        (git / "stray.md").write_text("| **GOV-R98** | not a requirement |\n", encoding="utf-8")
        code, out = self.check("Spec: GOV-R98\n")
        self.assertEqual(code, 1)
        self.assertIn("GOV-R98", out)

    def test_a_git_directory_cannot_retire_a_live_identifier(self):
        git = self.root / SPEC / ".git"
        git.mkdir()
        (git / "stray.md").write_text(
            "| **GOV-R12** | *Withdrawn — by a file nobody wrote.* |\n", encoding="utf-8"
        )
        code, out = self.check("Spec: GOV-R12\n")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)


class Usage(GateCase):
    def test_a_missing_spec_checkout_is_a_usage_error(self):
        code, out = self.check("Spec: GOV-R12\n", spec_dir="nowhere")
        self.assertEqual(code, 2)
        self.assertIn("spec dir not found", out)

    def test_a_text_file_outside_the_tree_is_refused(self):
        code, out = self.check("Spec: GOV-R12\n", text_file="/etc/hostname")
        self.assertEqual(code, 2)
        self.assertIn("must be within the working directory", out)

    def test_a_spec_checkout_defining_nothing_cannot_verify(self):
        (self.root / SPEC / "governance.md").write_text("# Nothing here\n", encoding="utf-8")
        code, out = self.check("Spec: GOV-R12\n")
        self.assertEqual(code, 2)
        self.assertIn("cannot verify", out)


class Dependabot(GateCase):
    """Q-R55: the one author that cannot write a trailer, and no one else."""

    def test_dependabot_needs_no_trailer(self):
        code, out = self.check("Bumps serde from 1.0.1 to 1.0.2.\n", "--pr-author", "dependabot[bot]")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)

    def test_a_human_claiming_to_be_dependabot_is_still_refused(self):
        code, out = self.check(
            "Bumps serde from 1.0.1 to 1.0.2.\n\n"
            "Signed-off-by: dependabot[bot] <noreply@github.com>\n"
            "Author: dependabot[bot]\n",
            "--pr-author",
            "not-dependabot",
        )
        self.assertEqual(code, 1)
        self.assertIn("no `Spec:` citation found", out)

    def test_a_lookalike_login_is_refused(self):
        code, _ = self.check("Bumps serde.\n", "--pr-author", "dependabot")
        self.assertEqual(code, 1)

    def test_no_author_given_is_refused(self):
        code, _ = self.check("Bumps serde.\n")
        self.assertEqual(code, 1)

    def test_the_supplied_citation_is_still_checked_for_existence(self):
        (self.root / SPEC / "governance.md").write_text(
            "| **Q-R55** | Something else entirely. |\n", encoding="utf-8"
        )
        code, out = self.check("Bumps serde.\n", "--pr-author", "dependabot[bot]")
        self.assertEqual(code, 1)
        self.assertIn("do not exist on spec@main: GOV-R12", out)

    def test_dependabot_may_still_cite_something_of_its_own(self):
        code, out = self.check("Spec: Q-R55\n", "--pr-author", "dependabot[bot]")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12, Q-R55", out)


class AMergeGroup(GateCase):
    """`--citation-optional`: the event with no pull request to read.

    A merge queue asks this gate about a batch on a branch of its own, and that
    event carries no body and no author — two of the three places GOV-R2 looks.
    So presence stops being required and GOV-R3 does not, and both halves of
    that are held here, because a flag that quietly took the whole gate with it
    would look exactly like this one from the outside.
    """

    def test_citing_nothing_is_not_a_refusal(self):
        code, out = self.check("A commit message with no trailer.\n", "--citation-optional")
        self.assertEqual(code, 0)
        self.assertIn("nothing cited", out)

    def test_an_identifier_that_does_not_exist_is_still_refused(self):
        code, out = self.check("Spec: GOV-R999\n", "--citation-optional")
        self.assertEqual(code, 1)
        self.assertIn("do not exist on spec@main: GOV-R999", out)

    def test_what_is_cited_is_still_resolved_and_reported(self):
        code, out = self.check("Spec: GOV-R12\n", "--citation-optional")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)

    def test_without_the_flag_the_same_text_is_refused(self):
        # The pair, rather than the permissive half alone: this is the line the
        # flag moves, and a test that only ever passes it cannot show that.
        code, out = self.check("A commit message with no trailer.\n")
        self.assertEqual(code, 1)
        self.assertIn("no `Spec:` citation found", out)



class WhatAFileNames(GateCase):
    """GOV-R3 over the lines a change adds, not only over its trailer."""

    def test_an_identifier_a_file_names_is_resolved(self):
        code, out = self.check_diff(a_diff("// GOV-R12 — the rule this keeps."))
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)

    def test_a_number_that_does_not_exist_is_refused(self):
        code, out = self.check_diff(a_diff("// GOV-R120 — the rule this keeps."))
        self.assertEqual(code, 1)
        self.assertIn("names identifiers that do not exist", out)
        self.assertIn("GOV-R120", out)

    def test_a_perfect_trailer_does_not_rescue_a_file(self):
        # The whole point of the second half: the citation can be impeccable and
        # the comment beside the rule can still send somebody nowhere.
        code, out = self.check_diff(
            a_diff("// GOV-R120 — the rule this keeps."), "Spec: GOV-R12\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("GOV-R120", out)

    def test_the_gate_does_not_read_its_own_tests(self):
        # This file names identifiers that do not resolve, because that is what a
        # test of "refuse an unknown identifier" is. Reading it would have the
        # gate refuse the change that teaches it to refuse.
        code, out = self.check_diff(
            a_diff("GOV-R120", path="scripts/test_spec_check.py"), "Spec: GOV-R12\n"
        )
        self.assertEqual(code, 0, out)

    def test_the_exemption_is_two_paths_and_not_a_pattern(self):
        # A test's own title is exactly the kind of citation this check exists to
        # resolve, so exempting `tests/` anywhere would be a hole wide enough to
        # walk a repository through.
        code, out = self.check_diff(
            a_diff("GOV-R120", path="scripts/test_something_else.py"), "Spec: GOV-R12\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("GOV-R120", out)

    def test_a_repository_declares_a_fixture_of_its_own(self):
        # The Rust stack renders a withdrawn requirement and asserts the
        # strikethrough. Read without an answer for that, the gate refuses the
        # next change touching the line, and the only way to satisfy it is to
        # write the fixture out of a real requirement number.
        fixtures = self.root / ".github"
        fixtures.mkdir(parents=True, exist_ok=True)
        (self.root / "render.rs").write_text("fixture", encoding="utf-8")
        (fixtures / "spec-check-fixtures").write_text(
            "# names ids that do not resolve, on purpose\nrender.rs\n", encoding="utf-8"
        )
        code, out = self.check_diff(
            a_diff("Gone GOV-R120 (withdrawn)", path="render.rs"), "Spec: GOV-R12\n"
        )
        self.assertEqual(code, 0, out)
        self.assertIn("not read for identifiers", out)
        self.assertIn("render.rs", out)

    def test_a_declaration_names_a_path_and_not_a_pattern(self):
        fixtures = self.root / ".github"
        fixtures.mkdir(parents=True, exist_ok=True)
        (fixtures / "spec-check-fixtures").write_text("tests/*\n", encoding="utf-8")
        code, out = self.check_diff(a_diff("GOV-R12"), "Spec: GOV-R12\n")
        self.assertEqual(code, 2)
        self.assertIn("names a pattern, not a path", out)

    def test_a_declaration_that_stopped_applying_is_refused(self):
        # A list carrying an entry nobody can point at is one nobody trusts
        # enough to shorten, so the day the fixture moves the gate says which
        # line to delete rather than quietly reading one file more.
        fixtures = self.root / ".github"
        fixtures.mkdir(parents=True, exist_ok=True)
        (fixtures / "spec-check-fixtures").write_text("gone.rs\n", encoding="utf-8")
        code, out = self.check_diff(a_diff("GOV-R12"), "Spec: GOV-R12\n")
        self.assertEqual(code, 2)
        self.assertIn("names a file that is not there: gone.rs", out)

    def test_a_declaration_does_not_cover_a_file_it_did_not_name(self):
        fixtures = self.root / ".github"
        fixtures.mkdir(parents=True, exist_ok=True)
        (self.root / "render.rs").write_text("fixture", encoding="utf-8")
        (fixtures / "spec-check-fixtures").write_text("render.rs\n", encoding="utf-8")
        code, out = self.check_diff(
            a_diff("GOV-R120", path="other.rs"), "Spec: GOV-R12\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("GOV-R120", out)

    def test_a_removed_line_is_not_this_change_to_answer_for(self):
        diff = (
            "diff --git a/x.md b/x.md\n--- a/x.md\n+++ b/x.md\n"
            "@@ -1 +1 @@\n-GOV-R120 was here\n+GOV-R12 is here\n"
        )
        code, _ = self.check_diff(diff)
        self.assertEqual(code, 0)

    def test_the_file_header_is_not_read_as_an_added_line(self):
        # `+++ b/GOV-R120.md` starts with a plus and is not a line anybody wrote.
        code, _ = self.check_diff(a_diff("nothing here", path="GOV-R120.md"))
        self.assertEqual(code, 0)

    def test_a_family_the_spec_never_defined_is_prose(self):
        # `X-R1..R4` means *any requirement of any family*. The limit is stated
        # in `named_in`, and this is what it costs and buys.
        code, _ = self.check_diff(a_diff("/// counted as `X-R1..R4`, the four it means"))
        self.assertEqual(code, 0)

    def test_a_merge_group_citing_nothing_is_still_asked(self):
        # The event where presence is not required returns early on the trailer.
        # GOV-R3 is the half a queue can change, so it runs before that.
        code, out = self.check_diff(
            a_diff("// GOV-R120"), "no trailer at all\n", "--citation-optional"
        )
        self.assertEqual(code, 1)
        self.assertIn("GOV-R120", out)

    def test_no_diff_given_leaves_the_gate_as_it_was(self):
        code, out = self.check("Spec: GOV-R12\n")
        self.assertEqual(code, 0)
        self.assertIn("cites GOV-R12", out)

    def test_a_retired_number_in_prose_is_not_refused(self):
        # A comment recording a withdrawal has to name the number. The trailer is
        # where a citation is made and where GOV-R8 is enforced.
        code, _ = self.check_diff(a_diff("// GOV-R90 was withdrawn; this reads GOV-R12 now."))
        self.assertEqual(code, 0)

    def test_a_diff_that_did_not_arrive_is_a_usage_error(self):
        # Never 1: an absent diff is a fault on the gate's side, and closing
        # somebody's pull request for it is the one outcome that must not happen.
        code, out = self.check("Spec: GOV-R12\n", "--diff-file", ".no-such-diff.txt")
        self.assertEqual(code, 2)
        self.assertIn("diff-file not found", out)

    def test_a_diff_outside_the_tree_is_refused(self):
        code, out = self.check("Spec: GOV-R12\n", "--diff-file", "/etc/hosts")
        self.assertEqual(code, 2)
        self.assertIn("diff-file must be within", out)

if __name__ == "__main__":
    unittest.main(verbosity=2)
