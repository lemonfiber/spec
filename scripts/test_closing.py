#!/usr/bin/env python3
"""The citation gate shown closing, and shown not closing (Q-R66, GOV-R3).

`50-governance/cross-repo-ci.md` says a pull request without a citation is
closed, naming what was wrong. Closing somebody's work is the most consequential
thing any gate here does, so the two cases that must never be confused are
driven rather than reasoned about:

  - the contributor's fault (`spec_check.py` exit 1) closes the pull request
  - the gate's own fault (exit 2 — no spec checkout, or one holding no
    identifiers) closes nothing, because a fault on this side must never cost
    somebody their thread

And a fork, whose token is read-only however this workflow declares its
permissions, must say which happened rather than appearing to succeed.

The scripts are read out of the committed YAML through a parser, so these are
the literal texts CI runs, and `gh` is replaced on a PATH prefix by a stub.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_closing.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "spec-check.yml"
CLOSING = "Close the pull request, naming what it cited"
DECIDING = "The citation decides whether this may merge"
QUEUED = "What a merge group was, and was not, asked"
GATHERING = "Gather the text this event carries"

GH_STUB = """#!/bin/sh
# Records what was asked of it, and fails when told to.
printf '%s\\n' "$*" >> "$GH_LOG"
if [ -n "$GH_FAILS" ]; then
  echo "gh: HTTP 403: Resource not accessible by integration" >&2
  exit 1
fi
exit 0
"""


def step_script(name: str) -> str:
    """The `run:` text of a named step, as the parser hands it to the runner."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    named = [s for s in workflow["jobs"]["spec-check"]["steps"] if s.get("name") == name]
    if not named:
        raise AssertionError(f"no step named {name!r} in {WORKFLOW.name}")
    return named[0]["run"]


