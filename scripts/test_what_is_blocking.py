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
    """`_gh` answers from a table keyed on any fragment of the call.

    Keyed on a fragment rather than the sub-command, because two calls can share
    one: `_base` and `_branch_of` are both `pr view`, and a stub that cannot tell
    them apart hands each the other's answer and tests neither. The longest
    matching key wins, so `pr view` stays a usable default beside a specific one.
    """

    def setUp(self):
        self.said = {}
        self.addCleanup(setattr, wib, "_gh", wib._gh)
        wib._gh = self.answer

    def answer(self, *args):
        whole = " ".join(args)
        matches = [key for key in self.said if key in whole]
        return self.said[max(matches, key=len)] if matches else ""


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
    """A re-run leaves two reports under one name, and one of them is stale."""

    def run_of(self, name, conclusion=None, status="completed", when="2026-01-01T00:00:00Z"):
        return {
            "name": name,
            "conclusion": conclusion,
            "status": status,
            "completed_at": when if conclusion else None,
            "started_at": when,
        }

    def test_the_most_recent_report_is_the_one_the_forge_holds_you_to(self):
        # `lemonfiber-companion#123`: a `mutation testing` that passed at 09:45
        # and another still running at 09:53. The merge is blocked on the second.
        runs = [
            self.run_of("m", "success", when="2026-09-13T09:45:44Z"),
            self.run_of("m", None, "in_progress", "2026-09-13T09:53:00Z"),
        ]
        self.assertEqual(reading := wib.reading(runs, []), {"m": "IN_PROGRESS"})
        self.assertEqual(wib.reading(list(reversed(runs)), []), reading)

    def test_the_older_report_does_not_win_by_being_newer_shaped(self):
        runs = [
            self.run_of("m", None, "in_progress", "2026-09-13T09:00:00Z"),
            self.run_of("m", "failure", when="2026-09-13T09:53:00Z"),
        ]
        self.assertEqual(wib.reading(runs, []), {"m": "FAILURE"})

    def test_where_two_share_a_timestamp_the_worse_one_wins(self):
        same = "2026-09-13T09:00:00Z"
        runs = [self.run_of("m", "success", when=same), self.run_of("m", "failure", when=same)]
        self.assertEqual(wib.reading(runs, []), {"m": "FAILURE"})
        self.assertEqual(wib.reading(list(reversed(runs)), []), {"m": "FAILURE"})

    def test_every_conclusion_this_script_knows(self):
        for conclusion, state in wib._CONCLUSION.items():
            with self.subTest(conclusion):
                self.assertEqual(wib.reading([self.run_of("m", conclusion)], []), {"m": state})

    def test_a_conclusion_it_does_not_know_keeps_its_own_name(self):
        # `blocking` reads an unknown state as unfinished, which is the right
        # reading for a word GitHub adds after this was written.
        got = wib.reading([self.run_of("m", "flambeed")], [])
        self.assertEqual(got, {"m": "FLAMBEED"})
        self.assertEqual(wib.blocking(["m"], got)["waiting"], ["m"])

    def test_a_run_that_has_not_finished_reports_its_status(self):
        self.assertEqual(wib.reading([self.run_of("m", None, "queued")], []), {"m": "QUEUED"})
        self.assertEqual(wib.reading([self.run_of("m", None, "in_progress")], []), {"m": "IN_PROGRESS"})
        self.assertEqual(wib.reading([self.run_of("m", None, "napping")], []), {"m": "PENDING"})

    def test_commit_statuses_are_read_beside_check_runs(self):
        # `SonarCloud Code Analysis` is one of these, not a check run.
        statuses = [{"context": "s", "state": "success", "created_at": "2026-01-01T00:00:00Z"}]
        self.assertEqual(wib.reading([], statuses), {"s": "SUCCESS"})

    def test_a_status_error_is_a_failure_and_an_unknown_one_is_not_a_pass(self):
        def one(state):
            return [{"context": "s", "state": state, "created_at": "2026-01-01T00:00:00Z"}]
        self.assertEqual(wib.reading([], one("error")), {"s": "FAILURE"})
        self.assertEqual(wib.reading([], one("pending")), {"s": "PENDING"})
        self.assertEqual(wib.reading([], one("sideways")), {"s": "PENDING"})

    def test_a_report_with_no_name_is_dropped_rather_than_filed_under_nothing(self):
        self.assertEqual(wib.reading([self.run_of("", "success")], []), {})
        self.assertEqual(wib.reading([], [{"context": "", "state": "success"}]), {})

    def test_nothing_reported(self):
        self.assertEqual(wib.reading([], []), {})
        self.assertEqual(wib._reported("o/r", 1), {})

    def test_the_head_commit_is_what_gets_asked_about(self):
        self.assertEqual(wib._head("o/r", 1), "")
        self.said["headRefOid"] = "abc123\n"
        self.assertEqual(wib._head("o/r", 1), "abc123")
        self.said["check-runs"] = json.dumps([self.run_of("m", "success")])
        self.said["/status"] = json.dumps([])
        self.assertEqual(wib._reported("o/r", 1), {"m": "SUCCESS"})


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
        self.said["headRefOid"] = "abc123\n"
        self.said["check-runs"] = json.dumps(
            [{"name": "x", "conclusion": "success", "status": "completed",
              "completed_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:00Z"}]
        )
        out = wib.look("o/r", 3)
        self.assertIn("nothing required, or branch protection is unreadable", out[0])

    def test_required_contexts_are_read_from_the_base_branch(self):
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["gate / gate"], "strict": False}}
        )
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
        self.said["headRefOid"] = "abc123\n"
        self.said["check-runs"] = json.dumps(
            [{"name": "a", "conclusion": "failure", "status": "completed",
              "completed_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:00Z"}]
        )
        self.said["/status"] = json.dumps([])
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


