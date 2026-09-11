#!/usr/bin/env python3
"""The allowance a repository declares may only fall — shown refusing (Q-R66, Q-R67).

`sonar-gate.yml` lets a repository still working a SonarCloud backlog down declare
what is left as `allowed-open`. A pull request runs the workflow file its own head
declares, so without this the same diff that brings the issues could raise the
number that permits them. The first step of the gate compares this run's value
against the same declaration on the base branch and refuses a rise.

This drives that step as CI drives it: the script is read out of the committed
YAML through a YAML parser, so it is the literal text that runs, and `curl` is
replaced on a PATH prefix by a stub that answers with a chosen status and body.
A gate is worth what it refuses, so each case is checked by the exit code and by
the message a maintainer would read.

Stdlib unittest plus PyYAML (the parser is the point — a hand-rolled reader would
be testing a different string than CI runs).
Run:  python3 scripts/test_ratchet.py
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
WORKFLOW = HERE.parent / ".github" / "workflows" / "sonar-gate.yml"
STEP = "The declared allowance may only fall (Q-R67)"

# What a caller's workflow looks like on the base branch. The three shapes in the
# org today: no `with:` block at all, and an explicit number.
DECLARES_NOTHING = """name: sonar
on:
  pull_request:
jobs:
  gate:
    uses: lemonfiber/spec/.github/workflows/sonar-gate.yml@main
    secrets:
      sonar-token: ${{ secrets.SONAR_TOKEN }}
"""
DECLARES = """name: sonar
on:
  pull_request:
jobs:
  gate:
    uses: lemonfiber/spec/.github/workflows/sonar-gate.yml@main
    with:
      allowed-open: {n}
    secrets:
      sonar-token: ${{{{ secrets.SONAR_TOKEN }}}}
"""

CURL_STUB = """#!/bin/sh
# Stand in for curl. CURL_STATUS is the status it reports, CURL_BODY the file it
# copies to wherever curl was told to write the body, CURL_FAILS makes the
# process itself fail the way an unreachable host does.
#
# The step asks two different hosts — GitHub for the base branch's declaration,
# SonarCloud for what stands against that branch — so the stub answers by which
# one was called. Without that, a test setting up one of them would be silently
# answering the other as well.
set -eu
printf '%s\\n' "$*" >> "${CURL_LOG:-/dev/null}"
case "$*" in
*sonarcloud.io*)
  CURL_STATUS=${CURL_SONAR_STATUS:-200}
  CURL_BODY=${CURL_SONAR_BODY:-}
  CURL_FAILS=${CURL_SONAR_FAILS:-}
  ;;
esac
if [ "${CURL_FAILS:-}" = "1" ]; then
  exit 7
fi
out=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then
    out=$arg
  fi
  prev=$arg
done
if [ -n "$out" ]; then
  if [ -n "${CURL_BODY:-}" ]; then
    cat "$CURL_BODY" > "$out"
  else
    : > "$out"
  fi
fi
printf '%s' "${CURL_STATUS:-200}"
"""


def step_script() -> str:
    """The `run:` text of the ratchet step, as the parser hands it to the runner."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    named = [s for s in workflow["jobs"]["gate"]["steps"] if s["name"] == STEP]
    return named[0]["run"]


