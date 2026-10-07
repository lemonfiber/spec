#!/usr/bin/env python3
"""The job conditions that decide whether a runner starts, read out of the
workflows and evaluated over the events they answer.

Each condition is evaluated before a runner is assigned, and nothing else runs
it before a merge. Wrong one way, it skips work that had to happen: a pull
request from a fork never flagged, a red run on `main` never posted. Wrong the
other way, it starts the runner it was written to save. Both are pinned here,
event by event, with the condition read from the file rather than copied into
the test, so the test cannot agree with a condition the file no longer holds.

Stdlib unittest plus PyYAML, as the coverage job installs.
Run:  python3 scripts/test_job_conditions.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from workflow_expression import decides

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"
REPO = "lemonfiber/core"


def condition(workflow: str, job: str) -> str:
    read = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    return read["jobs"][job]["if"]


def run(conclusion="success", head=REPO, actor="User", event="pull_request") -> dict:
    """A `workflow_run` event, as the caller's run receives it."""
    return {
        "github": {
            "event_name": "workflow_run",
            "repository": REPO,
            "event": {
                "workflow_run": {
                    "conclusion": conclusion,
                    "event": event,
                    "head_repository": {"full_name": head},
                    "actor": {"type": actor},
                },
            },
        },
    }


def labelled(event_name: str, labels: list[str], state: str | None = None) -> dict:
    """A close or a review on a pull request carrying these labels."""
    event = {"pull_request": {"labels": [{"name": name} for name in labels]}}
    if state is not None:
        event["review"] = {"state": state}
    return {"github": {"event_name": event_name, "repository": REPO, "event": event}}


class AwaitingMaintainer(unittest.TestCase):
    """Who is evaluated in full, and who is answered by the event alone."""

    def setUp(self):
        self.held = condition("awaiting-maintainer.yml", "toggle")

    def starts(self, context: dict) -> bool:
        return decides(self.held, context)

    def test_a_green_run_from_a_fork_is_evaluated(self):
        self.assertTrue(self.starts(run(head="someone/core")))

    def test_a_green_run_a_bot_started_on_a_branch_here_is_evaluated(self):
        self.assertTrue(self.starts(run(actor="Bot")))

    def test_a_green_run_a_person_started_on_a_branch_here_starts_nothing(self):
        self.assertFalse(self.starts(run(actor="User")))

    def test_a_run_that_did_not_succeed_starts_nothing_wherever_it_came_from(self):
        for conclusion in ("failure", "cancelled", "skipped", "timed_out"):
            self.assertFalse(self.starts(run(conclusion=conclusion, head="someone/core")), conclusion)
            self.assertFalse(self.starts(run(conclusion=conclusion, actor="Bot")), conclusion)

    def test_a_close_clears_a_label_it_carries(self):
        self.assertTrue(self.starts(labelled("pull_request_target", ["awaiting-maintainer"])))

    def test_a_close_with_no_label_starts_nothing(self):
        self.assertFalse(self.starts(labelled("pull_request_target", ["ci"])))

    def test_a_review_that_decides_clears_a_label_it_carries(self):
        for state in ("approved", "changes_requested", "APPROVED"):
            self.assertTrue(self.starts(labelled("pull_request_review", ["awaiting-maintainer"], state)), state)

    def test_a_review_that_only_comments_starts_nothing(self):
        self.assertFalse(self.starts(labelled("pull_request_review", ["awaiting-maintainer"], "commented")))

    def test_a_review_on_a_pull_request_with_no_label_starts_nothing(self):
        self.assertFalse(self.starts(labelled("pull_request_review", [], "approved")))


class BuildLog(unittest.TestCase):
    """Which runs the public build log carries (OPS-R24)."""

    def setUp(self):
        self.held = condition("discord-notify.yml", "post")

    def posts(self, context: dict, build_log: bool = True) -> bool:
        return decides(self.held, {**context, "inputs": {"build-log": build_log}})

    def test_every_run_that_is_not_a_pull_requests_is_posted(self):
        for event in ("push", "schedule", "workflow_dispatch", "release", "merge_group"):
            for conclusion in ("success", "failure", "cancelled"):
                self.assertTrue(self.posts(run(conclusion=conclusion, event=event)), (event, conclusion))

    def test_a_pull_requests_run_that_failed_is_posted(self):
        for conclusion in ("failure", "timed_out", "startup_failure"):
            self.assertTrue(self.posts(run(conclusion=conclusion)), conclusion)

    def test_a_pull_requests_run_that_did_not_fail_starts_nothing(self):
        for event in ("pull_request", "pull_request_target"):
            for conclusion in ("success", "cancelled", "skipped", "neutral"):
                self.assertFalse(self.posts(run(conclusion=conclusion, event=event)), (event, conclusion))

    def test_a_message_that_is_not_for_the_build_log_is_always_posted(self):
        self.assertTrue(self.posts(run(conclusion="success"), build_log=False))
        issue = {"github": {"event_name": "issues", "event": {}}}
        self.assertTrue(self.posts(issue, build_log=False))

    def test_the_build_log_caller_says_it_is_one(self):
        read = yaml.safe_load((WORKFLOWS / "discord-build.yml").read_text(encoding="utf-8"))
        self.assertIs(read["jobs"]["notify"]["with"]["build-log"], True)


if __name__ == "__main__":
    unittest.main()
