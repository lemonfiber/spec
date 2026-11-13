#!/usr/bin/env python3
"""`adapter-release.yml`: an adapter's image published from main and from train tags,
nothing published from a commit changing nothing but a pin, and its pin moved through
`manifest-pin` on the adapter's own rolling branches — OPS-R90, OPS-R91.

Run:  python3 scripts/test_adapter_release.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import workflow_steps
import yaml

TOOLING = pathlib.Path(__file__).resolve().parent.parent
PATH = TOOLING / ".github/workflows/adapter-release.yml"
WORKFLOW = yaml.safe_load(PATH.read_text(encoding="utf-8"))
JOBS = WORKFLOW["jobs"]
SETTLE = "A tag the train cuts, on main, at the version the crate declares; or a commit on main"
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false")
CRATE = '[package]\nname = "jellyfin-adapter"\nversion = "0.18.0"\n'
MANIFEST = """schema_version = 1
[plugin]
id = "jellyfin"
version = "0.18.0"

[[service]]
id = "jellyfin-adapter"
image = "ghcr.io/lemonfiber/jellyfin-adapter"
speaks = ["media.serve@1"]
"""


class Called(unittest.TestCase):
    def test_it_is_called_with_the_release_apps_key_alone(self):
        called = WORKFLOW[True]["workflow_call"]
        self.assertEqual(set(called["secrets"]), {"RELEASE_APP_KEY"})
        self.assertNotIn("inputs", called)

    def test_only_a_push_in_the_organisation_publishes(self):
        self.assertEqual(
            JOBS["settle"]["if"], "github.event_name == 'push' && github.repository_owner == 'lemonfiber'"
        )
        for name in ("build", "publish", "manifest"):
            self.assertIn("settle", JOBS[name]["needs"])

    def test_only_what_settle_publishes_is_built(self):
        self.assertEqual(JOBS["build"]["if"], "needs.settle.outputs.publish == 'yes'")


class Pin(unittest.TestCase):
    def test_the_published_image_is_pinned_by_manifest_pin_on_the_adapters_branches(self):
        self.assertEqual(set(JOBS), {"settle", "build", "publish", "manifest"})
        self.assertEqual(JOBS["manifest"]["uses"], "./.github/workflows/manifest-pin.yml")
        self.assertEqual(JOBS["manifest"]["needs"], ["settle", "publish"])
        self.assertEqual(
            JOBS["manifest"]["with"],
            {
                "image": "${{ needs.settle.outputs.image }}",
                "tag": "${{ needs.settle.outputs.tag }}",
                "digest": "${{ needs.publish.outputs.digest }}",
                "pin": "adapter",
            },
        )

    def test_no_job_that_builds_or_publishes_holds_the_release_key(self):
        for name in ("settle", "build", "publish"):
            with self.subTest(job=name):
                self.assertNotIn("RELEASE_APP_KEY", yaml.safe_dump(JOBS[name]))

    def test_each_platform_gets_a_build_provenance_and_an_sbom_attestation(self):
        attested = [one.get("name", "") for one in JOBS["publish"]["steps"] if "attest@" in one.get("uses", "")]
        for platform in ("amd64", "arm64"):
            with self.subTest(platform=platform):
                self.assertIn(f"Attest the linux/{platform} image's build provenance", attested)
                self.assertIn(f"Attest the linux/{platform} image's SBOM", attested)

    def test_no_checkout_keeps_a_credential(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                if one.get("uses", "").startswith("actions/checkout@"):
                    self.assertIs(one["with"]["persist-credentials"], False)


class Settle(unittest.TestCase):
    """A commit on main publishes unless it changes nothing but a pin; a train tag
    publishes at the version the crate and the manifest declare."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        self.commit({"Cargo.toml": CRATE, "plugin.toml": MANIFEST})
        self.before = self.head()

    def head(self) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout.strip()

    def commit(self, files: dict[str, str]) -> None:
        for path, body in files.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(body)
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "c"], cwd=self.root, check=True)

    def settled(self, ref: str) -> tuple[int, dict, str]:
        output = self.root / ".output"
        env = {
            "PATH": os.environ["PATH"],
            "GITHUB_OUTPUT": str(output),
            "GITHUB_SHA": self.head(),
            "REGISTRY": "ghcr.io/lemonfiber",
            "KIND": "tag" if ref.startswith("refs/tags/") else "branch",
            "REF": ref,
            "NAME": ref.rsplit("/", 1)[-1],
            "BEFORE": self.before,
            "TOOLING": str(TOOLING),
        }
        done = subprocess.run(
            ["bash", "-c", workflow_steps.step(PATH, "settle", SETTLE)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        said = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
        return done.returncode, said, done.stdout + done.stderr

    def test_a_commit_changing_code_publishes_its_commit_image(self):
        self.commit({"src/main.rs": "fn main() {}"})
        code, said, printed = self.settled("refs/heads/main")
        self.assertEqual(code, 0, printed)
        self.assertEqual(
            (said["image"], said["tag"], said["publish"]),
            ("ghcr.io/lemonfiber/jellyfin-adapter", f"main-{self.head()[:12]}", "yes"),
        )

    def test_a_commit_changing_nothing_but_a_pin_publishes_nothing(self):
        self.commit(
            {
                "plugin.toml": MANIFEST + "# moved\n",
                "proofs.json": "{}",
                "recordings/jellyfin/a.json": "{}",
                "targets.toml": "",
            }
        )
        code, said, printed = self.settled("refs/heads/main")
        self.assertEqual((code, said["publish"]), (0, "no"), printed)
        self.assertIn("no image is published", printed)
        self.assertNotIn("publishing", printed)

    def test_a_train_tag_at_the_crates_version_publishes_it(self):
        subprocess.run(["git", "remote", "add", "origin", str(self.root)], cwd=self.root, check=True)
        code, said, printed = self.settled("refs/tags/v0.18.0")
        self.assertEqual(code, 0, printed)
        self.assertEqual((said["tag"], said["publish"]), ("v0.18.0", "yes"))

    def test_another_branch_publishes_nothing(self):
        code, said, printed = self.settled("refs/heads/feature")
        self.assertNotEqual(code, 0)
        self.assertEqual(said, {})
        self.assertIn("no other branch publishes", printed)


class Interpolation(unittest.TestCase):
    def test_no_script_interpolates_an_expression(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                self.assertNotIn("${{", one.get("run", ""), one.get("name"))


if __name__ == "__main__":
    unittest.main()