class Ratchet(unittest.TestCase):
    """The step, run against a stubbed GitHub."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(step_script(), encoding="utf-8")
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        curl = stubs / "curl"
        curl.write_text(CURL_STUB, encoding="utf-8")
        curl.chmod(0o755)
        self.stubs = stubs
        self.log = self.tmp / "curl.log"

    def run_step(self, declared, *, base=None, status="200", fails=False,
                 standing=None, sonar_status=None):
        """Run the step with `allowed-open: declared` against a base branch file.

        `standing` is how many issues SonarCloud reports against the base branch.
        Left out, no token reaches the step at all — which is a fork's run, and the
        case where a raise cannot be checked.
        """
        work = self.tmp / "work"
        work.mkdir(exist_ok=True)
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GH_TOKEN": "not-a-real-token",
            "API": "https://api.github.com",
            "REPO": "lemonfiber/sdk-php",
            "WORKFLOW_REF": (
                "lemonfiber/sdk-php/.github/workflows/sonar.yml@refs/pull/12/merge"
            ),
            "BASE_REF": "main",
            "ALLOWED": str(declared),
            "CURL_STATUS": status,
            "CURL_LOG": str(self.log),
        }
        if base is not None:
            body = self.tmp / "base-branch.yml"
            body.write_text(base, encoding="utf-8")
            env["CURL_BODY"] = str(body)
        if standing is not None:
            answer = self.tmp / "standing.json"
            answer.write_text(f'{{"total": {standing}}}', encoding="utf-8")
            env["SONAR_TOKEN"] = "not-a-real-token"
            env["CURL_SONAR_BODY"] = str(answer)
            env["PROJECT"] = ""
        if sonar_status is not None:
            env["CURL_SONAR_STATUS"] = sonar_status
        if fails:
            env["CURL_FAILS"] = "1"
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    # --- the raise, which is the whole reason the step exists ----------------

    def test_a_raise_past_what_stands_is_refused(self):
        code, out = self.run_step(3, base=DECLARES.format(n=0), standing=1)
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 3 on this pull request and 0 on main", out)
        self.assertIn("1 issues stand against main", out)
        self.assertIn("may name the backlog and nothing past it", out)

    def test_a_new_declaration_is_a_raise_from_the_default(self):
        code, out = self.run_step(2, base=DECLARES_NOTHING, standing=1)
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 2 on this pull request and 0 on main", out)

    def test_a_raise_that_buys_room_for_a_new_issue_is_refused(self):
        """The whole point, and the case the relaxation must not cost.

        Nothing stands against the base branch, so there is no backlog to name and
        the only thing a raise could be is room for what this diff brings.
        """
        code, out = self.run_step(1, base=DECLARES.format(n=0), standing=0)
        self.assertEqual(code, 1)
        self.assertIn("0 issues stand against main", out)

    def test_a_raise_to_the_backlog_that_stands_is_allowed(self):
        """A backlog nobody wrote — an analyser turned a rule on — can be declared.

        Without this there is no number the repository can put in its own workflow:
        the ratchet refuses everything above the zero already on the base branch,
        including on the pull request that takes the count back to zero.
        """
        code, out = self.run_step(28, base=DECLARES.format(n=0), standing=28)
        self.assertEqual(code, 0)
        self.assertIn("rises from 0 to 28", out)
        self.assertIn("rather than room for anything new", out)

    def test_a_raise_below_what_stands_is_allowed(self):
        code, out = self.run_step(20, base=DECLARES.format(n=0), standing=28)
        self.assertEqual(code, 0)
        self.assertIn("rises from 0 to 20", out)

    def test_a_raise_nobody_could_check_is_refused(self):
        """No token reaches a fork's run, so what stands cannot be read."""
        code, out = self.run_step(3, base=DECLARES.format(n=0))
        self.assertEqual(code, 1)
        self.assertIn("could not read how many issues stand against main", out)
        self.assertIn("not knowing whether the ratchet held", out)

    def test_a_sonarcloud_that_will_not_answer_leaves_a_raise_refused(self):
        code, out = self.run_step(
            3, base=DECLARES.format(n=0), standing=28, sonar_status="401"
        )
        self.assertEqual(code, 1)
        self.assertIn("could not read how many issues stand against main", out)

    def test_it_asks_sonarcloud_about_the_base_branch(self):
        self.run_step(3, base=DECLARES.format(n=0), standing=28)
        asked = self.log.read_text(encoding="utf-8")
        self.assertIn("sonarcloud.io/api/issues/search", asked)
        self.assertIn("branch=main", asked)
        self.assertIn("resolved=false", asked)

    # --- what must keep working ----------------------------------------------

    def test_a_fall_is_allowed(self):
        code, out = self.run_step(0, base=DECLARES.format(n=3))
        self.assertEqual(code, 0)
        self.assertIn("allowed-open falls from 3 to 0", out)

    def test_unchanged_is_allowed(self):
        code, out = self.run_step(0, base=DECLARES.format(n=0))
        self.assertEqual(code, 0)
        self.assertIn("allowed-open is 0 here and 0 on main", out)

    def test_declaring_nothing_on_either_side_is_allowed(self):
        code, out = self.run_step(0, base=DECLARES_NOTHING)
        self.assertEqual(code, 0)
        self.assertIn("allowed-open is 0 here and 0 on main", out)

    # --- what it does when it cannot tell ------------------------------------

    def test_an_unreadable_base_is_refused(self):
        code, out = self.run_step(3, status="404")
        self.assertEqual(code, 1)
        self.assertIn("Could not read .github/workflows/sonar.yml on main (HTTP 404)", out)
        self.assertIn("cannot tell whether allowed-open: 3 is a raise", out)

    def test_an_unauthorised_base_is_refused_too(self):
        code, out = self.run_step(1, status="401")
        self.assertEqual(code, 1)
        self.assertIn("(HTTP 401)", out)

    def test_a_curl_that_never_answered_is_refused(self):
        code, out = self.run_step(1, fails=True)
        self.assertEqual(code, 1)
        self.assertIn("(HTTP 000)", out)

    def test_zero_needs_no_base(self):
        code, out = self.run_step(0, status="500")
        self.assertEqual(code, 0)
        self.assertIn("no count is below zero", out)

    def test_a_value_that_is_not_a_whole_number_is_refused(self):
        code, out = self.run_step("1.5", base=DECLARES.format(n=9))
        self.assertEqual(code, 1)
        self.assertIn("must be a whole number", out)

    # --- it has to be asking the right thing ---------------------------------

    def test_it_reads_the_callers_file_on_the_base_branch(self):
        self.run_step(0, base=DECLARES_NOTHING)
        asked = self.log.read_text(encoding="utf-8")
        self.assertIn(
            "https://api.github.com/repos/lemonfiber/sdk-php/contents/"
            ".github/workflows/sonar.yml?ref=main",
            asked,
        )

    def test_a_commented_out_declaration_is_not_read(self):
        code, out = self.run_step(
            1, base=DECLARES_NOTHING + "#     allowed-open: 5\n", standing=0
        )
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 1 on this pull request and 0 on main", out)

    def test_the_step_carries_no_workflow_expressions(self):
        self.assertNotIn("${{", step_script())


if __name__ == "__main__":
    unittest.main(verbosity=2)
