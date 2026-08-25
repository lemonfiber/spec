#!/usr/bin/env python3
"""A run with no token says which kind of run it was, rather than passing quietly (Q-R66).

`sonar-gate.yml` blocks on a counted SonarCloud issue and on nothing else, so the
paths where it counts nothing are the ones worth holding to a standard. Without a
`SONAR_TOKEN` there is no analysis to read, and the gate passes — but a check that
goes green having read nothing and explains itself nowhere cannot be told apart
from one that looked and found nothing wrong.

Two kinds of run arrive that way and the step used to report them as one. A pull
request from a fork is given no secrets. A pull request Dependabot opened reads the
Dependabot secret store rather than the Actions store, so `SONAR_TOKEN` is empty
and the scan that would produce a summary is skipped for that reason; calling that
a fork's sends whoever reads it looking for the wrong thing.

This drives the step as CI drives it, the way `test_ratchet.py` drives its sibling:
the script is read out of the committed YAML through a YAML parser, so it is the
literal text that runs, and `gh` and `curl` are replaced on a PATH prefix. Each
case is checked by the exit code, by the message a maintainer would read, and by
the verdict reaching somewhere it can be read from.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_no_token.py
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
STEP = "Enforce zero new SonarCloud issues (Q-R64)"
DEPENDABOT = "dependabot[bot]"

# Stand in for `gh`. GH_LOG records what was asked, GH_COMMENT_ID is what the
# search for an existing verdict answers, GH_FAILS makes every call fail the way a
# token that may not write does.
GH_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "${GH_LOG:-/dev/null}"
if [ "${GH_FAILS:-}" = "1" ]; then
  exit 1
fi
case "$*" in
*"-X POST"* | *"-X PATCH"*) exit 0 ;;
esac
printf '%s' "${GH_ANSWER:-}"
"""

# Stand in for `curl`, which is reached only once a token is present. It answers
# every request with the status in CURL_STATUS and an empty body.
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
  : > "$out"
fi
printf '%s' "${CURL_STATUS:-404}"
"""

# The wait between polls, which is five minutes of real time the assertions do not
# need. Only the tokened case reaches it.
SLEEP_STUB = "#!/bin/sh\nexit 0\n"


def step_script() -> str:
    """The `run:` text of the issue-gate step, as the parser hands it to the runner."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    named = [s for s in workflow["jobs"]["gate"]["steps"] if s["name"] == STEP]
    return named[0]["run"]


class NoToken(unittest.TestCase):
    """The step, run against a stubbed GitHub with no SonarCloud token."""

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
        self.summary = self.tmp / "summary.md"
        self.summary.touch()

    def run_step(self, *, author, token="", gh_fails=False):
        """Run the step as the pull request of `author`, with `token` as SONAR_TOKEN."""
        work = self.tmp / "work"
        work.mkdir(exist_ok=True)
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GITHUB_REPOSITORY": "lemonfiber/lemonfiber",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GH_TOKEN": "not-a-real-token",
            "SONAR_TOKEN": token,
            "PR": "384",
            "BOT": "sonarqubecloud[bot]",
            "AUTHOR": author,
            "DEPENDABOT": DEPENDABOT,
            "MARKER": "<!-- lemonfiber:issue-gate -->",
            "PROJECT": "",
            "ALLOWED": "0",
            "GH_LOG": str(self.log),
        }
        if gh_fails:
            env["GH_FAILS"] = "1"
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

    # --- the two runs are told apart -----------------------------------------

    def test_a_bot_run_is_named_as_one(self):
        code, out = self.run_step(author=DEPENDABOT)
        self.assertEqual(code, 0)
        self.assertIn(f"Scan deliberately skipped for a {DEPENDABOT} pull request", out)
        self.assertIn("deliberately skipped", self.verdict())

    def test_a_fork_run_is_not_reported_as_the_bot(self):
        code, out = self.run_step(author="a-contributor")
        self.assertEqual(code, 0)
        self.assertNotIn("dependabot", out.lower())
        self.assertIn("No SONAR_TOKEN reached this run", out)
        self.assertIn("fork", self.verdict())

    # --- neither goes green in silence ---------------------------------------

    def test_a_bot_run_says_the_requirement_went_unenforced(self):
        _, out = self.run_step(author=DEPENDABOT)
        self.assertIn("::warning::", out)
        self.assertIn("Q-R64 was not enforced on this run", out)
        self.assertIn("`Q-R64` was not enforced on this run", self.verdict())

    def test_a_fork_run_says_the_requirement_went_unenforced(self):
        _, out = self.run_step(author="a-contributor")
        self.assertIn("::warning::", out)
        self.assertIn("Q-R64 was not enforced on this run", out)
        self.assertIn("`Q-R64` was not enforced on this run", self.verdict())

    def test_the_verdict_is_posted_as_well_as_summarised(self):
        self.run_step(author=DEPENDABOT)
        self.assertIn("-X POST", self.log.read_text(encoding="utf-8"))

    def test_a_verdict_that_cannot_be_posted_still_reaches_the_summary(self):
        code, out = self.run_step(author=DEPENDABOT, gh_fails=True)
        self.assertEqual(code, 0)
        self.assertIn("Could not post the verdict comment", out)
        self.assertIn("deliberately skipped", self.verdict())

    # --- and the skip is the token's doing, not the author's ------------------

    def test_a_bot_run_that_does_have_a_token_is_gated_like_any_other(self):
        code, out = self.run_step(author=DEPENDABOT, token="a-token")
        self.assertEqual(code, 0)
        self.assertNotIn("deliberately skipped", out)
        self.assertIn("posted no summary within the timeout", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
