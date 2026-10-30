#!/usr/bin/env python3
"""The train's two steps, shown in the workflows that run them — ADR-0033 §4, OPS-R68,
Q-R66. Its plugin gate is shown in `test_train_plugin_gate.py`.

`check_image_pins.py` and `check_bundle_pins.py` are measured in `test_release_images.py`
and `train_step.py` in `test_train_step.py`. What decides whether a core is tagged over a bundle pinning
another tag's image, or another release of a plugin, is how
`execute-version` and `prerelease-version` wire them: which step a release run is on,
that both pin checks run before the core is tagged and refuse what does not pin the tag,
that a pre-release is one run tagging no first-party plugin and reading no pin, and that
the tag loop, the declared-version check and the pre-release record read the lists
`train_step.py` wrote.

A run stopped part-way is finished by running it again. The tag loop passes over a
repository already carrying the tag at the commit it would tag and refuses one
carrying it elsewhere; a pre-release already recorded on main is not recorded
again, but held to the pins this run embeds; and the record's branch is rebuilt
from main, so a branch and pull request an earlier run left do not refuse it.

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
from types import MappingProxyType

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
#: The pre-release's one run, which tags no first-party plugin.
PRE_STEP = "What the pre-release tags (OPS-R86)"
#: The step in each lane that settles what it tags.
SETTLES = {"execute-version.yml": STEP, "prerelease-version.yml": PRE_STEP}
PINS = "The embedded bundle pins each image at this tag"
COMPAT = "Cross-stream compatibility (OPS-R35"
BUNDLE = "The embedded bundle pins each first-party plugin at this tag"
#: The two gates a release and a pre-release both pass before anything is tagged.
GATES = ("Gate — every goal satisfied", "Gate — no requirement it locks is unbuilt")
TAG_LOOP = "Tag the target repos"
DECLARED = "The repos declare"
RECORDS = ("Record it on the manifest (OPS-R65)", "Wait for the record to land on main (OPS-R62, OPS-R65)")
STREAMS_ONLY = f"steps.step.outputs.step == '{train_step.STREAMS}'"
IMAGES_ONLY = f"steps.step.outputs.step == '{train_step.IMAGES}'"
#: The release's notice for the first step, then for the second.
NOTICES = ("Images and plugins tagged", "Tagged")
CLONE = "Read the manifest and clone its repos"
HOLD = "Hold the core at the commit its plugins were proved with"
PLUGINS = "plugins"
RECORDED = "A record already on main names this build"
TRANSITION = HERE.parent / ".github" / "actions" / "manifest-transition" / "action.yml"
REBUILT = "Open the record on a branch rebuilt from main"
SHA = "b" * 40

DIGEST = "sha256:" + "a" * 64

#: What lets the core's checkout take a submodule from a local remote, and the owner it is asked for.
ALLOWED = MappingProxyType(
    {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
        "OWNER": "o",
    }
)

#: Stands in for `docker buildx imagetools inspect <ref> --format ...`.
DOCKER = f"""#!/bin/sh
case " ${{DOCKER_MISSING:-}} " in *" $4 "*) echo "ERROR: $4: not found" >&2; exit 1 ;; esac
printf '%s' '{{"digest": "{DIGEST}"}}'
"""

#: Stands in for `gh`. Logs every call; `GH_HELD` lists `repo=sha` for each
#: repository already carrying the tag, `GH_REFS_FAIL` makes the tag lookup itself
#: fail, and `GH_BRANCH_LEFT` says an earlier run left its record branch behind.
#: The lookup answers as `matching-refs` filtered to the exact tag does: the commit
#: where the tag is held, and nothing at all where it is not.
GH = f"""#!/bin/sh
printf '%s\\n' "$*" >> "$GH_LOG"
case "$*" in
  "api repos/"*"/git/matching-refs/tags/"*)
    [ -z "${{GH_REFS_FAIL:-}}" ] || {{ echo "gh: Server Error (HTTP 502)" >&2; exit 1; }}
    repo=$(printf '%s' "$2" | cut -d/ -f3)
    for pair in ${{GH_HELD:-}}; do
      case "$pair" in "$repo="*) printf '%s\\n' "${{pair#*=}}"; exit 0 ;; esac
    done
    exit 0 ;;
  "api repos/"*"/git/ref/heads/main "*) echo "{SHA}" ;;
  "api repos/"*"/git/ref/heads/"*) [ -n "${{GH_BRANCH_LEFT:-}}" ] || exit 1 ;;
  "api repos/"*"/compare/main..."*) echo "${{GH_OTHERS:-0}}" ;;
  "pr create "*) echo "https://github.com/o/spec/pull/1" ;;
