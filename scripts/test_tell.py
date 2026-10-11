#!/usr/bin/env python3
"""`tell.yml` tells each repository named, refuses what it cannot send, and fails over a silence.

Driven the way `test_milestone.py` drives its workflow: each step's script is read
out of the committed YAML through a YAML parser, so what runs here is the literal
text CI runs, and `gh` is replaced on a PATH prefix by a stub that records every
call and refuses the repositories it is told to.

Stdlib unittest plus PyYAML (the parser is the point).
Run:  python3 scripts/test_tell.py
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "tell.yml"

GH_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$GH_LOG"
for refused in ${REFUSED:-}; do
  case "$*" in *"/${refused}"*) exit 1 ;; esac
done
case "$*" in
*"--jq .default_branch"*) printf '%s\\n' "${DEFAULT-main}" ;;
*"/compare/"*) printf '%s\\n' "${COMPARE:-}" ;;
*"--input"*) for last; do :; done; cp "$last" "$BODIES/$(basename "$last")" ;;
esac
exit 0
"""


def steps() -> dict[str, dict]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return {step.get("name", ""): step for step in workflow["jobs"]["tell"]["steps"]}


class Stubbed:
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        self.output = self.root / "output"
        self.output.touch()
        self.log = self.root / "gh.log"
        self.bodies = self.root / "bodies"
        self.bodies.mkdir()

    def run_step(self, name: str, **env: str) -> subprocess.CompletedProcess:
        base = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(self.root),
            "GITHUB_OUTPUT": str(self.output),
            "GH_LOG": str(self.log),
            "BODIES": str(self.bodies),
        }
        return subprocess.run(
            ["bash", "-c", steps()[name]["run"]],
            env={**base, **env},
            capture_output=True,
            text=True,
            check=False,
        )

    def what(self, **env: str) -> subprocess.CompletedProcess:
        asked = {"REPOS": "", "WORKFLOW": "", "EVENT": "", "INPUTS": "{}", "PAYLOAD": "{}"}
        return self.run_step("What is told, and to whom", **{**asked, **env})

    def outputs(self) -> dict[str, str]:
        return dict(line.split("=", 1) for line in self.output.read_text(encoding="utf-8").splitlines())