class WhenNothingRanAtAll(Stubbed):
    """Twenty missing contexts, one line each, is twenty statements of one fact."""

    def all_missing(self, n=3):
        return wib.blocking([f"c{i}" for i in range(n)], {})

    def test_a_workflow_that_could_not_start_is_named(self):
        # The failure with no other symptom: no check run, no log, nothing on the
        # pull request. Twenty MISSING lines is what it looks like from outside.
        said = wib.why_nothing_ran(self.all_missing(), ["startup_failure", "success"])
        self.assertIn("did not start", said)
        self.assertIn("push the branch again", said)

    def test_no_runs_at_all(self):
        said = wib.why_nothing_ran(self.all_missing(), [])
        self.assertIn("no workflow run exists", said)

    def test_runs_that_simply_have_not_produced_them(self):
        said = wib.why_nothing_ran(self.all_missing(), ["success", "success"])
        self.assertIn("not produced them", said)

    def test_one_missing_context_among_reported_ones_is_a_different_question(self):
        # A `paths:` filter or a failed `needs:`, and "nothing ran" is the wrong
        # answer to it. Answering only where everything is missing is the point.
        found = wib.blocking(["a", "b"], {"b": "SUCCESS"})
        self.assertIsNone(wib.why_nothing_ran(found, ["startup_failure"]))

    def test_nothing_missing_is_not_this_question_either(self):
        found = wib.blocking(["a"], {"a": "SUCCESS"})
        self.assertIsNone(wib.why_nothing_ran(found, ["startup_failure"]))

    def test_the_report_collapses_to_one_line_and_a_count(self):
        out = wib.lines("o/r", 1, self.all_missing(), None, "the workflows did not start")
        self.assertEqual(out[0], "o/r#1: the workflows did not start")
        self.assertIn("3 required contexts, all of them", out[1])
        self.assertEqual(len(out), 2)

    def test_a_protection_rule_still_shows_beside_it(self):
        out = wib.lines("o/r", 1, self.all_missing(), ["sign the commits"], "nothing ran")
        self.assertIn("RULE: sign the commits", out[1])

    def test_end_to_end_a_branch_whose_workflows_never_started(self):
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["a", "b"]}}
        )
        self.said["headRefName"] = "feat/a-thing\n"
        self.said["baseRefName"] = "main\n"
        self.said["run list"] = json.dumps(["startup_failure", "startup_failure"])
        out = wib.look("o/r", 1)
        self.assertIn("did not start", out[0])
        self.assertIn("2 required contexts", out[1])

    def test_conclusions_drops_the_runs_that_have_not_finished(self):
        self.said["run list"] = json.dumps(["success", None, "failure"])
        self.assertEqual(wib._conclusions("o/r", "b"), ["success", "failure"])

    def test_a_branch_name_gh_will_not_give_is_not_asked_about(self):
        # `_branch_of` answers empty when `gh` refuses, and an empty branch is not
        # a branch — asking `gh run list --branch ""` would list the whole repo.
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["a"]}}
        )
        self.assertEqual(wib._branch_of("o/r", 1), "")
        out = wib.look("o/r", 1)
        self.assertIn("MISSING: a", out[1])


