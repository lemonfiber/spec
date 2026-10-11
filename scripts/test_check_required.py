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
import json
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
    def survey(self, required, observed, only=None, widened=None, targeted=None):
        """The verdict, where each repository's sampled pull requests produced `observed`,
        and the whole listed window produced `widened` (the same, where not given)."""
        self.asked = []

        def seen(owner, name, since, sampled=check_required.SAMPLED):
            self.asked.append((name, sampled))
            return (widened or observed)[name] if sampled == check_required.LISTED else observed[name]

        out = io.StringIO()
        with mock.patch.object(check_required, "register", return_value=(NAMES, PREFIXES)), \
             mock.patch.object(check_required, "repositories", return_value=list(required)), \
             mock.patch.object(check_required, "required_in", side_effect=lambda o, n: required[n]), \
             mock.patch.object(check_required, "gates_landed", return_value=None), \
             mock.patch.object(check_required, "observed_in", side_effect=seen), \
             mock.patch.object(check_required, "targeted_in",
                               side_effect=lambda o, n: (targeted or {}).get(n, set())):
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

    def test_a_check_only_a_pull_request_target_run_produced_is_refused(self):
        # pin-only ran on every open pull request and on no merged one.
        code, out = self.survey(
            required={"plugin-komga": {"gates / gates"}},
            observed={"plugin-komga": {"gates / gates"}},
            targeted={"plugin-komga": {"pin-only / pin-only"}},
            only="lemonfiber/plugin-komga",
        )
        self.assertEqual(code, 1)
        self.assertIn("pin-only / pin-only", out)

    def test_a_required_pull_request_target_check_is_not_refused(self):
        code, _ = self.survey(
            required={"plugin-komga": {"gates / gates", "pin-only / pin-only"}},
            observed={"plugin-komga": {"gates / gates"}},
            targeted={"plugin-komga": {"pin-only / pin-only"}},
            only="lemonfiber/plugin-komga",
        )
        self.assertEqual(code, 0)

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

    def test_an_exemption_seen_only_past_the_sample_is_not_refused(self):
        code, said = self.survey(
            {"brand": {"hygiene / typos"}, "spec": {"hygiene / typos"}},
            {"brand": {"hygiene / typos", "labeler / label"}, "spec": {"hygiene / typos"}},
            widened={"brand": {"hygiene / typos"}, "spec": {"mutation (a)"}},
        )
        self.assertEqual(code, 0, said)
        self.assertIn(("spec", check_required.LISTED), self.asked)

    def test_the_window_is_read_only_until_every_exemption_has_matched(self):
        self.survey(
            {"brand": {"a"}, "spec": {"a"}},
            {"brand": {"a", "labeler / label"}, "spec": {"a"}},
            widened={"brand": {"mutation (a)"}, "spec": {"a"}},
        )
        self.assertEqual([n for n, sampled in self.asked if sampled == check_required.LISTED], ["brand"])

    def test_a_survey_matching_every_exemption_reads_no_further(self):
        self.survey({"brand": {"a"}}, {"brand": {"a", "labeler / label", "mutation (a)"}})
        self.assertNotIn(("brand", check_required.LISTED), self.asked)

    def test_one_repository_asked_alone_is_not_held_to_every_exemption(self):
        code, said = self.survey({"brand": {"a"}}, {"brand": {"a"}}, only="lemonfiber/brand")
        self.assertEqual(code, 0, said)
        self.assertEqual(self.asked, [("brand", check_required.SAMPLED)])

    def test_one_repository_can_be_asked_about_on_its_own(self):
        code, said = self.survey(
            {"brand": {"a"}},
            {"brand": {"a", "labeler / label", "mutation (a)"}},
            only="lemonfiber/brand",
        )
        self.assertEqual(code, 0, said)


def merged(pulls: list[dict]):
    """A forge whose merged pull requests are `pulls`: listed by number and
    date, each one's checks answered when it is viewed."""
    numbered = [{"number": at, **pull} for at, pull in enumerate(pulls, 1)]

    def answer(argv: list[str]) -> str:
        if argv[:3] == ["gh", "pr", "list"]:
            return json.dumps([{"number": p["number"], "mergedAt": p.get("mergedAt")} for p in numbered])
        number = int(argv[argv.index("view") + 1])
        return json.dumps({"statusCheckRollup": numbered[number - 1].get("statusCheckRollup")})

    return answer


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

    def test_a_protection_refused_to_the_token_names_the_permission(self):
        denied = check_required.Unanswerable(
            "`gh api ...` failed: gh: Resource not accessible by integration (HTTP 403)")
        with mock.patch.object(check_required, "_run", side_effect=denied), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required.required_in("lemonfiber", ".github")
        self.assertIn("lemonfiber/.github's branch protection could not be read (HTTP 403)", str(why.exception))
        self.assertIn("Administration: read", str(why.exception))

    def test_any_other_failure_to_read_protection_is_said_as_it_came(self):
        missing = check_required.Unanswerable("`gh api ...` failed: Branch not protected (HTTP 404)")
        with mock.patch.object(check_required, "_run", side_effect=missing), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required.required_in("lemonfiber", "spec")
        self.assertIs(why.exception, missing)

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
        rollup = merged([{"statusCheckRollup": [{"name": "a"}, {"context": "b"}, {}]}, {"statusCheckRollup": None}])
        with mock.patch.object(check_required, "_run", side_effect=rollup):
            self.assertEqual(check_required.observed_in("lemonfiber", "brand"), {"a", "b"})
        with mock.patch.object(check_required.subprocess, "run",
                               return_value=mock.Mock(returncode=0, stdout="x")):
            self.assertEqual(check_required._run(["gh", "api", "x"]), "x")
        asked = []

        def answer(argv):
            asked.append(argv[2])
            return "11\n12\n" if "event=pull_request_target" in argv[2] else "pin-only / pin-only\n\n"

        with mock.patch.object(check_required, "_run", side_effect=answer):
            self.assertEqual(check_required.targeted_in("lemonfiber", "brand"), {"pin-only / pin-only"})
        self.assertEqual(asked, [
            f"repos/lemonfiber/brand/actions/runs?event=pull_request_target&per_page={check_required.TARGET_RUNS}",
            "repos/lemonfiber/brand/actions/runs/11/jobs",
            "repos/lemonfiber/brand/actions/runs/12/jobs",
        ])


