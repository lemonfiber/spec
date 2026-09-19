#!/usr/bin/env python3
"""What the unrequired-check survey refuses, driven against a stubbed forge.

Nothing here talks to GitHub. The three readers — the repository list, a
repository's required contexts, and the check names its pull requests produced —
are replaced, so what is exercised is the arithmetic and the four ways it can be
asked about nothing.

The register itself is read from the real file in one test, because an exemption
with no reason is the defect the register exists to prevent and a fixture would
not notice it.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_check_required.py
"""

from __future__ import annotations

import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_required

NAMES = [{"name": "labeler / label", "why": "reports"}]
PREFIXES = [{"prefix": "mutation (", "why": "shards"}]


def wrote(text: str) -> pathlib.Path:
    where = pathlib.Path(tempfile.mkdtemp()) / "required-checks.toml"
    where.write_text(text, encoding="utf-8")
    return where


class TheRegisterOnDisk(unittest.TestCase):
    def test_every_exemption_in_the_real_register_carries_a_reason(self):
        names, prefixes = check_required.register()
        self.assertTrue(names)
        for entry in (*names, *prefixes):
            self.assertTrue(entry["why"].strip(), entry)

    def test_the_complement_legs_are_registered(self):
        names, _ = check_required.register()
        registered = {entry["name"] for entry in names}
        self.assertIn("gate / not-a-pull-request", registered)
        self.assertIn("CodeQL", registered)


class TheRegister(unittest.TestCase):
    def test_a_register_that_is_not_there_refuses(self):
        with self.assertRaises(check_required.Unanswerable) as why:
            check_required.register(pathlib.Path("/nowhere/required-checks.toml"))
        self.assertIn("is not here", str(why.exception))

    def test_a_register_exempting_nothing_refuses(self):
        where = wrote("# nothing here\n")
        with self.assertRaises(check_required.Unanswerable) as why:
            check_required.register(where)
        self.assertIn("exempts nothing", str(why.exception))

    def test_an_exemption_with_no_reason_refuses(self):
        where = wrote('[[exempt]]\nname = "x"\n')
        with self.assertRaises(check_required.Unanswerable) as why:
            check_required.register(where)
        self.assertIn("carries no reason", str(why.exception))

    def test_an_exemption_naming_neither_a_check_nor_a_prefix_refuses(self):
        where = wrote('[[exempt]]\nwhy = "because"\n')
        with self.assertRaises(check_required.Unanswerable) as why:
            check_required.register(where)
        self.assertIn("neither a check nor a prefix", str(why.exception))

    def test_names_and_prefixes_are_kept_apart(self):
        names, prefixes = check_required.register(
            wrote(
                '[[exempt]]\nname = "a"\nwhy = "r"\n'
                '[[exempt]]\nprefix = "b ("\nwhy = "r"\n'
            )
        )
        self.assertEqual([e["name"] for e in names], ["a"])
        self.assertEqual([e["prefix"] for e in prefixes], ["b ("])


class TheMatching(unittest.TestCase):
    def test_a_named_check_is_exempt(self):
        self.assertIsNotNone(
            check_required.exempt("labeler / label", NAMES, PREFIXES)
        )

    def test_a_prefixed_check_is_exempt(self):
        self.assertIsNotNone(
            check_required.exempt("mutation (kernel)", NAMES, PREFIXES)
        )

    def test_anything_else_is_not(self):
        self.assertIsNone(check_required.exempt("build", NAMES, PREFIXES))


class TheRefusal(unittest.TestCase):
    def test_it_names_the_repository_and_every_check(self):
        said = check_required.refusal("lemonfiber/brand", ["check", "analyze"])
        self.assertIn("lemonfiber/brand", said)
        self.assertIn("check", said)
        self.assertIn("analyze", said)

    def test_it_says_what_the_defect_is_and_both_ways_out(self):
        said = check_required.refusal("lemonfiber/brand", ["check"])
        self.assertIn("the merge happens anyway", said)
        self.assertIn("required contexts", said)
        self.assertIn("required-checks.toml", said)

    def test_it_warns_against_naming_a_matrix_leg(self):
        self.assertIn(
            "run-time matrix", check_required.refusal("lemonfiber/brand", ["x"])
        )