esac
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
        self.assertLess(position("execute-version.yml", STEP), position("execute-version.yml", PINS))
        self.assertLess(position("execute-version.yml", PINS), position("execute-version.yml", TAG_LOOP))
        self.assertLess(
            position("prerelease-version.yml", PRE_STEP), position("prerelease-version.yml", TAG_LOOP)
        )

    def test_the_pin_checks_run_in_the_release_s_second_step_only(self):
        for name in (PINS, BUNDLE):
            self.assertIn(STREAMS_ONLY, step("execute-version.yml", name)["if"])

    def test_a_release_refuses_on_the_bundle_before_anything_is_tagged(self):
        self.assertLess(position("execute-version.yml", STEP), position("execute-version.yml", BUNDLE))
        self.assertLess(position("execute-version.yml", BUNDLE), position("execute-version.yml", TAG_LOOP))

    def test_a_pre_release_reads_no_bundle_or_image_pin(self):
        """A pre-release is what the plugins are built against, so its bundle may pin them by
        revision alone (OPS-R86), and nothing here asks otherwise."""
        self.assertFalse(
            [
                one
                for one in steps("prerelease-version.yml")
                if str(one.get("name", "")).startswith((BUNDLE, PINS))
                or "check_bundle_pins.py" in str(one.get("run", ""))
                or "check_image_pins.py" in str(one.get("run", ""))
            ]
        )

    def test_a_pre_release_is_one_run(self):
        """It tags no first-party plugin, so nothing it does waits on a step."""
        self.assertFalse(
            [one["name"] for one in steps("prerelease-version.yml") if "steps.step.outputs" in str(one)]
        )

    def test_a_pre_release_passes_the_gates_a_release_passes(self):
        """The same goal gate and no-stub gate, refusing alike, before anything is recorded or
        tagged (OPS-R66, OPS-R70)."""
        for name in GATES:
            with self.subTest(name):
                ours, theirs = step("prerelease-version.yml", name), step("execute-version.yml", name)
                self.assertEqual(ours["run"], theirs["run"])
                self.assertNotIn("continue-on-error", ours)
                self.assertNotIn("if", ours)
                self.assertLess(
                    position("prerelease-version.yml", PRE_STEP), position("prerelease-version.yml", name)
                )
                for after in (RECORDS[0], TAG_LOOP):
                    self.assertLess(
                        position("prerelease-version.yml", name), position("prerelease-version.yml", after)
                    )

    def test_what_is_tagged_and_what_declares_are_the_lists_the_step_wrote(self):
        """`repos.txt` is everything the version cuts, which neither step tags."""
        for workflow in LANES:
            with self.subTest(workflow):
                self.assertIn("done < tagging.txt", step(workflow, TAG_LOOP)["run"])
                self.assertIn("done < declaring.txt", step(workflow, DECLARED)["run"])

    def test_each_release_step_ends_on_its_own_notice(self):
        """The first step says to run again; only the second says to publish."""
        first, second = (step("execute-version.yml", name)["if"] for name in NOTICES)
        self.assertIn(IMAGES_ONLY, first)
        self.assertIn(STREAMS_ONLY, second)

    def test_a_tag_already_recorded_is_not_recorded_again(self):
        """A re-run after the record reached main goes straight to the check and the tag."""
        for name in RECORDS:
            self.assertIn("steps.read.outputs.recorded != 'true'", step("prerelease-version.yml", name)["if"])
        self.assertEqual(
            step("prerelease-version.yml", RECORDED)["if"], "${{ steps.read.outputs.recorded == 'true' }}"
        )
        for before in ("Cross-stream compatibility", "Read the pins these artefacts will carry"):
            self.assertLess(
                position("prerelease-version.yml", before), position("prerelease-version.yml", RECORDED)
            )
        self.assertLess(
            position("prerelease-version.yml", RECORDED), position("prerelease-version.yml", TAG_LOOP)
        )


