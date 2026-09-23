#!/usr/bin/env python3
"""The fan-out's own shell, shown doing it — OPS-R48, Q-R66.

`test_fan_out_pins.py` covers the rewrite. The half that decides *what happens to
a repository* is shell inside `fan-out-pins.yml`: clone it, measure it, branch,
commit, push, open the pull request, and decide whether the run failed. None of
that is Python and none of it was exercised by anything.

This drives that step as CI drives it. The script is read out of the committed
YAML through a YAML parser, so what runs here is the literal text that runs
there — an edit to the workflow that breaks the loop fails this rather than
being found by a tag six weeks later. `gh` is replaced on a PATH prefix by a stub
that clones a fixture, answers whether a pull request already exists, and records
the ones it is asked to open. `git` is the real one, except for `push`, which is
intercepted the same way: the step is supposed to push to an addressed remote
rather than to `origin`, and a test that let it try would be testing the network.

The case worth the most is the last one. The step says every repository is
visited even after one of them fails, because stopping at the first would leave
the rest of the organisation red for a reason having nothing to do with them.
That is a claim about a loop, and a loop is exactly the thing that quietly stops
being true.

Stdlib unittest plus PyYAML (the parser is the point — a hand-rolled reader would
be testing a different string than CI runs).
Run:  python3 scripts/test_fan_out_workflow.py
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
WORKFLOW = HERE.parent / ".github" / "workflows" / "fan-out-pins.yml"
JOB = "fan-out-pins"
STEP = "Open the bump wherever one is owed"

#: Stands in for `gh`. Three subcommands, answered by what was asked:
#:
#: `repo clone`  — lays down a checkout seeded from GH_FIXTURE, unless the
#:                 repository is named in GH_CLONE_FAILS.
#: `pr list`     — prints GH_PR_EXISTS, which the step reads as a count.
#: `pr create`   — records the call and succeeds, unless named in GH_CREATE_FAILS.
GH_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "${GH_LOG}"

case "$1 $2" in
"repo clone")
  named=$3
  short=${named#*/}
  at=$4
  case " ${GH_CLONE_FAILS:-} " in *" $short "*) exit 1 ;; esac
  mkdir -p "$at"
  cp -R "${GH_FIXTURE}/." "$at/"
  git -C "$at" init -q -b main
  git -C "$at" config user.email t@example.com
  git -C "$at" config user.name T
  git -C "$at" add -A
  git -C "$at" commit -qm "as it stands"
  exit 0
  ;;
"pr list")
  printf '%s\\n' "${GH_PR_EXISTS:-0}"
  exit 0
  ;;
"pr create")
  prev=""
  for word in "$@"; do
    case "$prev" in --repo) short=${word#*/} ;; esac
    prev=$word
  done
  case " ${GH_CREATE_FAILS:-} " in *" ${short:-} "*) exit 1 ;; esac
  printf 'created %s\\n' "${short:-?}" >> "${GH_CREATED}"
  exit 0
  ;;
esac
exit 0
"""

#: Stands in for `git`, passing everything through to the real one except a
#: push. The step pushes to a URL it builds rather than to `origin`, so there is
#: no local remote a test could point at; intercepting is the only way to run the
#: step's own text without reaching the network.
GIT_STUB = """#!/bin/sh
set -eu
for word in "$@"; do
  if [ "$word" = "push" ]; then
    printf '%s\\n' "$*" >> "${GIT_PUSH_LOG}"
    if [ -n "${GIT_PUSH_FAILS:-}" ]; then
      case " ${GIT_PUSH_FAILS} " in *" any "*) exit 1 ;; esac
    fi
    exit 0
  fi
done
exec "${REAL_GIT}" "$@"
"""


def the_step() -> str:
    """The step's shell, read out of the committed workflow."""
    described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    for step in described["jobs"][JOB]["steps"]:
        if step.get("name") == STEP:
            return step["run"]

    raise AssertionError(f"no step named {STEP!r} in {WORKFLOW}")


def a_pin(workflow: str, sha: str) -> str:
    return (
        "jobs:\n  one:\n    uses: "
        f"lemonfiber/spec/.github/workflows/{workflow}@{sha} # v1.0.1\n"
    )


