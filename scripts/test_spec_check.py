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

# A requirement is defined by its table row, and an ADR by its filename.
ROWS = """# Governance

| ID | Requirement |
|----|-------------|
| **GOV-R12** | Routine maintenance MUST cite a governance identifier. |
| **Q-R55** | Dependency-update automation MUST satisfy spec-check unattended. |
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

    def test_a_git_directory_is_not_read_for_identifiers(self):
        git = self.root / SPEC / ".git"
        git.mkdir()
        (git / "stray.md").write_text("| **GOV-R98** | not a requirement |\n", encoding="utf-8")
        code, out = self.check("Spec: GOV-R98\n")
        self.assertEqual(code, 1)
        self.assertIn("GOV-R98", out)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
