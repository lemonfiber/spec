#!/usr/bin/env python3
"""The train's two steps, shown in the workflows that run them — ADR-0033 §4, Q-R66.

`train_step.py` and `check_image_pins.py` are measured in `test_release_train.py`.
What decides whether a core is tagged over a stack pinning another tag's image is
how `execute-version` and `prerelease-version` wire them: which step a run is on,
that the pin check runs before the core is tagged and refuses a stack that does
not pin the tag, and that the tag loop, the declared-version check and the
pre-release record read the lists the step settled.

The step shell is read out of the committed YAML through a parser and run with
bash, so what runs here is the text that runs there. `docker` is replaced on a
PATH prefix by a stub answering for the registry; `git` is the real one, against
local remotes.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_train_workflows.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import train_step
import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / ".github" / "workflows"

#: Each lane, the job it runs in, and the tag one of its runs cuts for 0.2.0.
LANES = {
    "execute-version.yml": ("execute", "v0.2.0"),
    "prerelease-version.yml": ("prerelease", "v0.2.0-pre.1"),
}

STEP = "Which step of the train this run is (ADR-0033 §4)"
PINS = "The embedded stack pins each image at this tag"
TAG_LOOP = "Tag the target repos"
DECLARED = "The repos declare"
RECORDS = ("Record it on the manifest (OPS-R65)", "Wait for the record to land on main (OPS-R62, OPS-R65)")
STREAMS_ONLY = f"steps.step.outputs.step == '{train_step.STREAMS}'"
IMAGES_ONLY = f"steps.step.outputs.step == '{train_step.IMAGES}'"
NOTICES = ("Images tagged", "Tagged")

DIGEST = "sha256:" + "a" * 64

#: Stands in for `docker buildx imagetools inspect <ref> --format ...`.
DOCKER = f"""#!/bin/sh
case " ${{DOCKER_MISSING:-}} " in *" $4 "*) echo "ERROR: $4: not found" >&2; exit 1 ;; esac
printf '%s' '{{"digest": "{DIGEST}"}}'
"""


def steps(workflow: str) -> list[dict]:
    job, _ = LANES[workflow]
    return yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))["jobs"][job]["steps"]


def step(workflow: str, starts: str) -> dict:
    for one in steps(workflow):
        if str(one.get("name", "")).startswith(starts):
            return one
    raise AssertionError(f"no step starting {starts!r} in {workflow}")


def position(workflow: str, starts: str) -> int:
    return steps(workflow).index(step(workflow, starts))


class TheWiring(unittest.TestCase):
    """What each lane reads, and in what order."""

    def test_the_step_is_settled_before_anything_reads_it(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertLess(position(workflow, STEP), position(workflow, PINS))
                self.assertLess(position(workflow, PINS), position(workflow, TAG_LOOP))

    def test_the_pin_check_runs_in_the_second_step_only(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertIn(STREAMS_ONLY, step(workflow, PINS)["if"])

    def test_what_is_tagged_and_what_declares_are_the_lists_the_step_wrote(self):
        """`repos.txt` is everything the version cuts, which neither step tags."""
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertIn("done < tagging.txt", step(workflow, TAG_LOOP)["run"])
                self.assertIn("done < declaring.txt", step(workflow, DECLARED)["run"])

    def test_each_step_ends_on_its_own_notice(self):
        """The first step says to run again; only the second says to publish."""
        for workflow in LANES:
            with self.subTest(workflow):
                first, second = (step(workflow, name)["if"] for name in NOTICES)
                self.assertIn(IMAGES_ONLY, first)
                self.assertIn(STREAMS_ONLY, second)

    def test_a_pre_release_is_recorded_in_the_run_that_tags_the_core(self):
        """Recorded in the first step, the second would refuse the tag as already cut."""
        for name in RECORDS:
            self.assertIn(STREAMS_ONLY, step("prerelease-version.yml", name)["if"])


class TheSteps(unittest.TestCase):
    """The lanes' own shell, run against a workspace laid out the way CI lays it out."""

    def fresh(self):
        """A new workspace, one per lane, so neither run reads what the other wrote."""
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "scripts").symlink_to(HERE)
        (self.root / "30-repos").mkdir()
        (self.root / "30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lemonfiber"\n\n'
            '[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n', encoding="utf-8")
        (self.root / "70-operations/versions").mkdir(parents=True)
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber", "lemonfiber-decline"]\n', encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "docker").write_text(DOCKER, encoding="utf-8")
        (self.bin / "docker").chmod(0o755)

    def git(self, *args):
        subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                       check=True, capture_output=True, cwd=self.root)

    def stream(self, name: str, tagged: str = ""):
        remote = f"remotes/{name}"
        self.git("init", "-q", "-b", "main", remote)
        self.git("-C", remote, "-c", "user.email=t@t", "-c", "user.name=t",
                 "commit", "-q", "--allow-empty", "-m", "as it stands")
        if tagged:
            self.git("-C", remote, "tag", tagged)
        self.git("clone", "-q", remote, f"checkouts/{name}")

    def stack(self, tag: str):
        where = self.root / "checkouts/lemonfiber/assets/media-stack"
        where.mkdir(parents=True)
        (where / "stack.toml").write_text(
            f'[[service]]\nid = "decline"\nimage = "ghcr.io/lemonfiber/decline"\n'
            f'tag = "{tag}"\ndigest = "{DIGEST}"\n', encoding="utf-8")

    def run_step(self, workflow: str, starts: str, **extra) -> subprocess.CompletedProcess:
        _, tag = LANES[workflow]
        output = self.root / "output"
        output.write_text("", encoding="utf-8")
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "VERSION": "0.2.0", "TAG": tag, "GITHUB_OUTPUT": str(output), **extra}
        return subprocess.run(["bash", "-e", "-c", step(workflow, starts)["run"]],
                              capture_output=True, text=True, cwd=self.root, env=env, check=False)

    def read(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def test_an_untagged_image_makes_the_run_tag_it_alone(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.fresh()
                self.stream("lemonfiber")
                self.stream("lemonfiber-decline")
                done = self.run_step(workflow, STEP)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(self.read("output"), "step=images\n")
                self.assertEqual(self.read("tagging.txt"), "lemonfiber-decline\n")

    def test_a_tagged_image_makes_the_run_tag_the_core(self):
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                self.stream("lemonfiber")
                self.stream("lemonfiber-decline", tagged=tag)
                done = self.run_step(workflow, STEP)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(self.read("output"), "step=streams\n")
                self.assertEqual(self.read("tagging.txt"), "lemonfiber\n")

    def test_the_pin_check_passes_a_stack_pinning_the_tag(self):
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                self.stack(tag)
                done = self.run_step(workflow, PINS)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn(f"decline is pinned at {tag}", done.stdout)

    def test_the_pin_check_refuses_a_stack_pinning_another_tag(self):
        """The defect it exists for: a core tagged over another tag's image."""
        for workflow in LANES:
            with self.subTest(workflow):
                self.fresh()
                self.stack("v0.1.0")
                done = self.run_step(workflow, PINS)
                self.assertEqual(done.returncode, 1)
                self.assertIn("pinned at tag 'v0.1.0'", done.stdout)

    def test_the_pin_check_refuses_an_image_the_tag_has_not_published(self):
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                self.stack(tag)
                done = self.run_step(workflow, PINS, DOCKER_MISSING=f"ghcr.io/lemonfiber/decline:{tag}")
                self.assertEqual(done.returncode, 1)
                self.assertIn("is not published", done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
