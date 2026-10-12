"""`rust-service-release.yml`'s settle step: the tag a train cut, at the version the crate
and, where the repository holds one, its plugin.toml declare."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/rust-service-release.yml"
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")
SETTLE = "The tag is one the train cuts, on main, at the version the crate and its manifest declare"


def step(job: str, named: str) -> str:
    """The `run` of one named step of the workflow."""
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][job]["steps"]
    return next(one for one in steps if one.get("name") == named)["run"]


class Settle(unittest.TestCase):
    """A tag publishes where the crate, and a manifest beside it, declare its version."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        (self.root / "Cargo.toml").write_text('[package]\nname = "decline"\nversion = "0.18.0"\n')

    def settled(self, manifest: str | None = None, tag: str = "v0.18.0") -> tuple[int, dict, str]:
        if manifest is not None:
            (self.root / "plugin.toml").write_text(manifest)
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "c"], cwd=self.root, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.root)], cwd=self.root, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True,
                             text=True, check=True).stdout.strip()
        output = self.root / ".output"
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": "push",
               "GITHUB_REF": f"refs/tags/{tag}", "GITHUB_SHA": sha, "REGISTRY": "ghcr.io/lemonfiber",
               "TAG": tag, "REPO": "lemonfiber-decline"}
        done = subprocess.run(["bash", "-c", step("settle", SETTLE)], cwd=self.root, env=env,
                              capture_output=True, text=True)
        said = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
        return done.returncode, said, done.stdout + done.stderr

    def test_a_crate_alone_publishes_and_pins_no_manifest(self):
        code, said, _ = self.settled()
        self.assertEqual((code, said["image"], said["manifest"]), (0, "ghcr.io/lemonfiber/decline", "false"))

    def test_a_manifest_at_the_tags_version_is_pinned(self):
        code, said, _ = self.settled('schema_version = 1\n[plugin]\nid = "decline"\nversion = "0.18.0"\n')
        self.assertEqual((code, said["manifest"]), (0, "true"))

    def test_a_manifest_at_another_version_publishes_nothing(self):
        code, said, printed = self.settled('schema_version = 1\n[plugin]\nid = "decline"\nversion = "0.17.0"\n')
        self.assertNotEqual(code, 0)
        self.assertEqual(said, {})
        self.assertIn("plugin.toml declares 0.17.0", printed)


if __name__ == "__main__":
    unittest.main()
