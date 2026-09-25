#!/usr/bin/env python3
"""Every required check answers a merge queue, and none answers it with a skip (Q-R37, Q-R66).

A merge queue asks for every context `main` requires again, on a branch of its
own, under the `merge_group` event. A context that never reports there is read
as a wait and the pull request is dropped at the timeout, naming nothing. A job
that reads the pull request, finds none, and skips is worse: a skipped required
check reports success, and the queue merges a batch nothing read.

This holds both. The workflows that produce `main`'s required contexts are read
for the trigger, and the steps that used to skip without a pull request are run
as CI runs them — the script read out of the committed YAML through a YAML
parser, so it is the literal text that runs, with `curl` and `gh` replaced on a
PATH prefix — and shown refusing a batch they cannot read.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_merge_group.py
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
WORKFLOWS = HERE.parent / ".github" / "workflows"

# The workflows `main`'s required contexts come from here. `SonarCloud Code
# Analysis` is not among them: an app posts it, and it does not post on a queue's
# branch, so `gate / gate` from `sonar` is what `main` requires in its place.
REQUIRED_FROM = (
    "attribution",
    "codeql",
    "commitlint",
    "coverage",
    "dco",
    "docs",
    "hygiene",
    "integrity",
    "security",
    "sonar",
    "workflow-pins",
)

# The three shared gates that read a base..head range off the event, and the
# step in each that does.
RANGED = {
    "dco": ("dco", "Check sign-off"),
    "attribution": ("attribution", "Check the record"),
    "commitlint": ("commitlint", "Lint commit subjects"),
}

MERGE_GROUP_STEP = "Every pull request in the batch carries zero new issues (Q-R64)"

BASE = "a" * 40
HEAD = "b" * 40

# Stand in for `curl`. It answers by what was asked: the project lookup, the open
# count, or one pull request's new-issue count, each from its own variable.
CURL_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "${CURL_LOG:-/dev/null}"
out=""
prev=""
url=""
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then
    out=$arg
  fi
  prev=$arg
  url=$arg
done
case "$url" in
*components/show*)
  printf '%s' "${CURL_PROJECT_STATUS:-200}"
  exit 0
  ;;
*pullRequest=*)
  pr=${url#*pullRequest=}
  pr=${pr%%&*}
  status=$(eval "printf '%s' \\"\\${CURL_PR_STATUS_${pr}:-200}\\"")
  total=$(eval "printf '%s' \\"\\${CURL_PR_TOTAL_${pr}:-0}\\"")
  ;;
*)
  status=${CURL_OPEN_STATUS:-200}
  total=${CURL_OPEN_TOTAL:-0}
  ;;
esac
if [ -n "$out" ] && [ "$out" != /dev/null ]; then
  printf '{"total": %s}' "$total" > "$out"
fi
printf '%s' "$status"
"""