class Workspace:
    """The temporary tree, the `gh` stub and the runner the classes below share.

    Deliberately not a `TestCase`. Subclassing one here would make this a test
    class in its own right — collected and run, holding no tests, and reporting
    a pass that measured nothing — and `run_step` and `asked` would read as
    tests that forgot their prefix rather than as the helpers they are.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()
        gh = self.stubs / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        self.log = self.tmp / "gh.log"
        self.summary = self.tmp / "summary.md"
        self.summary.touch()
        self.work = self.tmp / "work"
        self.work.mkdir()

    def run_step(self, name, *, status="1", reason="no `Spec:` citation found", fails=False, extra=None):
        script = self.tmp / "step.sh"
        script.write_text(step_script(name), encoding="utf-8")
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GH_TOKEN": "not-a-real-token",
            "GH_LOG": str(self.log),
            "NUMBER": "42",
            "REPO": "lemonfiber/sdk-php",
            "REASON": reason,
            "STATUS": status,
            # The run page a step writes its reason to. A step that says what it
            # did not check is worth nothing if it says it only to a log nobody
            # opens, so the file is real here and read back below.
            "GITHUB_STEP_SUMMARY": str(self.summary),
        }
        if fails:
            env["GH_FAILS"] = "1"
        env.update(extra or {})
        done = subprocess.run(
            ["bash", str(script)],
            cwd=self.work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    def asked(self):
        return self.log.read_text(encoding="utf-8") if self.log.exists() else ""


class Closing(Workspace, unittest.TestCase):
    """What the gate does to a pull request it refuses."""

    def test_it_comments_before_it_closes(self):
        code, out = self.run_step(CLOSING)
        self.assertEqual(code, 0, out)
        asked = self.asked().splitlines()
        self.assertTrue(asked[0].startswith("pr comment 42"), asked)
        self.assertTrue(asked[1].startswith("pr close 42"), asked)

    def test_the_comment_says_what_was_wrong(self):
        self.run_step(CLOSING, reason="cited identifiers do not exist on spec@main: Z9-R1")
        body = next(
            p for p in self.work.glob(".close-comment.md")
        ).read_text(encoding="utf-8")
        self.assertIn("Z9-R1", body)

    def test_the_comment_says_this_is_sequencing_and_how_to_proceed(self):
        self.run_step(CLOSING)
        body = (self.work / ".close-comment.md").read_text(encoding="utf-8")
        self.assertIn("not rejection", body)
        self.assertIn("Spec:", body)
        self.assertIn("Reopen", body)

    def test_the_run_page_names_the_pull_request_it_closed(self):
        _, out = self.run_step(CLOSING)
        self.assertIn("::notice::Closed #42", out)

    def test_a_token_that_cannot_close_says_so_rather_than_passing_over_it(self):
        # A pull request from a fork is handed a read-only token whatever this
        # workflow declares, so this is the ordinary case for an outside
        # contribution — not an exotic one.
        code, out = self.run_step(CLOSING, fails=True)
        self.assertEqual(code, 0, "the refusal is the next step's to make")
        self.assertIn("::warning::Could not close #42", out)
        self.assertIn("fork", out)


class Deciding(Workspace, unittest.TestCase):
    """The refusal itself, which stands whether or not anything was closed."""

    def test_a_missing_citation_refuses_and_names_the_reason(self):
        code, out = self.run_step(DECIDING, status="1", reason="no `Spec:` citation found")
        self.assertEqual(code, 1)
        self.assertIn("no `Spec:` citation found", out)

    def test_the_gates_own_fault_refuses_without_blaming_the_pull_request(self):
        code, out = self.run_step(
            DECIDING, status="2", reason="no identifiers found in spec checkout"
        )
        self.assertEqual(code, 1)
        self.assertIn("Nothing was closed", out)
        self.assertIn("not the pull request's", out)

    def test_nothing_is_said_of_closing_where_the_contributor_is_at_fault(self):
        _, out = self.run_step(DECIDING, status="1")
        self.assertNotIn("Nothing was closed", out)


class TheRangeEachEventCarries(Workspace, unittest.TestCase):
    """What the gate reads, on each of the two events that reach it.

    The bug this closes: the range came from `github.event.pull_request` alone,
    so a merge group handed the step two empty strings and it exited 1 — failing
    a whole batch over a pull request that was never meant to be there. The
    shell is driven with each event's range in turn, over a real repository,
    because "it reads the commits" is the claim and a string comparison is not
    that claim.
    """

    def setUp(self):
        super().setUp()
        self.base, self.head = self._repo()

    def _repo(self):
        def git(*args):
            return subprocess.run(
                ["git", "-c", "user.name=T", "-c", "user.email=t@e", *args],
                cwd=self.work,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

        git("init", "-q", "-b", "main")
        (self.work / "a.md").write_text("a\n", encoding="utf-8")
        git("add", "a.md")
        git("commit", "-qm", "docs: the base this batch would land on")
        base = git("rev-parse", "HEAD")
        (self.work / "b.md").write_text("b\n", encoding="utf-8")
        git("add", "b.md")
        git("commit", "-qm", "feat: a queued change\n\nSpec: GOV-R12")
        return base, git("rev-parse", "HEAD")

    def gather(self, event, body="Spec: ONLY-IN-THE-BODY"):
        code, out = self.run_step(
            GATHERING,
            extra={
                "EVENT": event,
                "PR_BODY": body,
                "BASE_SHA": self.base,
                "HEAD_SHA": self.head,
            },
        )
        return code, out, (self.work / ".pr-text.txt").read_text(encoding="utf-8")

    def test_a_merge_group_range_is_read_rather_than_refused(self):
        code, out, text = self.gather("merge_group")
        self.assertEqual(code, 0, out)
        self.assertIn("Spec: GOV-R12", text)

    def test_a_merge_group_carries_no_body_to_read(self):
        _, _, text = self.gather("merge_group")
        self.assertNotIn("ONLY-IN-THE-BODY", text)

    def test_a_pull_request_still_reads_its_body_and_its_commits(self):
        code, out, text = self.gather("pull_request")
        self.assertEqual(code, 0, out)
        self.assertIn("ONLY-IN-THE-BODY", text)
        self.assertIn("Spec: GOV-R12", text)

    def test_a_range_that_is_not_two_shas_still_refuses_and_names_the_event(self):
        code, out = self.run_step(
            GATHERING,
            extra={"EVENT": "merge_group", "PR_BODY": "", "BASE_SHA": "", "HEAD_SHA": ""},
        )
        self.assertEqual(code, 1)
        self.assertIn("not a commit SHA on a merge_group event", out)


class AMergeGroup(Workspace, unittest.TestCase):
    """The narrower question, said out loud (GOV-R2, GOV-R3, Q-R66).

    A merge group carries no pull request, so the gate asks less of it than of a
    pull request. A check that quietly asks less is indistinguishable from one
    that asked everything and found nothing wrong, and this repository has been
    caught by that reading before — so the step that says which half ran is
    driven here rather than trusted.
    """

    def test_it_names_the_half_it_did_not_ask(self):
        code, out = self.run_step(QUEUED)
        self.assertEqual(code, 0, out)
        self.assertIn("GOV-R2", out)
        self.assertIn("not re-asked", out)

    def test_it_names_the_half_it_did_ask(self):
        _, out = self.run_step(QUEUED)
        self.assertIn("GOV-R3", out)
        self.assertIn("resolved against spec@main", out)

    def test_it_says_why_the_missing_half_is_not_a_gap(self):
        _, out = self.run_step(QUEUED)
        self.assertIn("before the queue accepted it", out)

    def test_it_writes_its_reason_to_the_run_page_as_well_as_the_log(self):
        self.run_step(QUEUED)
        written = self.summary.read_text(encoding="utf-8")
        self.assertIn("spec-check on a merge group", written)
        self.assertIn("GOV-R3", written)


class Wiring(unittest.TestCase):
    """The conditions that decide which of the two runs, read from the YAML."""

    def setUp(self):
        self.steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][
            "spec-check"
        ]["steps"]

    def named(self, name):
        return next(s for s in self.steps if s.get("name") == name)

    def test_closing_runs_only_on_the_contributors_fault_and_only_on_a_pull_request(self):
        # The second clause is not tidiness. A merge group reaches status 1 only
        # through GOV-R3 — an identifier that stopped resolving while the batch
        # waited — and the batch belongs to the queue rather than to any one
        # author, so closing there would pick a victim out of it. The refusal
        # still stands and the batch is still rejected; nobody's thread is.
        self.assertEqual(
            self.named(CLOSING)["if"],
            "steps.citation.outputs.status == '1' && github.event_name == 'pull_request'",
        )

    def test_the_refusal_runs_on_either_fault(self):
        self.assertEqual(self.named(DECIDING)["if"], "steps.citation.outputs.status != '0'")

    def test_the_check_does_not_end_the_job_before_the_two_can_run(self):
        self.assertTrue(self.named("Verify citation")["continue-on-error"])

    def test_the_range_is_named_for_both_events_rather_than_one(self):
        # The expressions cannot be evaluated here, so what is held is that both
        # are named. Only one of the two is ever non-null, and reading only the
        # first is the fault this change repairs.
        declared = self.named(GATHERING)["env"]
        for end in ("base", "head"):
            self.assertIn(f"github.event.pull_request.{end}.sha", declared[f"{end.upper()}_SHA"])
            self.assertIn(f"github.event.merge_group.{end}_sha", declared[f"{end.upper()}_SHA"])

    def test_the_merge_group_notice_runs_only_on_a_merge_group(self):
        self.assertEqual(self.named(QUEUED)["if"], "github.event_name == 'merge_group'")

    def test_the_workflow_asks_for_what_closing_needs(self):
        declared = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["permissions"]
        self.assertEqual(declared.get("pull-requests"), "write")


if __name__ == "__main__":
    unittest.main(verbosity=2)
