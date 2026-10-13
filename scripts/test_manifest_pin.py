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


def embedded(job: str, named: str) -> str:
    return workflow_steps.embedded(WORKFLOW, job, named)


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


class Pin(workflow_steps.Scratch):
    """The pin sets the digest and tag of every service running the image, and nothing else."""

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

    def pinned(self, manifest: str) -> tuple[int, str, str]:
        held = {"content": base64.b64encode(manifest.encode()).decode(), "sha": "x"}
        (self.root / "held.json").write_text(json.dumps(held))
        done = subprocess.run(["python3", "-I", "-c", embedded("pin", "Put what this tag or commit published on its rolling branch"),
                               IMAGE, DIGEST, "v0.18.0"], cwd=self.root, capture_output=True, text=True)
        written = (self.root / "plugin.toml").read_text() if (self.root / "plugin.toml").exists() else ""
        pinned = (self.root / "pinned").read_text() if (self.root / "pinned").exists() else None
        return done.returncode, pinned, written

    def test_the_running_service_moves_and_the_other_does_not(self):
        code, pinned, written = self.pinned(self.MANIFEST)
        self.assertEqual((code, pinned), (0, "yes"))
        services = {one["id"]: one for one in tomllib.loads(written)["service"]}
        self.assertEqual((services["door"]["digest"], services["door"]["tag"]), (DIGEST, "0.18.0"))
        self.assertEqual(services["other"]["tag"], "2.11.6")
        self.assertIn('digest = "' + DIGEST, written)

    def said(self, manifest: str) -> tuple[int, str]:
        held = {"content": base64.b64encode(manifest.encode()).decode(), "sha": "x"}
        (self.root / "held.json").write_text(json.dumps(held))
        done = subprocess.run(["python3", "-I", "-c", embedded("pin", "Put what this tag or commit published on its rolling branch"),
                               IMAGE, DIGEST, "v0.18.0"], cwd=self.root, capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_a_running_service_without_a_tag_to_move_is_refused(self):
        code, said = self.said(self.MANIFEST.replace('tag    = "main-000000000000"\n', ""))
        self.assertNotEqual(code, 0)
        self.assertIn("does not declare `tag` once", said)
        self.assertFalse((self.root / "plugin.toml").exists())

    def test_a_pin_the_manifest_does_not_read_back_is_refused(self):
        hidden = self.MANIFEST.replace(
            'digest = "sha256:' + "0" * 64 + '"',
            'why = """\ndigest = "not a field"\n"""\n"digest" = "sha256:' + "0" * 64 + '"', 1)
        code, said = self.said(hidden)
        self.assertNotEqual(code, 0)
        self.assertIn("does not run ghcr.io/lemonfiber/door at", said)
        self.assertFalse((self.root / "plugin.toml").exists())

    def test_a_running_service_written_so_the_pin_cannot_move_it_is_refused(self):
        quoted = self.MANIFEST.replace(f'image  = "{IMAGE}"', f"image  = '{IMAGE}'")
        code, _, written = self.pinned(quoted)
        self.assertNotEqual(code, 0)
        self.assertEqual(written, "")

    def test_a_manifest_naming_no_service_of_the_image_pins_nothing(self):
        code, pinned, written = self.pinned(self.MANIFEST.replace(IMAGE, "elsewhere"))
        self.assertEqual((code, pinned, written), (0, "", ""))



if __name__ == "__main__":
    unittest.main()