class TheSurvey(unittest.TestCase):
    def survey(self, required, observed, only=None):
        out = io.StringIO()
        with mock.patch.object(check_required, "register", return_value=(NAMES, PREFIXES)), \
             mock.patch.object(check_required, "repositories", return_value=list(required)), \
             mock.patch.object(check_required, "required_in", side_effect=lambda o, n: required[n]), \
             mock.patch.object(check_required, "observed_in", side_effect=lambda o, n: observed[n]):
            code = check_required.look("lemonfiber", only, out)
        return code, out.getvalue()

    def test_a_check_that_runs_and_does_not_block_is_refused(self):
        code, said = self.survey(
            {"brand": {"hygiene / typos"}},
            {"brand": {"hygiene / typos", "check", "labeler / label"}},
        )
        self.assertEqual(code, 1)
        self.assertIn("check", said)
        self.assertNotIn("hygiene / typos", said)

    def test_an_exempt_check_is_not_refused(self):
        code, said = self.survey(
            {"brand": {"hygiene / typos"}},
            {"brand": {"hygiene / typos", "labeler / label", "mutation (a)"}},
        )
        self.assertEqual(code, 0, said)
        self.assertIn("1 repositories", said)

    def test_an_exemption_matching_nothing_is_refused(self):
        code, said = self.survey(
            {"brand": {"hygiene / typos"}},
            {"brand": {"hygiene / typos", "labeler / label"}},
        )
        self.assertEqual(code, 1)
        self.assertIn("matched no check", said)
        self.assertIn("mutation (", said)

    def test_one_repository_can_be_asked_about_on_its_own(self):
        code, said = self.survey(
            {"brand": {"a"}},
            {"brand": {"a", "labeler / label", "mutation (a)"}},
            only="lemonfiber/brand",
        )
        self.assertEqual(code, 0, said)


class TheSilences(unittest.TestCase):
    def test_an_organisation_with_no_repository_refuses(self):
        with mock.patch.object(check_required, "_run", return_value="\n"), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required.repositories("lemonfiber")
        self.assertIn("no repository was listed", str(why.exception))

    def test_a_repository_with_no_check_at_all_refuses(self):
        with mock.patch.object(check_required, "_run", return_value="[]"), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required.observed_in("lemonfiber", "brand")
        self.assertIn("produced no check name", str(why.exception))

    def test_a_name_that_could_read_as_a_flag_refuses(self):
        with self.assertRaises(check_required.Unanswerable) as why:
            check_required.named("--upload-file=/etc/passwd", "repository")
        self.assertIn("read as a flag", str(why.exception))

    def test_the_organisation_profile_repository_is_a_name(self):
        self.assertEqual(check_required.named(".github", "repository"), ".github")

    def test_a_forge_that_will_not_answer_refuses(self):
        done = mock.Mock(returncode=1, stderr="not found", stdout="")
        with mock.patch.object(check_required.subprocess, "run", return_value=done), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required._run(["gh", "api", "whatever"])
        self.assertIn("not found", str(why.exception))

    def test_an_unreadable_protection_is_not_a_clean_repository(self):
        with mock.patch.object(check_required, "register", return_value=(NAMES, PREFIXES)), \
             mock.patch.object(check_required, "repositories", return_value=["brand"]), \
             mock.patch.object(check_required, "required_in", side_effect=check_required.Unanswerable("protection unreadable")):
            code = check_required.main(["--owner", "lemonfiber"])
        self.assertEqual(code, 1)

    def test_the_readers_parse_what_the_forge_answers(self):
        with mock.patch.object(check_required, "_run", return_value="b\na\n"):
            self.assertEqual(check_required.repositories("lemonfiber"), ["a", "b"])
        with mock.patch.object(check_required, "_run", return_value='{"checks":[{"context":"a"}]}'):
            self.assertEqual(check_required.required_in("lemonfiber", "brand"), {"a"})
        rollup = '[{"statusCheckRollup":[{"name":"a"},{"context":"b"},{}]}]'
        with mock.patch.object(check_required, "_run", return_value=rollup):
            self.assertEqual(check_required.observed_in("lemonfiber", "brand"), {"a", "b"})
        with mock.patch.object(check_required.subprocess, "run",
                               return_value=mock.Mock(returncode=0, stdout="x")):
            self.assertEqual(check_required._run(["gh", "api", "x"]), "x")


class TheCommandLine(unittest.TestCase):
    def test_a_clean_estate_passes(self):
        with mock.patch.object(check_required, "look", return_value=0):
            self.assertEqual(check_required.main([]), 0)


if __name__ == "__main__":
    unittest.main()
