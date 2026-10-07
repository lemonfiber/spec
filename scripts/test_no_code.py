#!/usr/bin/env python3
"""A change that touches no code is answered at once, and the backlog still counts (Q-R64).

A caller whose `what changed` job finds every changed path to be one no
code-judging job reads skips its SonarCloud scan and passes `code: false`. No
summary is coming, so the issue gate must not spend its five-minute wait on one,
and nothing the change touched can carry a new issue. The open count is the
repository's rather than the change's, so it is still read and still blocks
above `allowed-open` (Q-R67).

Drives the step as CI drives it, through the harness `test_no_token.py` uses:
the script is the literal `run:` text out of the committed YAML, and `gh`, `curl`
and `sleep` are replaced on a PATH prefix.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_no_code.py
"""

from __future__ import annotations

import unittest

from test_no_token import Harness


class NoCode(Harness, unittest.TestCase):
    """The step on a pull request with a token, its caller having found no code."""

    def run_with(self, *, code="false", open_issues=0):
        return self.run_step(
            author="a-contributor",
            token="a-token",
            PR="906",
            CODE=code,
            CURL_STATUS=200,
            CURL_BODY=f'{{"total": {open_issues}}}',
        )

    def test_no_code_passes_without_waiting_for_a_summary(self):
        code, out = self.run_with()
        self.assertEqual(code, 0, out)
        self.assertFalse(self.slept.exists(), "the step waited for a summary no scan will write")
        self.assertNotIn("pulls/906", self.log.read_text(encoding="utf-8"))
        self.assertIn("no SonarCloud analysis ran", self.verdict())

    def test_no_code_still_reports_the_standing_count(self):
        self.run_with()
        self.assertIn("Open issues against `lemonfiber_lemonfiber`: **0**", self.verdict())

    def test_no_code_still_blocks_a_backlog_above_the_allowance(self):
        code, out = self.run_with(open_issues=3)
        self.assertEqual(code, 1)
        self.assertIn("Issue gate failed", self.verdict())
        self.assertIn("**3 open issues**", self.verdict())
        self.assertIn("::error::3 open issues", out)

    def test_code_still_waits_for_the_summary(self):
        code, out = self.run_with(code="true")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.slept.exists(), "a change with code was not waited for")
        self.assertIn("posted no summary within the timeout", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
