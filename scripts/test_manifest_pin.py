"""`manifest-pin.yml`'s own steps: which rolling branch a pin goes on, and what it writes."""

from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import tomllib
import unittest

import workflow_steps
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/manifest-pin.yml"
IMAGE = "ghcr.io/lemonfiber/door"
DIGEST = "sha256:" + "a" * 64



def step(job: str, named: str) -> str:
    return workflow_steps.step(WORKFLOW, job, named)


class Branch(workflow_steps.Scratch):
    """A train tag's image goes on one rolling branch, and main's on the other."""

    def branch(self, kind: str) -> str:
        output = self.root / ".output"
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), "GITHUB_REF_TYPE": kind,
               **yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["env"]}
        subprocess.run(["bash", "-c", step("pin", "Which rolling branch the pin goes on")],
                       cwd=self.root, env=env, check=True)
        return output.read_text().strip()

    def test_a_tag_pins_on_the_tag_branch(self):
        self.assertEqual(self.branch("tag"), "branch=release/image-pin")

    def test_main_pins_on_the_commit_branch(self):
        self.assertEqual(self.branch("branch"), "branch=release/image-commit-pin")


# A `gh` answering the pin step's calls the way GitHub does, logging each, and a `base64`
# that writes one line on any platform, as GNU's `-w0` does.
GH = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
joined = " ".join(args)
if "/pulls" in joined:
    print("0")
elif joined.endswith("git/ref/heads/main --jq .object.sha"):
    print("f" * 40)
elif "PUT" in args:
    print("c" * 40)
elif "/contents/" in joined:
    print(open(os.environ["HELD"]).read())
"""
BASE64 = """#!/usr/bin/env python3
import base64, sys
sys.stdout.write(base64.b64encode(open(sys.argv[-1], "rb").read()).decode())
"""


class Pin(workflow_steps.Scratch):
    """The pin step moves every service running the image through `plugin_pin.py`, and
    commits the manifest only where one moved."""

    MANIFEST = f'''schema_version = 1

[[service]]
id     = "door"
image  = "{IMAGE}"
digest = "sha256:{"0" * 64}"
tag    = "main-000000000000"

[[service]]
id     = "other"
image  = "caddy"
digest = "sha256:{"1" * 64}"
tag    = "2.11.6"
'''

    def pinned(self, manifest: str) -> tuple[int, str, list[list[str]]]:
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name, body in (("gh", GH), ("base64", BASE64)):
            (bin_dir / name).write_text(body)
            (bin_dir / name).chmod(0o755)
        held = self.root / "held-answer.json"
        held.write_text(json.dumps({"content": base64.b64encode(manifest.encode()).decode(), "sha": "x"}))
        log, output = self.root / "gh.log", self.root / ".output"
        env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "GH_LOG": str(log), "HELD": str(held),
               "GITHUB_OUTPUT": str(output), "GITHUB_SHA": "e" * 40, "REPOSITORY": "lemonfiber/plugin-door",
               "IMAGE": IMAGE, "TAG": "v0.18.0", "DIGEST": DIGEST, "PIN_BRANCH": "release/image-pin",
               "DIRECTORY": ".", "BOT": "release[bot]", "TOOLING": str(WORKFLOW.parents[2]),
               **yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["env"]}
        done = subprocess.run(["bash", "-c", step("pin", "Put what this tag or commit published on its rolling branch")],
                              cwd=self.root, env=env, capture_output=True, text=True)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return done.returncode, done.stdout + done.stderr, calls

    @staticmethod
    def put(calls: list[list[str]]) -> str:
        """The manifest the step committed, or nothing where it committed none."""
        for call in calls:
            if "PUT" in call:
                content = next(arg for arg in call if arg.startswith("content="))
                return base64.b64decode(content.removeprefix("content=")).decode()
        return ""

    def test_the_running_service_moves_at_the_tag_without_its_v_and_the_other_does_not(self):
        code, said, calls = self.pinned(self.MANIFEST)
        self.assertEqual(code, 0, said)
        services = {one["id"]: one for one in tomllib.loads(self.put(calls))["service"]}
        self.assertEqual((services["door"]["digest"], services["door"]["tag"]), (DIGEST, "0.18.0"))
        self.assertEqual(services["other"]["tag"], "2.11.6")
        self.assertIn("head=" + "c" * 40, (self.root / ".output").read_text())

    def test_a_manifest_naming_no_service_of_the_image_commits_nothing(self):
        code, said, calls = self.pinned(self.MANIFEST.replace(IMAGE, "elsewhere"))
        self.assertEqual((code, self.put(calls)), (0, ""))
        self.assertIn("nothing to pin", said)

    def test_a_manifest_the_pin_cannot_move_commits_nothing_and_fails(self):
        code, said, calls = self.pinned(self.MANIFEST.replace('tag    = "main-000000000000"\n', ""))
        self.assertNotEqual(code, 0)
        self.assertEqual(self.put(calls), "")
        self.assertIn("does not declare `tag` once", said)


if __name__ == "__main__":
    unittest.main()