class Tell(Stubbed, unittest.TestCase):
    """What is told, and to whom."""

    def test_a_workflow_dispatch_carries_its_inputs(self):
        done = self.what(REPOS="sdk-ts\nsdk-php", WORKFLOW="contract-bump.yml", INPUTS='{"tag": "v1.2.3"}')
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(
            self.outputs(),
            {
                "repos": "sdk-ts sdk-php",
                "listed": "sdk-ts,sdk-php",
                "path": "actions/workflows/contract-bump.yml/dispatches",
                "dispatch": "true",
            },
        )
        body = json.loads((self.root / "body.json").read_text(encoding="utf-8"))
        self.assertEqual(body, {"inputs": {"tag": "v1.2.3"}})

    def test_a_repository_event_carries_its_payload(self):
        done = self.what(REPOS="spec", EVENT="tracker-moved", PAYLOAD='{"sha": "abc"}')
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.outputs()["path"], "dispatches")
        body = json.loads((self.root / "body.json").read_text(encoding="utf-8"))
        self.assertEqual(body, {"event_type": "tracker-moved", "client_payload": {"sha": "abc"}})

    def test_what_cannot_be_sent_is_refused_by_name(self):
        refusals = {
            "names no repository": {"WORKFLOW": "a.yml"},
            "is not a repository name": {"REPOS": "../other", "WORKFLOW": "a.yml"},
            "is not a repository name in": {"REPOS": "..", "WORKFLOW": "a.yml"},
            "exactly one of workflow and event": {"REPOS": "a", "WORKFLOW": "a.yml", "EVENT": "e"},
            "is not a workflow file name": {"REPOS": "a", "WORKFLOW": "a.sh"},
            "inputs is not JSON": {"REPOS": "a", "WORKFLOW": "a.yml", "INPUTS": "{"},
            "not a JSON object of strings": {"REPOS": "a", "WORKFLOW": "a.yml", "INPUTS": '{"n": 1}'},
            "is not a repository event type": {"REPOS": "a", "EVENT": "a b"},
            "payload is not a JSON object": {"REPOS": "a", "EVENT": "e", "PAYLOAD": "[]"},
        }
        for said, env in refusals.items():
            with self.subTest(said):
                done = self.what(**env)
                self.assertEqual(done.returncode, 1)
                self.assertIn(said, done.stdout)

    def test_every_repository_is_told_and_one_that_is_not_fails_the_run(self):
        (self.root / "body.json").write_text("{}", encoding="utf-8")
        env = {
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "REPOS": "a b c",
            "ENDPOINT": "dispatches",
            "DISPATCH": "false",
        }
        done = self.run_step("Tell each one", **env)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 3)

        self.log.unlink()
        done = self.run_step("Tell each one", REFUSED="b/", **env)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 3)
        self.assertIn("these were not told: b", done.stdout)

    def test_a_workflow_runs_on_each_targets_own_default_branch(self):
        (self.root / "body.json").write_text('{"inputs": {"ref": "evil"}}', encoding="utf-8")
        env = {
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "REPOS": "a",
            "ENDPOINT": "actions/workflows/x.yml/dispatches",
        }
        done = self.run_step("Tell each one", DISPATCH="true", DEFAULT="trunk", **env)
        self.assertEqual(done.returncode, 0, done.stdout)
        [sent] = [json.loads(one.read_text(encoding="utf-8")) for one in self.bodies.iterdir()]
        self.assertEqual(sent, {"inputs": {"ref": "evil"}, "ref": "trunk"})

    def test_a_target_whose_default_branch_cannot_be_read_is_not_told(self):
        (self.root / "body.json").write_text('{"inputs": {}}', encoding="utf-8")
        env = {
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "REPOS": "a",
            "ENDPOINT": "actions/workflows/x.yml/dispatches",
        }
        done = self.run_step("Tell each one", DISPATCH="true", DEFAULT="", **env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("could not read a's default branch", done.stdout)


class WhoMayTell(Stubbed, unittest.TestCase):
    """Only the caller's default branch, or a tag on a commit it holds, gets as far as the mint."""

    def authorised(self, **env: str) -> subprocess.CompletedProcess:
        base = {"GH_TOKEN": "t", "REPO": "lemonfiber/x", "SHA": "a" * 40, "DEFAULT": "main"}
        return self.run_step("Only the default branch, or a tag it holds, tells anyone", **{**base, **env})

    def test_the_default_branch_tells_for_a_push_a_dispatch_a_schedule_or_a_release(self):
        for event in ("push", "workflow_dispatch", "schedule", "release"):
            with self.subTest(event):
                self.assertEqual(self.authorised(EVENT=event, REF="refs/heads/main").returncode, 0)

    def test_a_pull_request_never_tells_whatever_its_ref(self):
        for event in ("pull_request", "pull_request_target", "issue_comment"):
            with self.subTest(event):
                done = self.authorised(EVENT=event, REF="refs/heads/main")
                self.assertEqual(done.returncode, 1)
                self.assertIn(f"never for {event}", done.stdout)

    def test_another_branch_never_tells(self):
        done = self.authorised(EVENT="workflow_dispatch", REF="refs/heads/feature")
        self.assertEqual(done.returncode, 1)
        self.assertIn("refs/heads/feature is not main", done.stdout)

    def test_a_tag_tells_only_where_the_default_branch_holds_its_commit(self):
        for status, code in (("identical", 0), ("behind", 0), ("ahead", 1), ("diverged", 1), ("", 1)):
            with self.subTest(status):
                self.assertEqual(
                    self.authorised(EVENT="push", REF="refs/tags/v1.2.3", COMPARE=status).returncode, code
                )

    def test_an_unreadable_default_branch_tells_nobody(self):
        done = self.authorised(EVENT="push", REF="refs/heads/main", DEFAULT="")
        self.assertEqual(done.returncode, 1)
        self.assertIn("could not be read", done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
