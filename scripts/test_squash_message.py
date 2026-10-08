#!/usr/bin/env python3
"""Coverage tests for squash_message.py — GOV-R62, Q-R66.

The pull request is handed over in the shapes the workflow writes from the API,
and the spec is a directory holding one page of rows, so each of the three asks
is driven on its own: the title, the citation and the sign-off. The exemptions
are where the care goes. A bot's pull request and a merge commit pass by design,
and an exemption nothing tests is one that widens unnoticed.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_squash_message.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import runpy
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import squash_message as gate

SPEC = ".spec-canonical"
PULL = "pull.json"
COMMITS = "commits.jsonl"

ROWS = """# Rules

| ID | Requirement |
|----|-------------|
| **ZZ-R1** | A rule that holds. |
| **ZZ-R2** | *Withdrawn — carried to [ZZ-R1](rules.md).* |
| **ZZ-R3** | *Draft:* a rule not yet agreed. |
"""

ME = {"name": "Ada Lovelace", "email": "ada@example.org", "parents": 1}
SIGNED = "Spec: ZZ-R1\n\nSigned-off-by: Ada Lovelace <ada@example.org>"


def run_main(argv):
    """Call main() with argv patched; return (exit code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["squash_message", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = gate.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Case(unittest.TestCase):
    """A temporary root with a spec checkout beside what the workflow wrote."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        (self.root / SPEC).mkdir()
        (self.root / SPEC / "rules.md").write_text(ROWS, encoding="utf-8")

    def check(self, title="feat: a thing", body=SIGNED, commits=(ME,), bot=False):
        (self.root / PULL).write_text(json.dumps({"title": title, "body": body, "bot": bot}), "utf-8")
        (self.root / COMMITS).write_text("".join(json.dumps(c) + "\n" for c in commits) + "\n", "utf-8")
        return run_main(["--spec-dir", SPEC, "--pull", PULL, "--commits", COMMITS])


class Passing(Case):
    def test_a_conventional_title_a_resolving_citation_and_the_sign_off_pass(self):
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn(gate.PASSED, out)

    def test_a_revert_titled_by_the_forge_passes(self):
        self.assertEqual(self.check(title='Revert "feat: a thing"')[0], 0)

    def test_the_sign_off_matches_the_address_whatever_its_case(self):
        body = "Spec: ZZ-R1\nSigned-off-by: Ada Lovelace <ADA@Example.org>"
        self.assertEqual(self.check(body=body)[0], 0)

    def test_a_bot_pull_request_is_exempt_whatever_it_carries(self):
        code, out = self.check(title="Bump x", body=None, bot=True)
        self.assertEqual(code, 0)
        self.assertIn(gate.PASSED, out)

    def test_merge_and_bot_commits_need_no_sign_off(self):
        merge = {"name": "Ada Lovelace", "email": "other@example.org", "parents": 2}
        bot = {"name": "dependabot[bot]", "email": "1+dependabot[bot]@users.noreply.github.com", "parents": 1}
        self.assertEqual(self.check(commits=(ME, merge, bot))[0], 0)


class Title(Case):
    def test_a_subject_without_a_type_is_refused_by_name(self):
        code, out = self.check(title="did a thing")
        self.assertEqual(code, 1)
        self.assertIn("The title `did a thing` is not a conventional subject", out)
        self.assertIn("feat, fix, docs", out)


class Citation(Case):
    def test_a_body_without_a_spec_line_is_refused_with_the_line_to_add(self):
        code, out = self.check(body="Signed-off-by: Ada Lovelace <ada@example.org>")
        self.assertEqual(code, 1)
        self.assertIn("The body has no `Spec:` line", out)
        self.assertIn("`Spec: OPS-R1`", out)

    def test_an_empty_body_is_refused_for_the_citation_and_the_sign_off(self):
        code, out = self.check(body=None)
        self.assertEqual(code, 1)
        self.assertIn("no `Spec:` line", out)
        self.assertIn("Signed-off-by: Ada Lovelace <ada@example.org>", out)

    def test_an_identifier_the_spec_does_not_define_is_named(self):
        code, out = self.check(body=SIGNED.replace("ZZ-R1", "ZZ-R9"))
        self.assertEqual(code, 1)
        self.assertIn("`ZZ-R9` is not defined on `spec@main`.", out)

    def test_a_retired_identifier_is_named_with_where_the_work_went(self):
        code, out = self.check(body=SIGNED.replace("ZZ-R1", "ZZ-R2"))
        self.assertEqual(code, 1)
        self.assertIn("`ZZ-R2` is retired: *Withdrawn — carried to [ZZ-R1](rules.md).*", out)

    def test_a_draft_identifier_is_named_with_its_document(self):
        code, out = self.check(body=SIGNED.replace("ZZ-R1", "ZZ-R3"))
        self.assertEqual(code, 1)
        self.assertIn("`ZZ-R3` is Draft (rules.md) and cannot be cited until it is Accepted.", out)

    def test_a_spec_holding_no_identifiers_cannot_be_read_against(self):
        (self.root / SPEC / "rules.md").write_text("# Nothing\n", encoding="utf-8")
        code, out = self.check()
        self.assertEqual(code, 2)
        self.assertIn("no identifiers found", out)


class SignOff(Case):
    def test_each_unsigned_author_is_given_their_line_once(self):
        grace = {"name": "Grace Hopper", "email": "grace@example.org", "parents": 1}
        code, out = self.check(commits=(ME, grace, grace))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("Signed-off-by: Grace Hopper <grace@example.org>"), 1)
        self.assertNotIn("Signed-off-by: Ada Lovelace <ada@example.org>\n  ```", out)

    def test_the_lines_to_add_stay_inside_their_bullet(self):
        code, out = self.check(body="Spec: ZZ-R1")
        self.assertEqual(code, 1)
        self.assertIn("\n  ```\n  Signed-off-by: Ada Lovelace <ada@example.org>\n  ```", out)

    def test_a_sign_off_by_somebody_else_does_not_count(self):
        body = "Spec: ZZ-R1\nSigned-off-by: Ada Lovelace <ada@elsewhere.org>"
        self.assertEqual(self.check(body=body)[0], 1)


class Usage(Case):
    def test_a_missing_spec_dir_cannot_run(self):
        code, out = run_main(["--spec-dir", "nowhere", "--pull", PULL, "--commits", COMMITS])
        self.assertEqual(code, 2)
        self.assertIn("spec dir not found: nowhere", out)

    def test_a_missing_file_cannot_run(self):
        code, out = run_main(["--spec-dir", SPEC, "--pull", PULL, "--commits", COMMITS])
        self.assertEqual(code, 2)
        self.assertIn("pull not found: pull.json", out)

    def test_a_file_outside_the_checkout_is_refused(self):
        code, out = run_main(["--spec-dir", SPEC, "--pull", "/etc/hosts", "--commits", COMMITS])
        self.assertEqual(code, 2)
        self.assertIn("pull must be within the working directory", out)

    def test_run_as_a_script_it_exits_with_the_verdict(self):
        self.check()
        argv = ["squash_message", "--spec-dir", SPEC, "--pull", PULL, "--commits", COMMITS]
        saved = sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as done:
                runpy.run_path(gate.__file__, run_name="__main__")
        finally:
            sys.argv = saved
        self.assertEqual(done.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
