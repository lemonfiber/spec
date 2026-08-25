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
set -eu
printf '%s\\n' "$*" >> "${CURL_LOG:-/dev/null}"
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

    def run_step(self, declared, *, base=None, status="200", fails=False):
        """Run the step with `allowed-open: declared` against a base branch file."""
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

    def test_a_raise_is_refused(self):
        code, out = self.run_step(3, base=DECLARES.format(n=0))
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 3 on this pull request and 0 on main", out)
        self.assertIn("may only fall", out)

    def test_a_new_declaration_is_a_raise_from_the_default(self):
        code, out = self.run_step(2, base=DECLARES_NOTHING)
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 2 on this pull request and 0 on main", out)

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
        code, out = self.run_step(1, base=DECLARES_NOTHING + "#     allowed-open: 5\n")
        self.assertEqual(code, 1)
        self.assertIn("allowed-open is 1 on this pull request and 0 on main", out)

    def test_the_step_carries_no_workflow_expressions(self):
        self.assertNotIn("${{", step_script())


if __name__ == "__main__":
    unittest.main(verbosity=2)
