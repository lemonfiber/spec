#!/usr/bin/env python3
"""The step that refuses a lychee `accept` list which cannot run (Q-R54).

The shared link check passes `--accept` on the command line, and a command-line
argument beats a config file. Five repositories carried
``accept = ["200", "206", "429"]`` in their own `lychee.toml` and not one of
those lists had ever been consulted — they held the same three codes as the one
that ran, so nothing ever disagreed and nothing caught it.

That is the worse half of a duplication: not two values disagreeing, but two
values agreeing while only one is read. On 2026-09-13 SonarCloud answered 503 for
over an hour, `hygiene / links` went red on a pull request that touched no link,
and the obvious fix was to add `503` to one of those dead lists.

This drives the step as CI drives it: the shell is read out of the committed YAML
through a parser, so it is the literal text that runs rather than a copy of it.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_dead_accept.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "hygiene.yml"
STEP = "An accept list in the caller's config is not the one that runs"


def step_script() -> str:
    """The step's shell, as the parser hands it to the runner."""
    named = [
        s
        for s in yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["links"]["steps"]
        if s.get("name") == STEP
    ]
    if not named:
        raise AssertionError(f"no step named {STEP!r} in the links job")
    return named[0]["run"]


class ADeadAcceptList(unittest.TestCase):
    """A tree with a `lychee.toml`, and what the step says about it."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(step_script(), encoding="utf-8")
        self.work = self.tmp / "work"
        self.work.mkdir()

    def config(self, text: str) -> None:
        (self.work / "lychee.toml").write_text(text, encoding="utf-8")

    def run_step(self):
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=self.work,
            env={"GITHUB_STEP_SUMMARY": str(self.tmp / "summary.md"), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    # --- the fixture has to be saying something -----------------------------

    def test_the_step_was_read_out_of_the_workflow(self):
        """Every case below runs this text. An empty read would pass them all."""
        script = step_script()
        self.assertIn("accept", script)
        self.assertIn("lychee.toml", script)
        self.assertGreater(len(script.splitlines()), 10)

    # --- what it refuses ----------------------------------------------------

    def test_a_config_declaring_an_accept_list(self):
        self.config('hidden = true\naccept = ["200", "206", "429"]\n')
        code, out = self.run_step()
        self.assertEqual(code, 1, out)
        self.assertIn("has never been consulted", out)
        self.assertIn("hygiene.yml", out)

    def test_an_accept_list_that_is_indented(self):
        # TOML permits it and a reader skims past it, which is the case a naive
        # `grep "^accept"` would let through.
        self.config('  accept = ["200"]\n')
        self.assertEqual(self.run_step()[0], 1)

    def test_an_accept_list_with_space_before_the_equals(self):
        self.config('accept   = ["200"]\n')
        self.assertEqual(self.run_step()[0], 1)

    # --- what it lets through -----------------------------------------------

    def test_a_repo_with_no_lychee_config(self):
        # Most repositories have none, and the shared list is then the only one.
        code, out = self.run_step()
        self.assertEqual(code, 0, out)
        self.assertIn("the list below is the only one", out)

    def test_a_config_that_declares_no_accept_list(self):
        self.config(
            "hidden = true\n"
            "max_retries = 2\n"
            "# There is deliberately no `accept` list here.\n"
            "exclude_loopback = true\n"
        )
        code, out = self.run_step()
        self.assertEqual(code, 0, out)
        self.assertIn("declares no accept list", out)

    def test_a_comment_mentioning_accept_is_not_a_declaration(self):
        # The paragraph that replaced the list says the word `accept` several
        # times. A check that refused its own explanation would be refused by
        # every repository that took the advice.
        self.config(
            "# There was an `accept` list here and it never ran. The one that\n"
            "# runs passes --accept on the command line.\n"
            "#   accept = [\"200\", \"206\", \"429\"]\n"
            "max_retries = 2\n"
        )
        code, out = self.run_step()
        self.assertEqual(code, 0, out)

    def test_a_key_merely_ending_in_accept(self):
        self.config('do_not_accept = ["500"]\n')
        self.assertEqual(self.run_step()[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
