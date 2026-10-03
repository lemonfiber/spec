#!/usr/bin/env python3
"""The train's two steps and its plugin gate, shown in the workflows that run them —
ADR-0033 §4, OPS-R68, Q-R66.

`train_step.py` and `check_image_pins.py` are measured in `test_release_train.py`.
What decides whether a core is tagged over a stack pinning another tag's image is
how `execute-version` and `prerelease-version` wire them: which step a run is on,
that the pin check runs before the core is tagged and refuses a stack that does
not pin the tag, and that the tag loop, the declared-version check and the
pre-release record read the lists the step settled.

The plugin gate runs in a job of its own, ahead of the one that mints the release
token and holding no secret, on the host the core's release builds on. It settles
the core commit, builds the candidate from it, fetches the reader the registry pins
and proves every registered plugin through it with that build; the tagging job then
holds its checkout of the core at that commit. The action's steps run here too, with
`rustc` and `cargo` stubbed and the forge's URLs pointed at local remotes.

The step shell is read out of the committed YAML through a parser and run with
bash, so what runs here is the text that runs there. `docker` is replaced on a
PATH prefix by a stub answering for the registry; `git` is the real one, against
local remotes.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_train_workflows.py
"""

from __future__ import annotations

import json
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
PROVE = HERE.parent / ".github" / "actions" / "prove-plugins" / "action.yml"

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
CLONE = "Read the manifest and clone its repos"
HOLD = "Hold the core at the commit its plugins were proved with"
PLUGINS = "plugins"

DIGEST = "sha256:" + "a" * 64

#: Stands in for `docker buildx imagetools inspect <ref> --format ...`.
DOCKER = f"""#!/bin/sh
case " ${{DOCKER_MISSING:-}} " in *" $4 "*) echo "ERROR: $4: not found" >&2; exit 1 ;; esac
printf '%s' '{{"digest": "{DIGEST}"}}'
"""


def jobs(workflow: str) -> dict:
    return yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))["jobs"]


def steps(workflow: str) -> list[dict]:
    job, _ = LANES[workflow]
    return jobs(workflow)[job]["steps"]


def proving() -> list[dict]:
    return yaml.safe_load(PROVE.read_text(encoding="utf-8"))["runs"]["steps"]


def action_step(starts: str) -> dict:
    for one in proving():
        if one["name"].startswith(starts):
            return one
    raise AssertionError(f"no step starting {starts!r} in {PROVE.name}")


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
                self.assertLess(held, position(workflow, STEP))
                self.assertLess(held, position(workflow, TAG_LOOP))
                self.assertEqual(step(workflow, HOLD)["env"]["CORE"],
                                 "${{ needs.plugins.outputs.core }}")

    def test_the_candidate_is_built_where_the_release_builds_its_linux_archive(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertEqual(jobs(workflow)[PLUGINS]["runs-on"], "ubuntu-22.04")

    def test_the_commit_handed_on_is_the_one_settled(self):
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertEqual(jobs(workflow)[PLUGINS]["outputs"]["core"],
                                 "${{ steps.prove.outputs.core }}")
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
        self.remote("lemonfiber", {
            "crates/lemonfiber-manifest/src/lib.rs": "pub const SCHEMA_VERSION: u32 = 1;\n"})
        self.remote("lemonfiber", {"README.md": "moved on\n"})
        self.remote("plugin-komga", {
            "plugin.toml": 'schema_version = 1\n[plugin]\nid = "komga"\n',
            "targets.toml": 'lemonfiber = "0.1.0"\n',
            "proofs.json": '{"lemonfiber": "0.1.0", "proofs": []}\n',
            ".github/reader/reader.py": OWN,
        })
        self.remote("plugin-template", {".github/reader/reader.py": READER})
        self.pinned = self.git("rev-parse", "HEAD", cwd=self.root / "remotes/plugin-template.git")
        # A later commit the pin does not name, so fetching the head would be caught.
        self.remote("plugin-template", {".github/reader/reader.py": OWN})
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit=self.pinned), encoding="utf-8")

    def git(self, *args, cwd=None) -> str:
        done = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True, text=True, cwd=cwd or self.root)
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
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "GITHUB_OUTPUT": str(output), "OWNER": "test",
               "CARGO_ASKED": str(self.root / "cargo-asked"),
               # The forge's URLs, answered by the local remotes.
               "GIT_CONFIG_COUNT": "2",
               "GIT_CONFIG_KEY_0": f"url.{(self.root / 'remotes').as_uri()}/.insteadOf",
               "GIT_CONFIG_VALUE_0": "https://github.com/test/",
               "GIT_CONFIG_KEY_1": "protocol.file.allow",
               "GIT_CONFIG_VALUE_1": "always",
               **extra}
        done = subprocess.run(["bash", "-e", "-c", script], capture_output=True, text=True,
                              cwd=self.root, env=env, check=False)
        said = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
        return done, said

    def test_the_action_builds_the_head_and_proves_the_plugin_with_it(self):
        done, settled = self.run_shell(action_step("Settle")["run"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(settled["sha"], self.commits[-1])

        done, built = self.run_shell(action_step("Build")["run"], CORE=self.commits[0])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(built, {
            "build": "x86_64-unknown-linux-gnu",
            "binary": "checkouts/lemonfiber/target/x86_64-unknown-linux-gnu/dist/lemonfiber",
        })
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "checkouts/lemonfiber"),
                         self.commits[0])
        self.assertEqual((self.root / "cargo-asked").read_text(encoding="utf-8").split(),
                         ["build", "--locked", "--profile", "dist",
                          "--target", "x86_64-unknown-linux-gnu", "-p", "lemonfiber"])

        done, fetched = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(fetched, {"reader": "reader/.github/reader/reader.py"})
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "reader"), self.pinned)

        done, _ = self.run_shell(action_step("Prove")["run"], VERSION="0.2.0",
                                 BUILD=built["build"], BINARY=built["binary"],
                                 READER=fetched["reader"])
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
            action_step("Prove")["run"], VERSION="0.2.0", BUILD="x86_64-unknown-linux-gnu",
            BINARY="checkouts/lemonfiber/target/x86_64-unknown-linux-gnu/dist/lemonfiber",
            READER=fetched["reader"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("::warning::plugin-komga@main could not be cloned", done.stdout)
        self.assertIn("not a plugin that passed", done.stdout)

    def test_a_reader_pinned_to_a_commit_the_template_lacks_is_refused(self):
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit="b" * 40), encoding="utf-8")
        done, _ = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("the reader is", done.stdout)

    def test_a_registry_refusing_its_reader_pin_is_shown(self):
        (self.root / "70-operations/plugins.toml").write_text(
            REGISTRY.format(commit="main"), encoding="utf-8")
        done, _ = self.run_shell(action_step("Fetch the reader")["run"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("pins 'main', which is not a full commit", done.stdout)

    def test_a_registry_that_cannot_be_read_is_shown(self):
        (self.root / "70-operations/plugins.toml").write_text("[[plugin]\n", encoding="utf-8")
        done, _ = self.run_shell(action_step("Prove")["run"], VERSION="0.2.0", BUILD="x",
                                 BINARY="x", READER="x")
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
                    self.git("rev-parse", "HEAD", cwd=self.root / "checkouts/lemonfiber"),
                    self.commits[0])
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
    unittest.main(verbosity=1)