class TheSteps(unittest.TestCase):
    """The lanes' own shell, run against a workspace laid out the way CI lays it out."""

    def fresh(self):
        """A new workspace, one per lane, so neither run reads what the other wrote."""
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "scripts").symlink_to(HERE)
        (self.root / "30-repos").mkdir()
        (self.root / "30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lemonfiber"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n',
            encoding="utf-8",
        )
        (self.root / "70-operations/versions").mkdir(parents=True)
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber", "lemonfiber-decline"]\n', encoding="utf-8"
        )
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "docker").write_text(DOCKER, encoding="utf-8")
        (self.bin / "docker").chmod(0o755)

    def git(self, *args):
        subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
            check=True,
            capture_output=True,
            cwd=self.root,
        )

    def stream(self, name: str, tagged: str = ""):
        remote = f"remotes/{name}"
        self.git("init", "-q", "-b", "main", remote)
        self.git(
            "-C",
            remote,
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "as it stands",
        )
        if tagged:
            self.git("-C", remote, "tag", tagged)
        self.git("clone", "-q", remote, f"checkouts/{name}")

    def embed(self, catalogue: str):
        """The core's checkout embedding the catalogue at `catalogue`, not yet checked out."""
        self.git("-C", catalogue, "add", "-A")
        self.git("-C", catalogue, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "bundle")
        self.git(
            "-C",
            "checkouts/lemonfiber",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-q",
            str(self.root / catalogue),
            "assets/plugins",
        )
        self.git(
            "-C",
            "checkouts/lemonfiber",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "embed",
        )
        self.git("-C", "checkouts/lemonfiber", "submodule", "deinit", "-q", "--all")

    def bundled(self, tag: str):
        """The core's checkout embedding a catalogue whose bundle pins decline, its copy
        running the image at `tag`."""
        self.stream("lemonfiber")
        catalogue = "remotes/lemonfiber-plugins"
        self.git("init", "-q", "-b", "main", catalogue)
        (self.root / catalogue / "bundle/plugins/decline").mkdir(parents=True)
        (self.root / catalogue / "bundle/bundle.toml").write_text(
            'schema = 2\n\n[[plugin]]\nid = "decline"\norigin = "https://github.com/o/lemonfiber-decline"\n',
            encoding="utf-8",
        )
        (self.root / catalogue / "bundle/plugins/decline/plugin.toml").write_text(
            f'[[service]]\nid = "decline"\nimage = "ghcr.io/lemonfiber/decline"\n'
            f'tag = "{tag.removeprefix("v")}"\ndigest = "{DIGEST}"\n',
            encoding="utf-8",
        )
        self.embed(catalogue)

    def run_step(self, workflow: str, starts: str, **extra) -> subprocess.CompletedProcess:
        _, tag = LANES[workflow]
        output = self.root / "output"
        output.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "VERSION": "0.2.0",
            "TAG": tag,
            "GITHUB_OUTPUT": str(output),
            **extra,
        }
        return subprocess.run(
            ["bash", "-e", "-c", step(workflow, starts)["run"]],
            capture_output=True,
            text=True,
            cwd=self.root,
            env=env,
            check=False,
        )

    def read(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def test_an_untagged_image_makes_the_release_tag_it_alone(self):
        self.fresh()
        self.stream("lemonfiber")
        self.stream("lemonfiber-decline")
        done = self.run_step("execute-version.yml", STEP)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.read("output"), "step=images\n")
        self.assertEqual(self.read("tagging.txt"), "lemonfiber-decline\n")

    def test_a_tagged_image_makes_the_release_tag_the_core(self):
        self.fresh()
        self.stream("lemonfiber")
        self.stream("lemonfiber-decline", tagged="v0.2.0")
        done = self.run_step("execute-version.yml", STEP)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.read("output"), "step=streams\n")
        self.assertEqual(self.read("tagging.txt"), "lemonfiber\n")

    def test_the_pin_check_passes_a_bundle_pinning_the_tag(self):
        self.fresh()
        self.bundled("v0.2.0")
        done = self.run_step("execute-version.yml", PINS, **ALLOWED)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("decline is pinned at v0.2.0", done.stdout)

    def test_the_pin_check_refuses_a_bundle_pinning_another_tag(self):
        """The defect it exists for: a core tagged over another tag's image."""
        self.fresh()
        self.bundled("v0.1.0")
        done = self.run_step("execute-version.yml", PINS, **ALLOWED)
        self.assertEqual(done.returncode, 1)
        self.assertIn("pinned at tag '0.1.0'", done.stdout)

    def test_the_pin_check_refuses_an_image_the_tag_has_not_published(self):
        self.fresh()
        self.bundled("v0.2.0")
        done = self.run_step(
            "execute-version.yml", PINS, DOCKER_MISSING="ghcr.io/lemonfiber/decline:v0.2.0", **ALLOWED
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("is not published", done.stdout)

    def test_compatibility_is_read_off_the_bundle_the_core_embeds(self):
        for workflow, (_, tag) in LANES.items():
            for reads, code in (("[1, 2]", 0), ("[1]", 1)):
                with self.subTest(workflow=workflow, reads=reads):
                    self.fresh()
                    self.bundled(tag)
                    reader = self.root / "checkouts/lemonfiber/crates/lemonfiber-bundle/src/lib.rs"
                    reader.parent.mkdir(parents=True)
                    reader.write_text(f"pub const SCHEMAS: [u32; 2] = {reads};\n", encoding="utf-8")
                    done = self.run_step(workflow, COMPAT, **ALLOWED)
                    self.assertEqual(done.returncode, code, done.stdout + done.stderr)
                    self.assertIn("the embedded bundle is schema 2", done.stdout)

    def test_a_pre_release_tags_no_plugin_repository(self):
        """The plugin, an image repository included, is built against the core's pre-release
        and tagged at the version by the release (OPS-R86)."""
        for held in ("", "v0.2.0-pre.1"):
            with self.subTest(image_tagged=bool(held)):
                self.fresh()
                (self.root / "30-repos/repos.toml").write_text(
                    '[[repo]]\nname = "lemonfiber"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n\n'
                    '[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
                    encoding="utf-8",
                )
                (self.root / "70-operations/versions/0.2.0.toml").write_text(
                    'version = "0.2.0"\nrepos = ["lemonfiber", "lemonfiber-decline", "plugin-jellyfin"]\n',
                    encoding="utf-8",
                )
                for name in ("lemonfiber", "plugin-jellyfin"):
                    self.stream(name)
                self.stream("lemonfiber-decline", tagged=held)
                done = self.run_step("prerelease-version.yml", PRE_STEP)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(
                    (self.read("tagging.txt"), self.read("declaring.txt")), ("lemonfiber\n", "lemonfiber\n")
                )

    def test_a_release_tags_each_plugin_repository_in_its_first_step(self):
        self.fresh()
        (self.root / "30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lemonfiber"\n\n[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
            encoding="utf-8",
        )
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber", "plugin-jellyfin"]\n', encoding="utf-8"
        )
        for name in ("lemonfiber", "plugin-jellyfin"):
            self.stream(name)
        done = self.run_step("execute-version.yml", STEP)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            (self.read("output"), self.read("tagging.txt")), ("step=images\n", "plugin-jellyfin\n")
        )

    def head(self, at: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root / at), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def catalogue(self, release: str):
        """The core's checkout embedding a catalogue whose bundle pins jellyfin at `release`,
        at a revision whose `targets.toml` names the core commit before the embedding."""
        (self.root / "30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lemonfiber"\n\n[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
            encoding="utf-8",
        )
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber", "plugin-jellyfin"]\n', encoding="utf-8"
        )
        self.stream("lemonfiber")
        plugin = "remotes/plugin-jellyfin"
        self.git("init", "-q", "-b", "main", plugin)
        (self.root / plugin / "targets.toml").write_text(
            f'commit = "{self.head("checkouts/lemonfiber")}"\n', encoding="utf-8"
        )
        self.git("-C", plugin, "add", "-A")
        self.git("-C", plugin, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "targets")
        catalogue = "remotes/lemonfiber-plugins"
        self.git("init", "-q", "-b", "main", catalogue)
        (self.root / catalogue / "bundle").mkdir()
        (self.root / catalogue / "bundle/bundle.toml").write_text(
            'schema = 1\n\n[[plugin]]\nid = "jellyfin"\n'
            f'origin = "https://github.com/o/plugin-jellyfin"\nrelease = "{release}"\n'
            f'revision = "{self.head(plugin)}"\n',
            encoding="utf-8",
        )
        # The pinned origin is on the forge; here it is a repository beside the core.
        self.forge = {
            **ALLOWED,
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_1": f"url.{self.root}/remotes/.insteadOf",
            "GIT_CONFIG_VALUE_1": "https://github.com/o/",
        }
        self.embed(catalogue)

    def test_the_bundle_check_passes_a_version_cutting_no_plugin(self):
        self.fresh()
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber"]\n', encoding="utf-8"
        )
        done = self.run_step("execute-version.yml", BUNDLE, OWNER="o")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("cuts no first-party plugin", done.stdout)

    def test_the_bundle_check_reads_the_catalogue_the_core_embeds(self):
        self.fresh()
        self.catalogue("0.2.0")
        done = self.run_step("execute-version.yml", BUNDLE, **self.forge)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("jellyfin is pinned at 0.2.0", done.stdout)

    def test_a_release_refuses_a_bundle_pinning_another_release(self):
        """The defect it exists for: a core tagged over a bundle pinning another release."""
        self.fresh()
        self.catalogue("0.1.0")
        done = self.run_step("execute-version.yml", BUNDLE, **self.forge)
        self.assertEqual(done.returncode, 1)
        self.assertIn("pinned at release '0.1.0'", done.stdout)

    def stub_gate(self, answer: int, says: str = ""):
        """The workspace's scripts with `gate.py` answering `answer`, 0 for every goal met and
        1 for one unmet, after printing `says`, so the gate step's own shell is what is under
        test."""
        self.fresh()
        (self.root / "scripts").unlink()
        (self.root / "scripts").mkdir()
        for script in HERE.glob("*.py"):
            (self.root / "scripts" / script.name).symlink_to(script)
        (self.root / "scripts/gate.py").unlink()
        (self.root / "scripts/gate.py").write_text(
            f"import sys\nprint({says!r})\nprint('B1-R4 unmet' if {answer} else 'releasable')\n"
            f"sys.exit({answer})\n",
            encoding="utf-8",
        )
        (self.root / "searched.txt").write_text("lemonfiber\n", encoding="utf-8")

    def test_a_pre_release_with_a_goal_unmet_is_refused(self):
        self.stub_gate(1)
        done = self.run_step("prerelease-version.yml", GATES[0])
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("B1-R4 unmet", done.stdout)

    def test_a_pre_release_with_every_goal_met_goes_on(self):
        self.stub_gate(0)
        done = self.run_step("prerelease-version.yml", GATES[0])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_gate_that_warns_refuses_the_tag_in_either_lane(self):
        """A tag is cut only where the gate prints no error and no warning (OPS-R70)."""
        for workflow in LANES:
            with self.subTest(workflow):
                self.stub_gate(0, says="::warning::something the gate could not vouch for")
                done = self.run_step(workflow, GATES[0])
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn("prints none (OPS-R70)", done.stdout)

    def stub_gh(self):
        (self.bin / "gh").write_text(GH, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)
        self.log = self.root / "gh.log"
        self.log.write_text("", encoding="utf-8")

    def calls(self) -> list[str]:
        return self.read("gh.log").splitlines()

    def tagging(self, held: str = "") -> tuple[subprocess.CompletedProcess, str]:
        """The tag loop over the core, with `held` naming what already carries the tag."""
        self.stub_gh()
        self.stream("lemonfiber")
        (self.root / "tagging.txt").write_text("lemonfiber\n", encoding="utf-8")
        head = subprocess.run(
            ["git", "-C", "checkouts/lemonfiber", "rev-parse", "HEAD"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return head, held.replace("HEAD", head)

    def test_the_tag_loop_tags_a_repository_that_lacks_the_tag(self):
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                head, _ = self.tagging()
                done = self.run_step(workflow, TAG_LOOP, GH_LOG=str(self.log), OWNER="o")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn(
                    f"api --method POST repos/o/lemonfiber/git/refs -f ref=refs/tags/{tag} -f sha={head}",
                    self.calls(),
                )

    def test_the_tag_loop_passes_over_a_repository_carrying_the_tag_at_its_commit(self):
        """A run that stopped part-way through the loop is finished by running it again."""
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                head, held = self.tagging("lemonfiber=HEAD")
                done = self.run_step(workflow, TAG_LOOP, GH_LOG=str(self.log), OWNER="o", GH_HELD=held)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn(f"lemonfiber already carries {tag} @ {head[:8]}.", done.stdout)
                self.assertFalse([call for call in self.calls() if "POST" in call])

    def test_the_tag_loop_refuses_a_repository_carrying_the_tag_elsewhere(self):
        for workflow, (_, tag) in LANES.items():
            with self.subTest(workflow):
                self.fresh()
                head, _ = self.tagging()
                done = self.run_step(
                    workflow, TAG_LOOP, GH_LOG=str(self.log), OWNER="o", GH_HELD=f"lemonfiber={SHA}"
                )
                self.assertEqual(done.returncode, 1)
                self.assertIn(f"::error::lemonfiber carries {tag} at {SHA[:8]}, not {head[:8]}", done.stdout)
                self.assertFalse([call for call in self.calls() if "POST" in call])

    def test_the_tag_loop_stops_where_the_tag_cannot_be_looked_up(self):
        """A lookup that failed says nothing about the tag, so nothing is tagged on it."""
        for workflow in LANES:
            with self.subTest(workflow):
                self.fresh()
                self.tagging()
                done = self.run_step(workflow, TAG_LOOP, GH_LOG=str(self.log), OWNER="o", GH_REFS_FAIL="1")
                self.assertNotEqual(done.returncode, 0)
                self.assertNotIn("carries", done.stdout)
                self.assertFalse([call for call in self.calls() if "POST" in call])

    def manifest(self, recorded: str = ""):
        """0.2.0 as staged, holding `recorded` as its pre-release records."""
        (self.root / "70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nstatus = "staged"\nrepos = ["lemonfiber", "lemonfiber-decline"]\n' + recorded,
            encoding="utf-8",
        )

    def test_reading_the_manifest_says_whether_the_tag_is_recorded(self):
        record = f'\n[[prerelease]]\ntag = "v0.2.0-pre.1"\npins = {{ lemonfiber-plugins = "{SHA}" }}\n'
        for recorded, says in (("", "false"), (record, "true")):
            with self.subTest(says):
                self.fresh()
                self.manifest(recorded)
                (self.bin / "git").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                (self.bin / "git").chmod(0o755)
                done = self.run_step("prerelease-version.yml", CLONE, GH_TOKEN="t", OWNER="o")
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn(f"recorded={says}\n", self.read("output"))

    def test_a_record_naming_the_pins_this_run_embeds_lets_the_tag_go_on(self):
        self.fresh()
        self.manifest(f'\n[[prerelease]]\ntag = "v0.2.0-pre.1"\npins = {{ lemonfiber-plugins = "{SHA}" }}\n')
        done = self.run_step("prerelease-version.yml", RECORDED, PINS=f"lemonfiber-plugins={SHA}")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("tagging without recording again", done.stdout)

    def test_a_record_naming_other_pins_is_refused(self):
        """The tag and the record would otherwise describe two builds."""
        self.fresh()
        self.manifest(f'\n[[prerelease]]\ntag = "v0.2.0-pre.1"\npins = {{ lemonfiber-plugins = "{SHA}" }}\n')
        done = self.run_step("prerelease-version.yml", RECORDED, PINS=f"lemonfiber-plugins={'c' * 40}")
        self.assertEqual(done.returncode, 1)
        self.assertIn("::error::v0.2.0-pre.1 is recorded with pins", done.stderr)


class TheRecordBranch(unittest.TestCase):
    """The record's branch is rebuilt from main, so a re-run is never refused by its own leftovers."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "gh").write_text(GH, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)
        for path in (
            "70-operations/versions/0.2.0.toml",
            "00-overview/roadmap.md",
            "10-functional/features/index.json",
            "10-functional/features/a-one/board.json",
        ):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text("written\n", encoding="utf-8")
        self.log = self.root / "gh.log"
        self.log.write_text("", encoding="utf-8")

    def run_action(self, **extra) -> tuple[subprocess.CompletedProcess, list[str]]:
        steps = yaml.safe_load(TRANSITION.read_text(encoding="utf-8"))["runs"]["steps"]
        run = next(one for one in steps if one.get("name") == REBUILT)["run"]
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.log),
            "OWNER": "o",
            "VERSION": "0.2.0",
            "STATUS": "staged",
            "PRERELEASE": "v0.2.0-pre.1",
            **extra,
        }
        done = subprocess.run(
            ["bash", "-e", "-c", run], capture_output=True, text=True, cwd=self.root, env=env, check=False
        )
        return done, self.log.read_text(encoding="utf-8").splitlines()

    def test_a_branch_an_earlier_run_left_is_deleted_before_it_is_made_again(self):
        done, calls = self.run_action(GH_BRANCH_LEFT="1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        deleted = calls.index(
            "api --method DELETE repos/o/spec/git/refs/heads/release/0.2.0-prerelease-0.2.0-pre.1"
        )
        made = calls.index(
            "api --method POST repos/o/spec/git/refs "
            f"-f ref=refs/heads/release/0.2.0-prerelease-0.2.0-pre.1 -f sha={SHA} --silent"
        )
        self.assertLess(deleted, made)
        self.assertTrue(calls[-1].startswith("pr merge https://github.com/o/spec/pull/1"))

    def test_a_branch_carrying_someone_else_s_commit_is_left_alone(self):
        done, calls = self.run_action(GH_BRANCH_LEFT="1", GH_OTHERS="2")
        self.assertEqual(done.returncode, 1)
        self.assertIn("carries 2 commit(s) the release App did not write", done.stdout)
        self.assertFalse([call for call in calls if "DELETE" in call or call.startswith("api --method POST")])
        asked = [call for call in calls if "/compare/main...release/0.2.0-prerelease-0.2.0-pre.1" in call]
        self.assertEqual(len(asked), 1)
        self.assertIn('select(.author.login != "lemonfiber-release-train[bot]")', asked[0])

    def test_a_first_run_makes_the_branch_without_deleting_anything(self):
        done, calls = self.run_action()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse([call for call in calls if "DELETE" in call])
        self.assertEqual(len([call for call in calls if call.startswith("api --method PUT")]), 4)


class EveryMintNamesWhatItUses(unittest.TestCase):
    """The release App can write every repository's contents, workflows and actions,
    so each token minted from it asks for the permissions its steps use and no
    others; a mint naming none would carry all of them."""

    def mints(self):
        files = sorted(WORKFLOWS.glob("*.yml")) + sorted(
            (HERE.parent / ".github" / "actions").glob("*/action.yml")
        )
        for path in files:
            read = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            jobs = read.get("jobs") or {"action": (read.get("runs") or {})}
            for name, job in jobs.items():
                for step in job.get("steps") or []:
                    if "create-github-app-token@" in str(step.get("uses", "")):
                        yield f"{path.name} {name}", step.get("with") or {}

    def test_every_mint_names_its_permissions(self):
        found = list(self.mints())
        self.assertGreater(len(found), 10)
        for where, given in found:
            asked = {key: value for key, value in given.items() if key.startswith("permission-")}
            self.assertTrue(asked, where)
            self.assertLessEqual(set(asked.values()), {"read", "write"}, where)


if __name__ == "__main__":
    unittest.main(verbosity=1)
