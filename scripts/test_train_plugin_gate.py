#!/usr/bin/env python3
"""The train's plugin gate: wired before anything is tagged, and its steps proving
every registered plugin through the reader the registry pins with the candidate core.

The plugin gate runs in a job of its own, ahead of the one that mints the release
token and holding no secret, on the host the core's release builds on. It settles
the core commit, builds the candidate from it, fetches the reader the registry pins
and proves every registered plugin through it with that build; the tagging job then
holds its checkout of the core at that commit. The action's steps run here too, with
`rustc` and `cargo` stubbed and the forge's URLs pointed at local remotes.

Run:  python3 scripts/test_train_plugin_gate.py
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
from test_train_workflows import (
    CLONE,
    HERE,
    HOLD,
    LANES,
    PLUGINS,
    PROVE,
    SETTLES,
    TAG_LOOP,
    action_step,
    jobs,
    position,
    step,
)


class ThePluginGateWiring(unittest.TestCase):
    """Proved before anything is tagged, by a job holding nothing it could leak."""

    def test_the_tagging_job_waits_for_the_plugin_gate(self):
        for workflow, (job, _) in LANES.items():
            with self.subTest(workflow):
                self.assertEqual(jobs(workflow)[job]["needs"], PLUGINS)

    def test_the_plugin_gate_holds_no_secret_and_mints_no_token(self):
        """Building runs every dependency's build script; proving runs each
        plugin's own reader. Neither runs beside the release App token."""
        for workflow in LANES:
            with self.subTest(workflow):
                job = json.dumps(jobs(workflow)[PLUGINS])
                self.assertNotIn("secrets.", job)
                self.assertNotIn("create-github-app-token", job)
        action = json.dumps(yaml.safe_load(PROVE.read_text(encoding="utf-8")))
        for held in ("secrets.", "token", "GH_TOKEN"):
            self.assertNotIn(held, action.replace("Nothing here takes a token", ""))

    def test_the_gate_runs_in_the_plugin_job_and_nowhere_else(self):
        for workflow, (job, _) in LANES.items():
            with self.subTest(workflow):
                uses = [one.get("uses") for one in jobs(workflow)[PLUGINS]["steps"]]
                self.assertIn("./.github/actions/prove-plugins", uses)
                self.assertNotIn("check_plugins.py", json.dumps(jobs(workflow)[job]))

    def test_the_core_is_held_before_anything_reads_it(self):
        for workflow in LANES:
            with self.subTest(workflow):
                held = position(workflow, HOLD)
                self.assertLess(position(workflow, CLONE), held)
                self.assertLess(held, position(workflow, SETTLES[workflow]))
                self.assertLess(held, position(workflow, TAG_LOOP))
                self.assertEqual(step(workflow, HOLD)["env"]["CORE"], "${{ needs.plugins.outputs.core }}")

    def test_the_candidate_is_built_where_the_release_builds_its_linux_archive(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertEqual(jobs(workflow)[PLUGINS]["runs-on"], "ubuntu-22.04")

    def test_the_commit_handed_on_is_the_one_settled(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertEqual(
                    jobs(workflow)[PLUGINS]["outputs"]["core"], "${{ steps.prove.outputs.core }}"
                )
        outputs = yaml.safe_load(PROVE.read_text(encoding="utf-8"))["outputs"]
        self.assertEqual(outputs["core"]["value"], "${{ steps.core.outputs.sha }}")


#: Stands in for the pinned toolchain's `rustc -vV`.
RUSTC = """#!/bin/sh
printf 'rustc 1.0.0\nhost: x86_64-unknown-linux-gnu\n'
"""

#: Stands in for `cargo build`: says what it was asked, and leaves a binary where
#: cargo would.
CARGO = """#!/bin/sh
echo "$@" > "$CARGO_ASKED"
while [ $# -gt 0 ]; do [ "$1" = --target ] && target=$2; shift; done
mkdir -p "target/$target/dist"
printf 'built' > "target/$target/dist/lemonfiber"
chmod +x "target/$target/dist/lemonfiber"
"""

#: The template's reader, doing what the real one does with a release in its cache.
READER = """import json, pathlib, sys, tomllib
root = pathlib.Path(__file__).resolve().parents[2]
version = tomllib.loads((root / "targets.toml").read_text())["lemonfiber"]
if not list((root / ".lemonfiber" / version).glob("*/lemonfiber")):
    print("::error::no release is held")
    sys.exit(1)
proofs = [{"id": "answers", "kind": "proof", "outcome": "passed", "detail": ""}]
(root / "proofs.json").write_text(json.dumps({"lemonfiber": version, "proofs": proofs}))
"""

#: A plugin's own reader, which the train never runs.
OWN = """raise SystemExit("::error::the plugin's own reader ran")
"""

REGISTRY = """schema = 1

[reader]
repo = "plugin-template"
commit = "{commit}"
path = ".github/reader/reader.py"

[[plugin]]
id = "komga"
repo = "plugin-komga"
manifest = "plugin.toml"
targets = "targets.toml"
report = "proofs.json"
ref = "main"
"""


class ThePluginGateSteps(unittest.TestCase):
    """The action's own shell and the hold step, against local remotes."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "scripts").symlink_to(HERE)
        (self.root / "70-operations").mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("rustc", RUSTC), ("cargo", CARGO)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        self.commits: list[str] = []
        self.remote(
            "lemonfiber", {"crates/lemonfiber-manifest/src/lib.rs": "pub const SCHEMA_VERSION: u32 = 1;\n"}
        )
        self.remote("lemonfiber", {"README.md": "moved on\n"})
        self.remote(
            "plugin-komga",
            {
                "plugin.toml": 'schema_version = 1\n[plugin]\nid = "komga"\n',
                "targets.toml": 'lemonfiber = "0.1.0"\n',
                "proofs.json": '{"lemonfiber": "0.1.0", "proofs": []}\n',
                ".github/reader/reader.py": OWN,
            },
        )
        self.remote("plugin-template", {".github/reader/reader.py": READER})
        self.pinned = self.git("rev-parse", "HEAD", cwd=self.root / "remotes/plugin-template.git")
        # A later commit the pin does not name, so fetching the head would be caught.
        self.remote("plugin-template", {".github/reader/reader.py": OWN})
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit=self.pinned), encoding="utf-8"
        )

    def git(self, *args, cwd=None) -> str:
        done = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd or self.root,
        )
        return done.stdout.strip()

    def remote(self, name: str, files: dict[str, str]):
        # Named as the forge's URL names it, `.git` and all.
        where = self.root / "remotes" / f"{name}.git"
        if not where.exists():
            self.git("init", "-q", "-b", "main", str(where))
        for path, body in files.items():
            (where / path).parent.mkdir(parents=True, exist_ok=True)
            (where / path).write_text(body, encoding="utf-8")
        self.git("add", "-A", cwd=where)
        self.git("commit", "-q", "-m", "as it stands", cwd=where)
        if name == "lemonfiber":
            self.commits.append(self.git("rev-parse", "HEAD", cwd=where))

    def run_shell(self, script: str, **extra) -> tuple[subprocess.CompletedProcess, dict[str, str]]:
        output = self.root / "output"
        output.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "OWNER": "test",
            "CARGO_ASKED": str(self.root / "cargo-asked"),
            # The forge's URLs, answered by the local remotes.
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": f"url.{(self.root / 'remotes').as_uri()}/.insteadOf",
            "GIT_CONFIG_VALUE_0": "https://github.com/test/",
            "GIT_CONFIG_KEY_1": "protocol.file.allow",
            "GIT_CONFIG_VALUE_1": "always",
            **extra,
        }
        done = subprocess.run(
            ["bash", "-e", "-c", script], capture_output=True, text=True, cwd=self.root, env=env, check=False
        )
        said = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
        return done, said

    def test_the_action_builds_the_head_and_proves_the_plugin_with_it(self):
        done, settled = self.run_shell(action_step("Settle")["run"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(settled["sha"], self.commits[-1])

        done, built = self.run_shell(action_step("Build")["run"], CORE=self.commits[0])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(
            built,
            {
                "build": "x86_64-unknown-linux-gnu",
                "binary": "checkouts/lemonfiber/target/x86_64-unknown-linux-gnu/dist/lemonfiber",
            },
        )
        self.assertEqual(
            self.git("rev-parse", "HEAD", cwd=self.root / "checkouts/lemonfiber"), self.commits[0]
        )
        self.assertEqual(
            (self.root / "cargo-asked").read_text(encoding="utf-8").split(),
            [
                "build",
                "--locked",
                "--profile",
                "dist",
                "--target",
                "x86_64-unknown-linux-gnu",
                "-p",
                "lemonfiber",
            ],
        )

        done, fetched = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(fetched, {"reader": "reader/.github/reader/reader.py"})
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "reader"), self.pinned)

        done, _ = self.run_shell(
            action_step("Prove")["run"],
            VERSION="0.2.0",
            BUILD=built["build"],
            BINARY=built["binary"],
            READER=fetched["reader"],
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("the plugin's own reader ran", done.stdout)
        self.assertIn("plugins ok: 1 of 1 ride 0.2.0, all proved with the candidate.", done.stdout)
        held = self.root / "plugins/plugin-komga/.lemonfiber/0.2.0/x86_64-unknown-linux-gnu/lemonfiber"
        self.assertEqual(held.read_text(encoding="utf-8"), "built")

    def test_a_plugin_that_cannot_be_cloned_is_named_by_the_gate(self):
        shutil.rmtree(self.root / "remotes/plugin-komga.git")
        done, _ = self.run_shell(action_step("Build")["run"], CORE=self.commits[0])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        done, fetched = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        done, _ = self.run_shell(
            action_step("Prove")["run"],
            VERSION="0.2.0",
            BUILD="x86_64-unknown-linux-gnu",
            BINARY="checkouts/lemonfiber/target/x86_64-unknown-linux-gnu/dist/lemonfiber",
            READER=fetched["reader"],
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("::warning::plugin-komga@main could not be cloned", done.stdout)
        self.assertIn("not a plugin that passed", done.stdout)

    def test_a_reader_pinned_to_a_commit_the_template_lacks_is_refused(self):
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit="b" * 40), encoding="utf-8"
        )
        done, _ = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("the reader is", done.stdout)

    def test_a_registry_refusing_its_reader_pin_is_shown(self):
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit="main"), encoding="utf-8"
        )
        done, _ = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("pins 'main', which is not a full commit", done.stdout)

    def test_a_registry_that_cannot_be_read_is_shown(self):
        (self.root / "70-operations/plugins.toml").write_text("[[plugin]\n", encoding="utf-8")
        done, _ = self.run_shell(
            action_step("Prove")["run"], VERSION="0.2.0", BUILD="x", BINARY="x", READER="x"
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("cannot be read", done.stdout)

    def test_the_tagging_job_holds_the_core_at_the_commit_proved(self):
        for workflow in LANES:
            with self.subTest(workflow):
                shutil.rmtree(self.root / "checkouts", ignore_errors=True)
                self.git("clone", "-q", str(self.root / "remotes/lemonfiber.git"), "checkouts/lemonfiber")
                done, _ = self.run_shell(step(workflow, HOLD)["run"], CORE=self.commits[0])
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(
                    self.git("rev-parse", "HEAD", cwd=self.root / "checkouts/lemonfiber"), self.commits[0]
                )
                self.assertIn(f"lemonfiber held at {self.commits[0][:8]}", done.stdout)

    def test_the_tagging_job_refuses_without_a_settled_commit(self):
        for workflow in LANES:
            with self.subTest(workflow):
                done, _ = self.run_shell(step(workflow, HOLD)["run"], CORE="")
                self.assertEqual(done.returncode, 1)
                self.assertIn("::error::the plugin gate settled no core commit: ''", done.stdout)

    def test_a_core_head_that_cannot_be_read_is_refused(self):
        shutil.rmtree(self.root / "remotes/lemonfiber.git")
        done, _ = self.run_shell(action_step("Settle")["run"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("::error::could not read the core's head commit: ''", done.stdout)


if __name__ == "__main__":
    unittest.main()