class WhenThisAndGitHubDisagree(Stubbed):
    """A second opinion that contradicts the forge silently is worse than none."""

    def clear(self):
        return wib.blocking(["a"], {"a": "SUCCESS"})

    def test_a_clean_reading_against_a_blocked_merge_box_is_said_out_loud(self):
        said = wib.disagrees(self.clear(), [], "BLOCKED")
        self.assertIn("but GitHub says BLOCKED", said)
        self.assertIn("GitHub decides", said)
        self.assertIn("closing and reopening", said)

    def test_agreement_says_nothing(self):
        self.assertIsNone(wib.disagrees(self.clear(), [], "CLEAN"))

    def test_states_that_are_not_a_disagreement(self):
        # `UNSTABLE` is a non-required check failing, which this deliberately
        # does not report on; the others are GitHub declining to say.
        for forge in ("CLEAN", "HAS_HOOKS", "UNSTABLE", "UNKNOWN", ""):
            with self.subTest(forge):
                self.assertIsNone(wib.disagrees(self.clear(), [], forge))

    def test_nothing_to_disagree_about_when_this_found_trouble_too(self):
        # Both say blocked. They agree on the answer; only the detail differs,
        # and the detail is what the rest of the report is for.
        self.assertIsNone(wib.disagrees(wib.blocking(["a"], {}), [], "BLOCKED"))
        self.assertIsNone(
            wib.disagrees(wib.blocking(["a"], {"a": "FAILURE"}), [], "BLOCKED")
        )
        self.assertIsNone(wib.disagrees(self.clear(), ["sign the commits"], "BLOCKED"))

    def test_a_check_still_running_is_not_a_disagreement(self):
        # GitHub is right to block a pull request whose checks have not finished.
        # Calling that a disagreement would cry wolf on almost every pull request
        # almost all of the time.
        found = wib.blocking(["a", "b"], {"a": "SUCCESS", "b": "IN_PROGRESS"})
        self.assertIsNone(wib.disagrees(found, [], "BLOCKED"))

    def test_a_quiet_check_is_still_a_disagreement(self):
        # `SKIPPED` is finished. Nothing more is coming, so if GitHub is still
        # blocking, the two really have read different things.
        found = wib.blocking(["a"], {"a": "SKIPPED"})
        self.assertIn("but GitHub says BLOCKED", wib.disagrees(found, [], "BLOCKED"))

    def test_the_report_is_that_line_and_nothing_else(self):
        out = wib.lines("o/r", 1, self.clear(), [], None, "we differ")
        self.assertEqual(out, ["o/r#1: we differ"])

    def test_end_to_end(self):
        self.said["api repos/o/r/branches/main/protection"] = json.dumps(
            {"required_status_checks": {"contexts": ["a"], "strict": True}}
        )
        self.said["headRefOid"] = "abc123\n"
        self.said["check-runs"] = json.dumps(
            [{"name": "a", "conclusion": "success", "status": "completed",
              "completed_at": "2026-01-01T00:00:00Z", "started_at": "2026-01-01T00:00:00Z"}]
        )
        self.said["/status"] = json.dumps([])
        self.said["baseRefName"] = "main\n"
        self.said["mergeStateStatus"] = json.dumps(
            {"mergeStateStatus": "BLOCKED", "reviewDecision": None}
        )
        out = wib.look("o/r", 1)
        self.assertIn("but GitHub says BLOCKED", out[0])


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

    def test_the_sanitiser_at_the_sink_takes_a_name_and_a_number(self):
        for good in ("lemonfiber/spec", "main", "feat/a-thing", "349", "o"):
            with self.subTest(good):
                self.assertEqual(wib.safe(good), good)

    def test_the_sanitiser_raises_rather_than_answering_empty(self):
        # An unchecked name reaching here is a mistake in this file, not a
        # repository somebody cannot read, and the two must not look alike.
        for bad in ("--template", "-R", "a b", "a;b", "a$(x)", "", "a" * 300):
            with self.subTest(bad), self.assertRaises(ValueError):
                wib.safe(bad)

    def test_every_helper_sanitises_what_it_was_handed(self):
        # `look` checks first and says something useful; these are what stops a
        # later caller skipping it, and what a taint analyser can actually see.
        for call in (
            lambda: wib._protection_of("--x", "main"),
            lambda: wib._protection_of("o/r", "--x"),
            lambda: wib._state("--x", 1),
            lambda: wib._unsigned("--x", 1),
            lambda: wib._unresolved("--x/y", 1),
            lambda: wib._reported("--x", 1),
            lambda: wib._conclusions("o/r", "--x"),
            lambda: wib._branch_of("--x", 1),
            lambda: wib._open_prs("--x"),
            lambda: wib._repos("--x"),
            lambda: wib._base("--x", 1),
        ):
            with self.assertRaises(ValueError):
                call()

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
