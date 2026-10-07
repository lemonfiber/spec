#!/usr/bin/env python3
"""A change that touches no code is answered at once, and the backlog still counts (Q-R64).

A caller whose `what changed` job finds every changed path to be one no
code-judging job reads skips its SonarCloud scan and passes `code: false`. No
summary is coming, so the issue gate must not spend its five-minute wait on one,
and nothing the change touched can carry a new issue. The open count is the
repository's rather than the change's, so it is still read and still blocks
above `allowed-open` (Q-R67).

Drives the step as CI drives it, the way `test_no_token.py` does: the script is
the literal `run:` text out of the committed YAML, and `gh`, `curl` and `sleep`
are replaced on a PATH prefix.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_no_code.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from test_no_token import GH_STUB, step_script

# Stand in for `curl`: every request answers CURL_STATUS with CURL_BODY written
# where `-o` asked, so the project lookup and the open count both read it.
CURL_STUB = """#!/bin/sh
set -eu
out=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then
    out=$arg
  fi
  prev=$arg
done
if [ -n "$out" ]; then
  printf '%s' "${CURL_BODY:-}" > "$out"
fi
printf '%s' "${CURL_STATUS:-200}"
"""

# Records each wait, so a test can say the step never polled for a summary.
SLEEP_STUB = """#!/bin/sh
printf 'slept\\n' >> "${SLEEP_LOG:-/dev/null}"
exit 0
"""


class NoCode(unittest.TestCase):
    """The step, run with a token and `code: false`."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(step_script(), encoding="utf-8")
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()
        for name, body in (("gh", GH_STUB), ("curl", CURL_STUB), ("sleep", SLEEP_STUB)):
            stub = self.stubs / name
            stub.write_text(body, encoding="utf-8")
            stub.chmod(0o755)
        self.log = self.tmp / "gh.log"
        self.slept = self.tmp / "sleep.log"
        self.summary = self.tmp / "summary.md"
        self.summary.touch()

    def run_step(self, *, code="false", open_issues=0, allowed="0"):
        """Run the step on a pull request with a token, `open_issues` standing open."""
        work = self.tmp / "work"
        work.mkdir(exist_ok=True)
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GITHUB_REPOSITORY": "lemonfiber/lemonfiber",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GH_TOKEN": "not-a-real-token",
            "SONAR_TOKEN": "a-token",
            "PR": "906",
            "BOT": "sonarqubecloud[bot]",
            "AUTHOR": "a-contributor",
            "DEPENDABOT": "dependabot[bot]",
            "MARKER": "<!-- lemonfiber:issue-gate -->",
            "PROJECT": "",
            "ALLOWED": allowed,
            "CODE": code,
            "CURL_BODY": f'{{"total": {open_issues}}}',
            "GH_LOG": str(self.log),
            "SLEEP_LOG": str(self.slept),
        }
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    def verdict(self) -> str:
        return self.summary.read_text(encoding="utf-8")

    def test_no_code_passes_without_waiting_for_a_summary(self):
        code, out = self.run_step()
        self.assertEqual(code, 0, out)
        self.assertFalse(self.slept.exists(), "the step waited for a summary no scan will write")
        self.assertNotIn("pulls/906", self.log.read_text(encoding="utf-8"))
        self.assertIn("no SonarCloud analysis ran", self.verdict())

    def test_no_code_still_reports_the_standing_count(self):
        self.run_step()
        self.assertIn("Open issues against `lemonfiber_lemonfiber`: **0**", self.verdict())

    def test_no_code_still_blocks_a_backlog_above_the_allowance(self):
        code, out = self.run_step(open_issues=3)
        self.assertEqual(code, 1)
        self.assertIn("Issue gate failed", self.verdict())
        self.assertIn("**3 open issues**", self.verdict())
        self.assertIn("::error::3 open issues", out)

    def test_code_still_waits_for_the_summary(self):
        code, out = self.run_step(code="true")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.slept.exists(), "a change with code was not waited for")
        self.assertIn("posted no summary within the timeout", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