class TheLoop(unittest.TestCase):
    """What the step does to each repository it is given."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.spec = self.root / "spec"
        (self.spec / "scripts").mkdir(parents=True)
        for name in ("fan_out_pins.py", "workflow_pins.py"):
            shutil.copy(HERE / name, self.spec / "scripts" / name)

        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")

        self.first = self.commit("one", "dco.yml")
        self.settled = self.commit("one", "hygiene.yml")
        self.head = self.commit("two", "dco.yml")

        # Cut where CI cuts it. The step resolves `TAG` to a revision and the
        # script reads the revision from that tag, so a harness whose spec holds
        # no tags drives a run CI never has — and used to pass anyway, because
        # the script fell back to `HEAD` and `HEAD` happened to be right here.
        self.git("tag", "-a", "-m", "v1.0.9", "v1.0.9")

        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("gh", GH_STUB), ("git", GIT_STUB)):
            where = self.bin / name
            where.write_text(body, encoding="utf-8")
            where.chmod(0o755)

        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        (self.fixture / ".github" / "workflows").mkdir(parents=True)

        self.log = self.root / "gh.log"
        self.created = self.root / "created.log"
        self.pushes = self.root / "pushes.log"
        self.summary = self.root / "summary.md"
        for where in (self.log, self.created, self.pushes, self.summary):
            where.touch()

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.spec), *args], check=True, capture_output=True
        )

    def commit(self, said: str, workflow: str) -> str:
        where = self.spec / ".github" / "workflows" / workflow
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(said, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", workflow)
        got = subprocess.run(
            ["git", "-C", str(self.spec), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return got.stdout.strip()

    def pinning(self, text: str):
        (self.fixture / ".github" / "workflows" / "ci.yml").write_text(
            text, encoding="utf-8"
        )

    def run_step(self, named: str = "alpha", **extra) -> subprocess.CompletedProcess:
        where = shutil.which("git")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "REAL_GIT": where,
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "TAG": "v1.0.9",
            "COMMIT": self.head,
            "NAMED": named,
            "SPEC": str(self.spec),
            "GH_FIXTURE": str(self.fixture),
            "GH_LOG": str(self.log),
            "GH_CREATED": str(self.created),
            "GIT_PUSH_LOG": str(self.pushes),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            **extra,
        }

        return subprocess.run(
            ["bash", "-c", the_step()], capture_output=True, text=True, env=env
        )

    # --- what it does -----------------------------------------------------

    def test_a_stale_pin_gets_a_pull_request(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step()

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertIn("created alpha", self.created.read_text(encoding="utf-8"))
        self.assertIn("opened:  alpha", self.summary.read_text(encoding="utf-8"))

    def test_the_branch_it_pushes_carries_the_tag(self):
        self.pinning(a_pin("dco.yml", self.first))

        self.run_step()

        pushed = self.pushes.read_text(encoding="utf-8")
        self.assertIn("ci/take-the-shared-workflows-at-v1.0.9", pushed)
        # To an addressed remote, not `origin` — the clone holds no credential.
        self.assertIn("github.com/lemonfiber/alpha.git", pushed)
        self.assertNotIn(" origin ", pushed)

    def test_a_repository_with_nothing_stale_gets_nothing(self):
        # `hygiene.yml` has not moved since the pin, so there is nothing owed
        # and a pull request would be an empty one.
        self.pinning(a_pin("hygiene.yml", self.settled))

        ran = self.run_step()

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")
        self.assertIn("current: alpha", self.summary.read_text(encoding="utf-8"))

    def test_an_open_pull_request_for_this_tag_is_not_opened_twice(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_PR_EXISTS="1")

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")
        self.assertIn("already open here", ran.stdout)
        self.assertIn("current: alpha", self.summary.read_text(encoding="utf-8"))

    # --- what it refuses --------------------------------------------------

    def test_a_repository_that_could_not_be_cloned_fails_the_run(self):
        # Not silently skipped. A repository nobody could ask about is not a
        # repository that is current.
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_CLONE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("could not be cloned", ran.stdout)
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))
        self.assertIn("no bump was opened in: alpha", ran.stdout)

    def test_a_branch_that_would_not_push_fails_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GIT_PUSH_FAILS="any")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("would not take the branch", ran.stdout)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")

    def test_a_pull_request_that_would_not_open_fails_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_CREATE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("would not take the pull request", ran.stdout)
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))

    # --- the claim the loop makes about itself ----------------------------

    def test_one_repository_failing_does_not_cost_the_others_their_bump(self):
        # The step says so in its own comment, and this is the only thing that
        # holds it to it. A `set -e`, or a `break` added while tidying, would
        # leave the rest of the organisation red for a reason of somebody
        # else's — which is the state the fan-out exists to end.
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(named="alpha\nbeta\ngamma", GH_CLONE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)

        created = self.created.read_text(encoding="utf-8")
        self.assertIn("created beta", created)
        self.assertIn("created gamma", created)

        said = self.summary.read_text(encoding="utf-8")
        self.assertIn("opened:  beta gamma", said)
        self.assertIn("refused: alpha", said)


class TheStepIsTheOneThatRuns(unittest.TestCase):
    """Read from the committed YAML, so this cannot drift from CI."""

    def test_the_step_is_found_by_name_in_the_workflow(self):
        self.assertIn("gh pr create", the_step())

    def test_the_workflow_declares_the_environment_the_step_reads(self):
        # A variable the step reads and the workflow does not pass is an empty
        # string under `set -u`… except that the step sets `-u` and would fail
        # loudly. This catches the rename before the tag does.
        described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        step = next(
            one
            for one in described["jobs"][JOB]["steps"]
            if one.get("name") == STEP
        )

        for named in ("GH_TOKEN", "OWNER", "TAG", "COMMIT", "NAMED", "SPEC"):
            self.assertIn(named, step["env"])

    def test_the_token_asks_for_permission_to_write_a_workflow_file(self):
        # Every change this workflow makes is to a file under
        # `.github/workflows/`, and GitHub refuses that push from an app without
        # `workflows`, whatever else the token may do. Asked for by name so a
        # token that cannot do it fails at the mint — on 2026-09-22 one that was
        # not asked got as far as twelve rejected pushes, reported as twelve
        # repositories refusing a branch.
        described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        minted = next(
            one
            for one in described["jobs"][JOB]["steps"]
            if str(one.get("uses", "")).startswith("actions/create-github-app-token")
        )

        for asked in ("contents", "pull-requests", "workflows"):
            self.assertEqual(minted["with"][f"permission-{asked}"], "write")


if __name__ == "__main__":
    unittest.main(verbosity=2)