# Stand in for `gh`. The compare call answers with GH_SUBJECTS, one per line; a
# pull request lookup answers with GH_AUTHOR; GH_COMPARE_FAILS fails the compare.
GH_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "${GH_LOG:-/dev/null}"
case "$*" in
*compare/*)
  if [ "${GH_COMPARE_FAILS:-}" = "1" ]; then
    exit 1
  fi
  printf '%s' "${GH_SUBJECTS:-}"
  ;;
*pulls/*)
  printf '%s\\n' "${GH_AUTHOR:-a-contributor}"
  ;;
esac
"""


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8"))


def triggers(name: str) -> dict:
    """The `on:` block, which PyYAML reads as the boolean `True`."""
    workflow = load(name)
    return workflow.get("on", workflow.get(True))


def step(name: str, job: str, title: str) -> dict:
    return next(s for s in load(name)["jobs"][job]["steps"] if s.get("name") == title)


class EveryRequiredWorkflowRunsInTheQueue(unittest.TestCase):
    def test_each_declares_merge_group(self):
        missing = [name for name in REQUIRED_FROM if "merge_group" not in triggers(name)]
        self.assertEqual(missing, [])

    def test_the_sonar_gate_runs_on_a_merge_group_rather_than_skipping(self):
        jobs = load("sonar-gate")["jobs"]
        self.assertIn("merge_group", jobs["gate"]["if"])
        self.assertIn("!= 'merge_group'", jobs["not-a-pull-request"]["if"])

    def test_the_batch_step_runs_only_on_a_merge_group(self):
        batch = step("sonar-gate", "gate", MERGE_GROUP_STEP)
        self.assertEqual(batch["if"], "github.event_name == 'merge_group'")
        single = step("sonar-gate", "gate", "Enforce zero new SonarCloud issues (Q-R64)")
        self.assertEqual(single["if"], "github.event_name == 'pull_request'")


class TheRangedGatesReadTheBatch(unittest.TestCase):
    """dco, attribution and commitlint, on the event that used to skip them."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_step(self, name: str, event: str):
        """Run the step as `event` delivers it when no range reached the job."""
        job, title = RANGED[name]
        script = self.tmp / f"{name}.sh"
        script.write_text(step(name, job, title)["run"], encoding="utf-8")
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.tmp),
            "EVENT": event,
            "BASE_SHA": "",
            "HEAD_SHA": "",
            "PR_BODY": "",
            "GITHUB_REPOSITORY": "lemonfiber/sdk-php",
        }
        done = subprocess.run(
            ["bash", str(script)],
            cwd=self.tmp,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    def test_each_names_the_merge_group_range(self):
        for name, (job, title) in RANGED.items():
            with self.subTest(name):
                declared = step(name, job, title)["env"]
                self.assertIn("github.event.merge_group.base_sha", declared["BASE_SHA"])
                self.assertIn("github.event.merge_group.head_sha", declared["HEAD_SHA"])
                self.assertEqual(declared["EVENT"], "${{ github.event_name }}")

    def test_a_merge_group_without_a_range_is_refused(self):
        for name in RANGED:
            with self.subTest(name):
                code, out = self.run_step(name, "merge_group")
                self.assertEqual(code, 1, out)
                self.assertIn("A merge group arrived without a base..head range", out)
                self.assertNotIn("skipping", out)

    def test_a_push_still_says_it_had_no_range(self):
        for name in RANGED:
            with self.subTest(name):
                code, out = self.run_step(name, "push")
                self.assertEqual(code, 0, out)
                self.assertIn("no PR range; skipping", out)


class TheSonarGateAsksTheBatch(unittest.TestCase):
    """The batch step, run against a stubbed SonarCloud and GitHub."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(
            step("sonar-gate", "gate", MERGE_GROUP_STEP)["run"], encoding="utf-8"
        )
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()
        for name, body in (("curl", CURL_STUB), ("gh", GH_STUB)):
            stub = self.stubs / name
            stub.write_text(body, encoding="utf-8")
            stub.chmod(0o755)
        self.summary = self.tmp / "summary.md"
        self.summary.touch()
        self.curl_log = self.tmp / "curl.log"
        self.gh_log = self.tmp / "gh.log"

    def run_step(self, *, token="not-a-real-token", subjects="feat: a thing (#12)", **extra):
        work = self.tmp / "work"
        work.mkdir(exist_ok=True)
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GH_TOKEN": "not-a-real-token",
            "SONAR_TOKEN": token,
            "PROJECT": "",
            "ALLOWED": "0",
            "REPO": "lemonfiber/spec",
            "BASE_SHA": BASE,
            "HEAD_SHA": HEAD,
            "DEPENDABOT": "dependabot[bot]",
            "GH_SUBJECTS": subjects,
            "CURL_LOG": str(self.curl_log),
            "GH_LOG": str(self.gh_log),
        }
        env.update({key: str(value) for key, value in extra.items()})
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    def summarised(self) -> str:
        return self.summary.read_text(encoding="utf-8")

    # --- a clean batch passes, and says what it read ---------------------------

    def test_a_clean_batch_passes_naming_each_pull_request(self):
        code, out = self.run_step(subjects="feat: one (#12)\nfix: two (#13)")
        self.assertEqual(code, 0, out)
        self.assertIn("#12: 0 new issues.", out)
        self.assertIn("#13: 0 new issues.", out)
        self.assertIn("No new issues on #12, #13", self.summarised())
        asked = self.curl_log.read_text(encoding="utf-8")
        self.assertIn("projects=lemonfiber_spec&pullRequest=12&", asked)
        self.assertIn("projects=lemonfiber_spec&pullRequest=13&", asked)
        compared = self.gh_log.read_text(encoding="utf-8")
        self.assertIn(f"repos/lemonfiber/spec/compare/{BASE}...{HEAD}", compared)

    # --- what it refuses -------------------------------------------------------

    def test_a_new_issue_on_any_pull_request_refuses_the_batch(self):
        code, out = self.run_step(
            subjects="feat: one (#12)\nfix: two (#13)", CURL_PR_TOTAL_13=2
        )
        self.assertEqual(code, 1)
        self.assertIn("#13 carries 2 new issue(s); this repository requires zero (Q-R64)", out)
        self.assertIn("refused this batch", self.summarised())

    def test_an_open_count_above_the_allowance_is_refused(self):
        code, out = self.run_step(CURL_OPEN_TOTAL=3)
        self.assertEqual(code, 1)
        self.assertIn("3 open issues against lemonfiber_spec; this repository declares allowed-open: 0", out)

    def test_an_open_count_within_the_allowance_passes(self):
        code, out = self.run_step(CURL_OPEN_TOTAL=3, ALLOWED=3)
        self.assertEqual(code, 0, out)

    def test_no_token_is_refused_rather_than_passed(self):
        code, out = self.run_step(token="")
        self.assertEqual(code, 1)
        self.assertIn("No SONAR_TOKEN reached this merge group", out)

    def test_a_project_that_does_not_resolve_is_refused(self):
        code, out = self.run_step(CURL_PROJECT_STATUS=404)
        self.assertEqual(code, 1)
        self.assertIn("No SonarCloud project called lemonfiber_spec could be read (HTTP 404)", out)

    def test_an_unreadable_open_count_is_refused(self):
        code, out = self.run_step(CURL_OPEN_STATUS=503)
        self.assertEqual(code, 1)
        self.assertIn("Could not read the open-issue count for lemonfiber_spec (HTTP 503)", out)

    def test_an_unreadable_new_count_is_refused(self):
        code, out = self.run_step(CURL_PR_STATUS_12=503)
        self.assertEqual(code, 1)
        self.assertIn("Could not read the new-issue count for #12 (HTTP 503)", out)

    def test_a_commit_naming_no_pull_request_is_refused(self):
        code, out = self.run_step(subjects="feat: one (#12)\nfeat: pushed around the queue")
        self.assertEqual(code, 1)
        self.assertIn('naming no pull request: "feat: pushed around the queue"', out)

    def test_an_unreadable_batch_is_refused(self):
        code, out = self.run_step(GH_COMPARE_FAILS=1)
        self.assertEqual(code, 1)
        self.assertIn("so the pull requests in this batch are unknown", out)

    def test_an_empty_batch_is_refused(self):
        code, out = self.run_step(subjects="")
        self.assertEqual(code, 1)
        self.assertIn("a pass would be about nothing", out)

    # --- the one allowance, which the pull request's own run also made ---------

    def test_a_dependabot_pull_request_without_a_count_is_named_and_passed(self):
        code, out = self.run_step(CURL_PR_STATUS_12=404, GH_AUTHOR="dependabot[bot]")
        self.assertEqual(code, 0, out)
        self.assertIn("#12 was opened by dependabot[bot]", out)
        self.assertIn("Q-R64 was not enforced on it here", out)

    def test_the_step_carries_no_workflow_expressions(self):
        run = step("sonar-gate", "gate", MERGE_GROUP_STEP)["run"]
        self.assertNotIn("${{", run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
