#!/usr/bin/env python3
"""Cover the decisions in `what_is_blocking.py`.

Everything here stubs `_gh`, which is the script's one shell boundary, so the
suite tests what the script concludes rather than what `gh` returns. One case at
the end runs the real `_gh` — it is the half a stub cannot vouch for.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_what_is_blocking.py
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import what_is_blocking as wib


class Stubbed(unittest.TestCase):
    """`_gh` answers from a table keyed on the sub-command it was asked."""

    def setUp(self):
        self.said = {}
        self.addCleanup(setattr, wib, "_gh", wib._gh)
        wib._gh = lambda *args: self.said.get(" ".join(args[:2]), "")


class Sorting(unittest.TestCase):
    """Every required context lands in exactly one column."""

    def test_a_context_nothing_reported_is_the_one_with_nowhere_to_look(self):
        found = wib.blocking(["gate / gate"], {})
        self.assertEqual(found["missing"], ["gate / gate"])

    def test_the_four_states_that_are_not_missing(self):
        found = wib.blocking(
            ["a", "b", "c", "d"],
            {"a": "SUCCESS", "b": "FAILURE", "c": "SKIPPED", "d": "IN_PROGRESS"},
        )
        self.assertEqual(found["passed"], ["a"])
        self.assertEqual(found["failing"], ["b"])
        self.assertEqual(found["quiet"], ["c"])
        self.assertEqual(found["waiting"], ["d"])

    def test_a_state_this_script_has_never_heard_of_counts_as_unfinished(self):
        # Deliberately not a pass. A state GitHub adds later should read as "not
        # finished" until somebody looks, or this widens every time the forge does.
        found = wib.blocking(["a"], {"a": "MOON_PHASE_PENDING"})
        self.assertEqual(found["waiting"], ["a"])
        self.assertEqual(found["passed"], [])

    def test_a_check_that_is_not_required_is_not_this_script_s_business(self):
        # It cannot block the merge, so naming it would only add noise to the
        # answer somebody came here for.
        found = wib.blocking(["a"], {"a": "SUCCESS", "unrelated": "FAILURE"})
        self.assertEqual(found["failing"], [])
        self.assertEqual(sum(len(v) for v in found.values()), 1)


class TheHeadline(unittest.TestCase):
    """The one line at the top says which kind of trouble this is."""

    def test_missing_outranks_failing(self):
        # Both are real, and only one of them has a log to read. Say that one.
        said = wib.verdict(wib.blocking(["a", "b"], {"b": "FAILURE"}))
        self.assertIn("never reported", said)

    def test_failing_names_where_the_log_is(self):
        said = wib.verdict(wib.blocking(["b"], {"b": "FAILURE"}))
        self.assertIn("log is on the pull request", said)

    def test_still_running_is_not_trouble(self):
        said = wib.verdict(wib.blocking(["b"], {"b": "QUEUED"}))
        self.assertIn("nothing is wrong", said)

    def test_everything_satisfied(self):
        said = wib.verdict(wib.blocking(["b"], {"b": "SUCCESS"}))
        self.assertIn("satisfied", said)

    def test_a_quiet_check_alone_is_not_called_trouble(self):
        # SKIPPED is neither a pass nor a failure here, and the headline does not
        # pretend otherwise — it is listed below, where a maintainer sees it.
        found = wib.blocking(["b"], {"b": "SKIPPED"})
        self.assertIn("satisfied", wib.verdict(found))
        self.assertEqual(found["quiet"], ["b"])


class TheReport(unittest.TestCase):
    def test_worst_first_and_passes_counted_rather_than_listed(self):
        found = wib.blocking(
            ["m", "f", "q", "w", "p"],
            {"f": "FAILURE", "q": "SKIPPED", "w": "QUEUED", "p": "SUCCESS"},
        )
        out = wib.lines("o/r", 7, found)
        self.assertTrue(out[0].startswith("o/r#7: "))
        self.assertIn("MISSING: m", out[1])
        self.assertIn("FAILING: f", out[2])
        self.assertIn("passed: 1", out[-1])

    def test_a_clean_pull_request_says_so_in_one_line_and_a_count(self):
        out = wib.lines("o/r", 7, wib.blocking(["p"], {"p": "SUCCESS"}))
        self.assertEqual(len(out), 2)

    def test_nothing_required_at_all(self):
        out = wib.lines("o/r", 7, wib.blocking([], {}))
        self.assertEqual(out, ["o/r#7: every required context is satisfied"])


class WhenANameReportsTwice(Stubbed):
    """A re-run leaves two entries, and the wrong one would hide the other."""

    def test_the_failure_wins_over_the_pass_beside_it(self):
        self.said["pr checks"] = json.dumps(
            [{"name": "gate", "state": "SUCCESS"}, {"name": "gate", "state": "FAILURE"}]
        )
        self.assertEqual(wib._reported("o/r", 1), {"gate": "FAILURE"})

    def test_in_either_order(self):
        self.said["pr checks"] = json.dumps(
            [{"name": "gate", "state": "FAILURE"}, {"name": "gate", "state": "SUCCESS"}]
        )
        self.assertEqual(wib._reported("o/r", 1), {"gate": "FAILURE"})

    def test_running_outranks_skipped(self):
        self.said["pr checks"] = json.dumps(
            [{"name": "g", "state": "SKIPPED"}, {"name": "g", "state": "IN_PROGRESS"}]
        )
        self.assertEqual(wib._reported("o/r", 1), {"g": "IN_PROGRESS"})

    def test_nothing_reported(self):
        self.assertEqual(wib._reported("o/r", 1), {})


class Ranking(unittest.TestCase):
    def test_a_failure_is_worse_than_anything(self):
        self.assertTrue(wib._worse("FAILURE", "QUEUED"))
        self.assertTrue(wib._worse("FAILURE", "SKIPPED"))

    def test_quiet_is_worse_than_nothing(self):
        self.assertFalse(wib._worse("SKIPPED", "FAILURE"))
        self.assertFalse(wib._worse("SKIPPED", "QUEUED"))

    def test_an_unknown_state_ranks_where_waiting_does(self):
        self.assertFalse(wib._worse("WHAT", "QUEUED"))
        self.assertTrue(wib._worse("WHAT", "SKIPPED"))


class ReadingTheForge(Stubbed):
    """Everything above `_gh`, with `_gh` answering from a table."""

    def test_a_repository_with_no_readable_protection_says_so(self):
        # Not "nothing is blocking it". A token that cannot read the rule and a
        # branch that carries none are different facts, and this claims neither.
        self.said["pr checks"] = json.dumps([{"name": "x", "state": "SUCCESS"}])
        out = wib.look("o/r", 3)
        self.assertIn("nothing required, or branch protection is unreadable", out[0])

    def test_required_contexts_are_read_from_the_base_branch(self):
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["gate / gate"], "strict": False}}
        )
        self.said["pr checks"] = json.dumps([])
        self.assertEqual(
            wib.required_in({"required_status_checks": {"contexts": ["gate / gate"]}}),
            ["gate / gate"],
        )
        out = wib.look("o/r", 3)
        self.assertIn("MISSING: gate / gate", out[1])

    def test_the_base_branch_falls_back_to_main(self):
        self.assertEqual(wib._base("o/r", 1), "main")
        self.said["pr view"] = "release\n"
        self.assertEqual(wib._base("o/r", 1), "release")

    def test_protection_is_read_once_and_both_questions_asked_of_it(self):
        # Two reads of one document, not two calls to one endpoint.
        protection = {
            "required_status_checks": {"contexts": ["a"], "strict": True},
            "required_signatures": {"enabled": True},
            "required_conversation_resolution": {"enabled": False},
            "required_pull_request_reviews": {"required_approving_review_count": 1},
        }
        self.assertEqual(wib.required_in(protection), ["a"])
        self.assertEqual(
            wib.rules_in(protection),
            {"strict": True, "signatures": True, "conversation": False, "reviews": True},
        )

    def test_a_protection_document_missing_every_optional_block(self):
        # A repository can turn any of these off, and the key then is not there
        # at all rather than false. Reading that as "on" would report a rule
        # holding a pull request that nothing is holding.
        self.assertEqual(wib.required_in({}), [])
        self.assertEqual(
            wib.rules_in({}),
            {"strict": False, "signatures": False, "conversation": False, "reviews": False},
        )

    def test_the_protection_endpoint_answers_or_it_does_not(self):
        self.assertEqual(wib._protection_of("o/r", "main"), {})
        self.said["api repos/o/r/branches/main/protection"] = json.dumps({"x": 1})
        self.assertEqual(wib._protection_of("o/r", "main"), {"x": 1})

    def test_nothing_open_and_nothing_listed(self):
        self.assertEqual(wib._open_prs("o/r"), [])
        self.assertEqual(wib._repos("o"), [])

    def test_open_pull_requests_and_repositories(self):
        self.said["pr list"] = json.dumps([{"number": 4}, {"number": 9}])
        self.assertEqual(wib._open_prs("o/r"), [4, 9])
        self.said["repo list"] = json.dumps([{"nameWithOwner": "o/r"}])
        self.assertEqual(wib._repos("o"), ["o/r"])


class TheCommandLine(Stubbed):
    def run_main(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = wib.main(argv)
        return code, out.getvalue()

    def test_named_numbers(self):
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["a"]}}
        )
        self.said["pr checks"] = json.dumps([{"name": "a", "state": "FAILURE"}])
        code, out = self.run_main(["o/r", "3"])
        self.assertEqual(code, 0)
        self.assertIn("FAILING: a", out)

    def test_every_open_pull_request_when_none_is_named(self):
        self.said["pr list"] = json.dumps([{"number": 4}])
        code, out = self.run_main(["o/r"])
        self.assertEqual(code, 0)
        self.assertIn("o/r#4", out)

    def test_the_whole_organisation(self):
        self.said["repo list"] = json.dumps([{"nameWithOwner": "o/r"}])
        self.said["pr list"] = json.dumps([{"number": 4}])
        code, out = self.run_main(["--org", "o"])
        self.assertEqual(code, 0)
        self.assertIn("o/r#4", out)


class RulesThatAreNotChecks(unittest.TestCase):
    """Branch protection blocks in ways that appear in no check list at all."""

    def test_a_rule_that_is_off_is_not_reported(self):
        self.assertEqual(wib.unmet({"strict": False}, {"behind": True}), [])

    def test_a_rule_that_is_on_and_satisfied_is_not_reported(self):
        self.assertEqual(wib.unmet({"strict": True}, {"behind": False}), [])

    def test_each_rule_names_what_to_do_about_it(self):
        for setting, condition, said in wib.RULES:
            with self.subTest(setting):
                self.assertEqual(wib.unmet({setting: True}, {condition: True}), [said])

    def test_a_pull_request_with_every_check_green_can_still_be_held(self):
        # The answer GitHub's own merge box gets wrong, and the reason the
        # headline could not simply read "every required context is satisfied".
        found = wib.blocking(["a"], {"a": "SUCCESS"})
        held = wib.unmet({"signatures": True}, {"unsigned": True})
        self.assertIn("branch protection rule holds it", wib.verdict(found, held))
        out = wib.lines("o/r", 1, found, held)
        self.assertIn("RULE: every commit must be signed", "\n".join(out))

    def test_a_failing_check_still_leads(self):
        # A rule has no log and a failed check does; send the reader to the log.
        found = wib.blocking(["a"], {"a": "FAILURE"})
        held = wib.unmet({"strict": True}, {"behind": True})
        self.assertIn("log is on the pull request", wib.verdict(found, held))
        self.assertIn("RULE:", "\n".join(wib.lines("o/r", 1, found, held)))

    def test_nothing_known_about_the_pull_request_holds_nothing(self):
        self.assertEqual(wib.unmet({"strict": True, "signatures": True}, {}), [])


class ReadingTheRulesOffTheForge(Stubbed):
    """The three reads that answer "is this pull request failing that rule"."""

    def test_a_pull_request_behind_its_base(self):
        self.said["pr view"] = json.dumps({"mergeStateStatus": "BEHIND"})
        self.assertTrue(wib._state("o/r", 1)["behind"])

    def test_a_pull_request_that_is_not_behind_and_is_approved(self):
        self.said["pr view"] = json.dumps(
            {"mergeStateStatus": "CLEAN", "reviewDecision": "APPROVED"}
        )
        state = wib._state("o/r", 1)
        self.assertFalse(state["behind"])
        self.assertFalse(state["unapproved"])

    def test_review_required_is_not_the_same_as_no_review_being_asked_for(self):
        # `null` is a repository that requires no approval. Reading it as "not
        # approved" would report every pull request as held by a rule that is off.
        self.said["pr view"] = json.dumps({"reviewDecision": None})
        self.assertFalse(wib._state("o/r", 1)["unapproved"])
        self.said["pr view"] = json.dumps({"reviewDecision": "CHANGES_REQUESTED"})
        self.assertTrue(wib._state("o/r", 1)["unapproved"])

    def test_a_pull_request_gh_will_not_describe(self):
        self.assertEqual(wib._state("o/r", 1), {})

    def test_unsigned_commits_are_named_by_their_short_sha(self):
        self.assertEqual(wib._unsigned("o/r", 1), [])
        self.said["api repos/o/r/pulls/1/commits"] = json.dumps(["abcd1234"])
        self.assertEqual(wib._unsigned("o/r", 1), ["abcd1234"])

    def test_an_open_conversation(self):
        self.assertFalse(wib._unresolved("o/r", 1))
        self.said["api graphql"] = json.dumps([True, True])
        self.assertFalse(wib._unresolved("o/r", 1))
        self.said["api graphql"] = json.dumps([True, False])
        self.assertTrue(wib._unresolved("o/r", 1))


class NamesThatWouldBecomeFlags(Stubbed):
    """`gh` reads a leading dash as an option, and no shell is needed for that."""

    def test_what_a_repository_may_be_called(self):
        for good in ("lemonfiber/spec", "o/r", "a-b.c/d_e", "O0/r9"):
            with self.subTest(good):
                self.assertTrue(wib.named(good))

    def test_what_it_may_not(self):
        # `--template` is not a repository this fails to find. It is a flag.
        for bad in ("--template", "-R", "o", "/r", "o/", "o/../x", "o/r/s", ""):
            with self.subTest(bad):
                self.assertFalse(wib.named(bad))

    def test_what_a_branch_may_be_called(self):
        self.assertTrue(wib.branched("main"))
        self.assertTrue(wib.branched("feat/a-thing"))

    def test_a_branch_that_walks_out_of_the_api_path(self):
        # Interpolated into `repos/{repo}/branches/{base}/protection`, so `..`
        # is not a branch that does not exist — it is a different endpoint.
        for bad in ("../../x", "a/../b", "-x", ""):
            with self.subTest(bad):
                self.assertFalse(wib.branched(bad))

    def test_a_bad_repository_never_reaches_gh(self):
        reached = []
        self.addCleanup(setattr, wib, "_gh", wib._gh)
        wib._gh = lambda *args: reached.append(args) or ""
        out = wib.look("--template", 1)
        self.assertIn("not a repository name", out[0])
        self.assertEqual(reached, [])

    def test_a_bad_base_branch_stops_before_the_protection_call(self):
        self.said["pr view"] = "../../elsewhere\n"
        out = wib.look("o/r", 1)
        self.assertIn("is not a branch name", out[0])

    def test_the_organisation_is_checked_too(self):
        # A leading dash never gets this far — argparse refuses it as an unknown
        # option, which is defence this did not have to write. Everything else
        # does get here, so it is checked here.
        out = io.StringIO()
        with redirect_stdout(out):
            code = wib.main(["--org", "owner/repo"])
        self.assertEqual(code, 1)
        self.assertIn("not an organisation name", out.getvalue())

    def test_argparse_turns_away_a_target_that_starts_with_a_dash(self):
        with self.assertRaises(SystemExit):
            wib.main(["--org", "--evil"])


class TheFieldNamesAreReal(unittest.TestCase):
    """`_gh` answers a rejected field the same way it answers an unreadable repo.

    Both come back empty, on purpose, so one bad repository does not end the run
    for the others. That makes a misspelled field silent: the rule it feeds never
    fires and the script reports nothing wrong. `reviewThreads` was exactly that
    — a plausible name, not a real one.
    """

    def test_gh_accepts_every_field_state_asks_for(self):
        said = wib._gh("pr", "view", "--json", ",".join(wib.FIELDS))
        # Run outside a pull request, so `gh` refuses for want of one — but it
        # validates the field names first, and names any it does not know.
        self.assertNotIn("Unknown JSON field", said)
        for field in wib.FIELDS:
            with self.subTest(field):
                rejected = wib._gh("pr", "view", "--json", field, "--repo", "o/r")
                self.assertNotIn("Unknown JSON field", rejected)

    def test_a_field_gh_does_not_know_is_caught_rather_than_swallowed(self):
        # The check above is only worth having if it can fail. This plants the
        # mistake and shows the probe notices.
        done = __import__("subprocess").run(
            ("gh", "pr", "view", "--json", "reviewThreads"),
            capture_output=True, text=True, check=False,
        )
        self.assertIn("Unknown JSON field", done.stderr + done.stdout)


class TheShellBoundary(unittest.TestCase):
    """The half a stub cannot vouch for."""

    def test_gh_answers(self):
        self.assertIn("gh version", wib._gh("--version"))

    def test_a_command_gh_refuses_is_an_empty_answer_rather_than_a_crash(self):
        # A repository with no protection, a token without the scope, and a typo
        # all land here, and none of them should end the run for the other
        # pull requests being reported beside it.
        self.assertEqual(wib._gh("api", "repos/lemonfiber/does-not-exist-xyz/branches/main/protection"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