class WhatIsSampled(unittest.TestCase):
    def test_only_merged_pull_requests_are_asked_about(self):
        with mock.patch.object(check_required, "_run", side_effect=merged([{"statusCheckRollup": [{"name": "a"}]}])) as ran:
            check_required.observed_in("lemonfiber", "homebrew-tap")
        listing = ran.call_args_list[0].args[0]
        self.assertEqual(listing[listing.index("--state") + 1], "merged")
        self.assertEqual(listing[listing.index("--json") + 1], "number,mergedAt")
        self.assertEqual(ran.call_args_list[1].args[0][:4], ["gh", "pr", "view", "1"])

    def test_only_pull_requests_merged_since_the_gates_landed_are_read(self):
        pulls = [
            {"mergedAt": "2026-10-09T10:00:00Z", "statusCheckRollup": [{"name": "gates / gates"}]},
            {"mergedAt": "2026-10-09T09:00:00Z", "statusCheckRollup": [{"name": "gates / report"}]},
            {"mergedAt": "2026-10-08T09:00:00Z", "statusCheckRollup": [{"name": "dco / dco"}]},
            {"mergedAt": None, "statusCheckRollup": [{"name": "odd"}]},
        ]
        with mock.patch.object(check_required, "_run", side_effect=merged(pulls)):
            self.assertEqual(check_required.observed_in("lemonfiber", "brand", since="2026-10-09T09:00:00Z"),
                             {"gates / gates", "gates / report"})
        with mock.patch.object(check_required, "_run", side_effect=merged(pulls)):
            self.assertEqual(check_required.observed_in("lemonfiber", "brand", sampled=1,
                                                        since="2026-10-08T00:00:00Z"), {"gates / gates"})
        with mock.patch.object(check_required, "_run", side_effect=merged(pulls)):
            self.assertEqual(len(check_required.observed_in("lemonfiber", "brand")), 4)
        with mock.patch.object(check_required, "_run", side_effect=merged(list(reversed(pulls)))):
            self.assertEqual(check_required.observed_in("lemonfiber", "brand", sampled=1,
                                                        since="2026-10-08T00:00:00Z"), {"gates / gates"})

    def test_only_the_sampled_pull_requests_checks_are_read(self):
        pulls = [{"mergedAt": f"2026-10-09T0{at}:00:00Z", "statusCheckRollup": [{"name": "a"}]} for at in range(9)]
        with mock.patch.object(check_required, "_run", side_effect=merged(pulls)) as ran:
            check_required.observed_in("lemonfiber", "brand")
        self.assertEqual(len(ran.call_args_list), 1 + check_required.SAMPLED)

    def test_none_merged_since_the_gates_landed_is_unanswered(self):
        pulls = [{"mergedAt": "2026-10-08T09:00:00Z", "statusCheckRollup": [{"name": "dco / dco"}]}]
        with mock.patch.object(check_required, "_run", side_effect=merged(pulls)), \
             self.assertRaises(check_required.Unanswerable) as why:
            check_required.observed_in("lemonfiber", "brand", since="2026-10-09T00:00:00Z")
        self.assertIn("merged since 2026-10-09T00:00:00Z", str(why.exception))

    def test_the_gates_landed_when_main_first_held_its_caller(self):
        with mock.patch.object(check_required, "_run",
                               return_value="2026-10-09T12:00:00Z\n2026-10-09T08:00:00Z\n") as ran:
            self.assertEqual(check_required.gates_landed("lemonfiber", "brand"), "2026-10-09T08:00:00Z")
        self.assertIn("path=.github/workflows/gates.yml&sha=main", " ".join(ran.call_args.args[0]))
        with mock.patch.object(check_required, "_run", return_value="\n"):
            self.assertIsNone(check_required.gates_landed("lemonfiber", "plugin-plex"))

    def test_the_survey_asks_since_the_gates_landed(self):
        seen = {}
        with mock.patch.object(check_required, "register", return_value=(NAMES, PREFIXES)), \
             mock.patch.object(check_required, "repositories", return_value=["brand"]), \
             mock.patch.object(check_required, "required_in", return_value={"gates / gates"}), \
             mock.patch.object(check_required, "gates_landed", return_value="2026-10-09T08:00:00Z"), \
             mock.patch.object(check_required, "observed_in",
                               side_effect=lambda o, n, since, sampled=None: seen.setdefault(n, since) and {"gates / gates"}):
            check_required.look("lemonfiber", None, io.StringIO())
        self.assertEqual(seen, {"brand": "2026-10-09T08:00:00Z"})


class TheCommandLine(unittest.TestCase):
    def test_a_clean_estate_passes(self):
        with mock.patch.object(check_required, "look", return_value=0):
            self.assertEqual(check_required.main([]), 0)


if __name__ == "__main__":
    unittest.main()
