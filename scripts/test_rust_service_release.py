"""`rust-service-release.yml`'s settle step and what it hands on: a commit on main as
`main-<12 hex>`, or the tag a train cut at the version the crate and, where the repository
holds one, its plugin.toml declare."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import workflow_steps
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/rust-service-release.yml"
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")
SETTLE = "A commit on main, or a tag the train cuts on main at the version the crate and its manifest declare"


def step(job: str, named: str) -> str:
    return workflow_steps.step(WORKFLOW, job, named)


class Settle(unittest.TestCase):
    """A tag publishes where the crate, and a manifest beside it, declare its version."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        (self.root / "Cargo.toml").write_text('[package]\nname = "decline"\nversion = "0.18.0"\n')

    def settled(self, manifest: str | None = None, tag: str = "v0.18.0", event: str = "push",
                ref: str = "") -> tuple[int, dict, str]:
        if manifest is not None:
            (self.root / "plugin.toml").write_text(manifest)
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "c"], cwd=self.root, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.root)], cwd=self.root, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True,
                             text=True, check=True).stdout.strip()
        ref = ref or f"refs/tags/{tag}"
        kind = "tag" if ref.startswith("refs/tags/") else "branch"
        output = self.root / ".output"
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": event,
               "GITHUB_REF": ref, "GITHUB_SHA": sha, "REGISTRY": "ghcr.io/lemonfiber",
               "NAME": ref.rsplit("/", 1)[-1], "KIND": kind, "REPO": "lemonfiber-decline"}
        done = subprocess.run(["bash", "-c", step("settle", SETTLE)], cwd=self.root, env=env,
                              capture_output=True, text=True)
        said = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
        self.sha = sha
        return done.returncode, said, done.stdout + done.stderr

    def test_a_crate_alone_publishes_and_pins_no_manifest(self):
        code, said, _ = self.settled()
        self.assertEqual((code, said["image"], said["kind"], said["manifest"]),
                         (0, "ghcr.io/lemonfiber/decline", "tag", "false"))

    def test_a_manifest_at_the_tags_version_is_pinned(self):
        code, said, _ = self.settled('schema_version = 1\n[plugin]\nid = "decline"\nversion = "0.18.0"\n')
        self.assertEqual((code, said["manifest"]), (0, "true"))

    def test_a_manifest_at_another_version_publishes_nothing(self):
        code, said, printed = self.settled('schema_version = 1\n[plugin]\nid = "decline"\nversion = "0.17.0"\n')
        self.assertNotEqual(code, 0)
        self.assertEqual(said, {})
        self.assertIn("plugin.toml declares 0.17.0", printed)

    def test_a_tag_that_is_not_the_trains_publishes_nothing(self):
        for tag in ("v0.18.0-rc1", "release-1", "v0.18"):
            with self.subTest(tag=tag):
                shutil.rmtree(self.root / ".git")
                subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
                code, said, printed = self.settled(tag=tag)
                self.assertNotEqual(code, 0)
                self.assertEqual(said, {})
                self.assertIn("is not a tag the train cuts", printed)

    def test_a_commit_on_main_publishes_its_commit_image_and_pins_a_manifest_of_any_version(self):
        code, said, _ = self.settled('schema_version = 1\n[plugin]\nid = "decline"\nversion = "0.17.0"\n',
                                     ref="refs/heads/main")
        self.assertEqual(code, 0)
        self.assertEqual((said["tag"], said["kind"], said["manifest"]), (f"main-{self.sha[:12]}", "commit", "true"))

    def test_another_branch_or_another_event_publishes_nothing(self):
        for event, ref in (("push", "refs/heads/feature"), ("workflow_dispatch", "refs/heads/main"),
                           ("workflow_dispatch", "refs/tags/v0.18.0")):
            with self.subTest(event=event, ref=ref):
                shutil.rmtree(self.root / ".git")
                subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
                code, said, printed = self.settled(event=event, ref=ref)
                self.assertNotEqual(code, 0)
                self.assertEqual(said, {})
                self.assertIn("is published for a push to main or a pushed tag", printed)

    def test_a_repository_not_named_for_a_service_publishes_nothing(self):
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(self.root / ".output"), "GITHUB_EVENT_NAME": "push",
               "GITHUB_REF": "refs/heads/main", "GITHUB_SHA": "0" * 40, "REGISTRY": "ghcr.io/lemonfiber",
               "NAME": "main", "KIND": "branch", "REPO": "decline"}
        done = subprocess.run(["bash", "-c", step("settle", SETTLE)], cwd=self.root, env=env,
                              capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("is not named lemonfiber-<service>", done.stdout + done.stderr)


# A `docker` answering the publish step's calls, logging each: the tag is published
# already where `EXISTS` is set, and the index it names publishes both platforms.
DOCKER = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["DOCKER_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:1] == ["login"]:
    sys.stdin.read()
    sys.exit(0)
if args[:3] == ["buildx", "imagetools", "inspect"] and len(args) == 4:
    sys.exit(0 if os.environ.get("EXISTS") else 1)
if "--raw" in args:
    print(json.dumps({"manifests": [
        {"platform": {"os": "linux", "architecture": "amd64"}, "digest": "sha256:" + "1" * 64},
        {"platform": {"os": "linux", "architecture": "arm64"}, "digest": "sha256:" + "2" * 64}]}))
elif "{{json .Manifest}}" in args:
    print(json.dumps({"digest": "sha256:" + "f" * 64}))
elif "--format" in args:
    print("{}")
"""


class Published(workflow_steps.Scratch):
    """The index is created under its tag once, and a tag already published is kept."""

    def published(self, workflow: pathlib.Path, exists: bool) -> list[list[str]]:
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "docker").write_text(DOCKER)
        (bin_dir / "docker").chmod(0o755)
        (self.root / "digests").mkdir()
        for name in ("a" * 64, "b" * 64):
            (self.root / "digests" / name).touch()
        log = self.root / "docker.log"
        env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "DOCKER_LOG": str(log), "GH_TOKEN": "t", "ACTOR": "a",
               "IMAGE": "ghcr.io/lemonfiber/decline", "TAG": "main-0123456789ab",
               "GITHUB_OUTPUT": str(self.root / ".output"), "GITHUB_STEP_SUMMARY": str(self.root / ".summary")}
        if exists:
            env["EXISTS"] = "1"
        done = subprocess.run(["bash", "-c", workflow_steps.step(workflow, "publish", "Join the platforms under one index, tagged")],
                              cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return [json.loads(line) for line in log.read_text().splitlines()]

    def test_a_new_tag_is_created_and_a_published_one_never_moves(self):
        for workflow in (WORKFLOW, WORKFLOW.parent / "first-party-image.yml"):
            for exists in (False, True):
                with self.subTest(workflow=workflow.name, exists=exists):
                    shutil.rmtree(self.root, True)
                    self.root.mkdir()
                    created = [call for call in self.published(workflow, exists) if call[:3] == ["buildx", "imagetools", "create"]]
                    self.assertEqual(len(created), 0 if exists else 1)
                    self.assertIn("f" * 64, (self.root / ".output").read_text())


class HandedOn(unittest.TestCase):
    """Only a train tag is told to the stack; both kinds reach the manifest's pin, and
    the release App's key reaches no job that builds or publishes."""

    JOBS = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]

    def test_only_a_train_tag_tells_the_stack(self):
        self.assertEqual(self.JOBS["pin"]["if"], "needs.settle.outputs.kind == 'tag'")
        self.assertEqual(self.JOBS["manifest"]["if"], "needs.settle.outputs.manifest == 'true'")
        self.assertTrue(self.JOBS["manifest"]["uses"].endswith("manifest-pin.yml"))

    def test_no_job_that_builds_or_publishes_holds_the_release_key(self):
        for name in ("settle", "build", "publish"):
            with self.subTest(job=name):
                self.assertNotIn("RELEASE_APP_KEY", yaml.safe_dump(self.JOBS[name]))
                for one in self.JOBS[name].get("steps", []):
                    if one.get("uses", "").startswith("actions/checkout@"):
                        self.assertFalse(one["with"]["persist-credentials"])


if __name__ == "__main__":
    unittest.main()
