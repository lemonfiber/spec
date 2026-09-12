#!/usr/bin/env python3
"""A PR citing a locked goal lands in that version's milestone — OPS-R39, Q-R66.

OPS-R39 asks for two things: the label, and the milestone. `goal-automations.yml`
did the first and never touched the second, and no repository in the org held a
milestone for any version — so the half that was implemented had nothing to be
half of. This is the second half, shown working before it is relied on.

Driven the way `test_ratchet.py` drives the ratchet: the step's script is read out
of the committed YAML through a YAML parser, so what runs here is the literal text
CI runs rather than a paraphrase of it, and `gh` is replaced on a PATH prefix by a
stub that answers a chosen forge and records every call. A gate is worth what it
does on the day, so each case is checked by the calls it made and not by its exit
code, which is zero in every branch by design.

Stdlib unittest plus PyYAML (the parser is the point).
Run:  python3 scripts/test_milestone.py
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
WORKFLOW = HERE.parent / ".github" / "workflows" / "goal-automations.yml"
STEP = "Classify and act"

#: A staged version, as a manifest writes one. `delivers` is what the milestone's
#: description has to come from; a second sentence written in the workflow would be
#: the same fact twice and would drift the first time either was edited.
MANIFEST = """version = "0.15.0"
milestone = "M9"
delivers  = "Away from the keyboard — remote control, autostart, customisation"
status  = "staged"
repos   = ["lemonfiber"]
goals   = ["B6-R1", "B8-R1", "F1-R5"]
"""

#: One that is not in flight, so nothing about it may be acted on.
RELEASED = """version = "0.14.0"
status  = "released"
repos   = ["lemonfiber"]
goals   = ["E1-R1"]
"""

GH_STUB = """#!/bin/sh
# Stand in for `gh`. Every invocation is appended to GH_LOG; the answer depends on
# which endpoint was asked for, because a stub that answers the same thing to every
# question is one that silently answers the wrong one.
#
#   EXISTING  the milestone number a lookup by title finds, or empty for none
#   MADE      the number a creation returns, or empty where it could not create one
set -eu
printf '%s\\n' "$*" >> "$GH_LOG"
case "$*" in
*"--method POST"*milestones*) printf '%s' "${MADE:-}" ;;
*milestones*)                 printf '%s' "${EXISTING:-}" ;;
*comments*--jq*)              : ;;
*)                            : ;;
esac
exit 0
"""


def step_script() -> str:
    """The `Classify and act` step's shell, out of the committed workflow."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for step in workflow["jobs"]["classify"]["steps"]:
        if step.get("name") == STEP:
            return step["run"]
    raise AssertionError(f"no step named {STEP!r} in {WORKFLOW}")


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "scripts").mkdir()
        for name in ("pr_goals.py", "patterns.py"):
            shutil.copy(HERE / name, self.tmp / "scripts" / name)
        (self.tmp / "70-operations" / "versions").mkdir(parents=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        stub = self.bin / "gh"
        stub.write_text(GH_STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.log = self.tmp / "gh.log"
        self.log.touch()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manifest(self, body=MANIFEST, name="0.15.0"):
        (self.tmp / "70-operations" / "versions" / f"{name}.toml").write_text(
            body, encoding="utf-8"
        )

    def act(self, trailer="Spec: B6-R1", existing="", made="7"):
        (self.tmp / "pr.txt").write_text(f"a change\n\n{trailer}\n", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.log),
            "GH_TOKEN": "stub",
            "REPO": "lemonfiber/lemonfiber",
            "PR": "42",
            "EXISTING": existing,
            "MADE": made,
        }
        done = subprocess.run(
            ["bash", "-c", step_script()], cwd=self.tmp, env=env,
            capture_output=True, text=True,
        )
        return done, self.log.read_text(encoding="utf-8")


class TheStepIsTheCommittedOne(Run):
    def test_the_script_was_read_out_of_the_workflow(self):
        """Assert what is being driven before what it does.

        A reader that returned an empty string would make every test below pass
        about nothing, which is the shape this whole file exists to refuse one
        level down.
        """
        script = step_script()
        self.assertIn("scripts/pr_goals.py", script)
        self.assertIn("milestone", script)


class APrCitingALockedGoal(Run):
    def test_it_is_put_in_the_version_s_milestone(self):
        self.manifest()
        done, log = self.act()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("--method PATCH repos/lemonfiber/lemonfiber/issues/42", log)
        self.assertIn("-F milestone=7", log)

    def test_it_still_gets_the_version_label(self):
        """The half that already worked is asserted too, so a change that trades
        one for the other cannot pass."""
        self.manifest()
        _, log = self.act()
        self.assertIn("label create v0.15.0", log)
        self.assertIn("pr edit 42", log)
        self.assertIn("--add-label v0.15.0", log)

    def test_the_milestone_is_made_where_the_repository_has_none(self):
        """No repository in the org has ever had one, so applying-only does nothing."""
        self.manifest()
        _, log = self.act(existing="", made="7")
        self.assertIn("--method POST repos/lemonfiber/lemonfiber/milestones", log)
        self.assertIn("title=v0.15.0", log)

    def test_the_description_is_the_manifest_s_own_words(self):
        """Carried from `delivers` rather than written again in the workflow."""
        self.manifest()
        _, log = self.act()
        self.assertIn(
            "description=Away from the keyboard — remote control, autostart, "
            "customisation",
            log,
        )

    def test_an_existing_milestone_is_used_rather_than_a_second_one_made(self):
        """Every PR of a version runs this. A second milestone per PR would be the
        release train rewritten once per contribution."""
        self.manifest()
        _, log = self.act(existing="3", made="99")
        self.assertNotIn("--method POST repos/lemonfiber/lemonfiber/milestones", log)
        self.assertIn("-F milestone=3", log)

    def test_the_lookup_asks_for_every_state(self):
        """A version's milestone is closed when it ships; a hotfix citing one of its
        goals afterwards belongs in that milestone, not in a new one beside it."""
        self.manifest()
        _, log = self.act(existing="3")
        self.assertIn("state=all", log)


class WhenNoMilestoneCanBeHad(Run):
    def test_it_says_so_rather_than_assigning_nothing(self):
        """A caller granting too little permission gets the label and no milestone.

        Silence there is the failure this rule has already had once: a half nobody
        noticed was missing. `milestone=` with nothing after it would be a PATCH
        the forge rejects and a log line nobody reads.
        """
        self.manifest()
        done, log = self.act(existing="", made="")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("::warning::no milestone v0.15.0", done.stdout)
        self.assertNotIn("-F milestone=\n", log + "\n")
        self.assertNotIn("--method PATCH repos/lemonfiber/lemonfiber/issues/42", log)


class WhatIsNotInScope(Run):
    def test_an_out_of_scope_pr_gets_no_milestone(self):
        """`scope:next` says this is for another version. Putting it in this one's
        milestone would say the opposite, on the same pull request."""
        self.manifest()
        _, log = self.act(trailer="Spec: Z9-R1")
        self.assertIn("--add-label scope:next", log)
        self.assertNotIn("milestones", log)
        self.assertNotIn("-F milestone", log)

    def test_a_pr_citing_nothing_is_left_alone(self):
        self.manifest()
        _, log = self.act(trailer="no trailer here")
        self.assertEqual(log.strip(), "")

    def test_nothing_staged_means_nothing_done(self):
        self.manifest(body=RELEASED, name="0.14.0")
        done, log = self.act()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(log.strip(), "")


if __name__ == "__main__":
    unittest.main()
