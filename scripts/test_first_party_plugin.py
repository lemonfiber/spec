"""`first-party-plugin.yml`'s own steps: what counts as a change the verdict reads, the
reader taken into a plugin that carries none, the record the run writes, and the
lemonfiber handed from the verdict to the live run."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/first-party-plugin.yml"
GIT = (
    "git",
    "-c",
    "user.name=test",
    "-c",
    "user.email=test@invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
)


def step(job: str, named: str | None = None, number: int | None = None) -> str:
    """The `run` of one step of the workflow, by its name or its position."""
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][job]["steps"]
    chosen = steps[number] if named is None else next(one for one in steps if one.get("name") == named)
    return chosen["run"]


class WhatChanged(unittest.TestCase):
    """The `what changed` step says `code=false` only where nothing the verdict reads changed."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        self.commit({"README.md": "x\n"})
        self.base = self.head()

    def commit(self, files: dict[str, str]) -> None:
        for path, content in files.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "--allow-empty", "-m", "c"], cwd=self.root, check=True)

    def head(self) -> str:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True)
        return done.stdout.strip()

    def code(self, base: str, directory: str = ".") -> str:
        output = self.root / ".output"
        env = {"PATH": os.environ["PATH"], "BASE": base, "DIRECTORY": directory, "GITHUB_OUTPUT": str(output)}
        subprocess.run(
            ["bash", "-c", step("scope", number=1)], cwd=self.root, env=env, check=True, capture_output=True
        )
        said = output.read_text(encoding="utf-8")
        output.unlink()
        return said.strip()

    def test_documentation_alone_is_not_judged_again(self):
        self.commit({"README.md": "y\n", "docs/a.md": "z\n", "LICENSE": "l\n", "status.toml": "s\n"})
        self.assertEqual(self.code(self.base), "code=false")

    def test_the_manifest_a_recording_or_a_starting_file_is_judged(self):
        for path in ("plugin.toml", "recordings/x/a.json", "config/x/a.ini", "targets.toml"):
            with self.subTest(path=path):
                self.commit({path: path})
                self.assertEqual(self.code(self.base), "code=true")

    def test_a_workflow_is_judged(self):
        self.commit({".github/workflows/plugin.yml": "on: push\n"})
        self.assertEqual(self.code(self.base, "part"), "code=true")

    def test_only_the_named_directory_is_read_where_one_is_named(self):
        self.commit({"plugin.toml": "elsewhere\n", "part/README.md": "doc\n"})
        self.assertEqual(self.code(self.base, "part"), "code=false")
        self.commit({"part/plugin.toml": "here\n"})
        self.assertEqual(self.code(self.base, "part/"), "code=true")

    def test_no_base_to_compare_against_is_judged(self):
        self.assertEqual(self.code(""), "code=true")
        self.assertEqual(self.code("0" * 40), "code=true")


class TheReader(unittest.TestCase):
    """The reader is taken into the plugin, and a plugin carrying its own is refused."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        taken = self.root / ".first-party-reader" / ".github" / "reader"
        taken.mkdir(parents=True)
        (taken / "reader.py").write_text("print('reader')\n", encoding="utf-8")
        self.plugin = self.root / "part"
        self.plugin.mkdir()

    def take(self) -> subprocess.CompletedProcess:
        env = {
            "PATH": os.environ["PATH"],
            "READER": ".github/reader",
            "TAKEN": str(self.root / ".first-party-reader"),
        }
        script = step("plugin", "The reader is this workflow's, and the plugin carries none")
        return subprocess.run(
            ["bash", "-c", script], cwd=self.plugin, env=env, capture_output=True, text=True
        )

    def test_the_reader_is_taken_in_and_its_checkout_removed(self):
        done = self.take()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((self.plugin / ".github" / "reader" / "reader.py").is_file())
        self.assertFalse((self.root / ".first-party-reader").exists())

    def test_a_plugin_carrying_its_own_reader_is_refused(self):
        (self.plugin / ".github" / "reader").mkdir(parents=True)
        done = self.take()
        self.assertEqual(done.returncode, 1)
        self.assertIn("carries no Python of its own", done.stdout)


class TheRecord(unittest.TestCase):
    """The committed `proofs.json` is the one the run writes, and an uncommitted one is refused."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        reader = self.root / ".github" / "reader"
        reader.mkdir(parents=True)
        (reader / "reader.py").write_text(
            "import pathlib\npathlib.Path('proofs.json').write_text('{\"proofs\": []}\\n')\n",
            encoding="utf-8",
        )

    def proved(self) -> subprocess.CompletedProcess:
        script = step("plugin", "Every claim, proof and contributed check, against its recording")
        env = {"PATH": os.environ["PATH"]}
        return subprocess.run(
            ["bash", "-e", "-c", script], cwd=self.root, env=env, capture_output=True, text=True
        )

    def committed(self, content: str) -> None:
        (self.root / "proofs.json").write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "proofs.json"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "p"], cwd=self.root, check=True)

    def test_an_uncommitted_record_is_refused(self):
        done = self.proved()
        self.assertEqual(done.returncode, 1)
        self.assertIn("proofs.json is not committed", done.stdout)

    def test_the_record_the_run_writes_passes(self):
        self.committed('{"proofs": []}\n')
        self.assertEqual(self.proved().returncode, 0)

    def test_a_record_the_run_does_not_write_is_refused(self):
        self.committed('{"proofs": ["stale"]}\n')
        done = self.proved()
        self.assertEqual(done.returncode, 1)
        self.assertIn("is not what this run writes", done.stdout)


class HandedToLive(unittest.TestCase):
    """The live run reads with the lemonfiber the verdict read with, kept in `.lemonfiber/`."""

    def setUp(self):
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        self.uploaded = next(
            one
            for one in jobs["plugin"]["steps"]
            if one.get("uses", "").startswith("actions/upload-artifact@")
        )
        self.downloaded = next(
            one
            for one in jobs["live"]["steps"]
            if one.get("uses", "").startswith("actions/download-artifact@")
        )

    def test_the_hidden_directory_the_reader_keeps_it_in_is_uploaded(self):
        self.assertTrue(self.uploaded["with"]["path"].endswith("/.lemonfiber/"))
        self.assertIs(self.uploaded["with"]["include-hidden-files"], True)

    def test_a_verdict_that_kept_none_says_so(self):
        self.assertEqual(self.uploaded["with"]["if-no-files-found"], "error")

    def test_the_live_run_takes_what_the_verdict_kept(self):
        self.assertEqual(self.downloaded["with"]["name"], self.uploaded["with"]["name"])


class TheStandIn(unittest.TestCase):
    """What the image a plugin's Dockerfile builds stands in for: its adapter where a service
    fronts one, the plugin's own service where nothing speaks a contract and that service
    runs this repository's own image or, before its first pin, exactly the image and digest
    the Dockerfile's last FROM builds on, and nothing otherwise."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text('#!/bin/sh\necho "$@" >> "$(dirname "$0")/asked"\n', encoding="utf-8")
        docker.chmod(0o755)
        self.plugin = self.root / "part"
        self.plugin.mkdir()
        (self.plugin / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    def stands_in(self, manifest: str) -> tuple[str, bool]:
        (self.plugin / "plugin.toml").write_text(manifest, encoding="utf-8")
        output = self.root / ".output"
        output.write_text("", encoding="utf-8")
        tooling = self.root / ".spec-tooling"
        (tooling / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy(pathlib.Path(__file__).with_name("first_pin.py"), tooling / "scripts")
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "OWNER": "LemonFiber",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(self.root / ".summary"),
            "TOOLING": str(tooling),
        }
        script = step("live", "The image this tree builds")
        done = subprocess.run(
            ["bash", "-c", script], cwd=self.plugin, env=env, capture_output=True, text=True
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        said = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").split())
        self.unpinned = said.get("unpinned") == "true"
        self.assertFalse(tooling.exists())
        return said.get("as", ""), (self.bin / "asked").exists()

    def test_a_part_built_here_stands_in_for_its_own_service(self):
        for plugin in ("request-gate", "decline"):
            with self.subTest(plugin=plugin):
                manifest = f"""[plugin]
id = "{plugin}"

[[service]]
id    = "{plugin}"
image = "ghcr.io/lemonfiber/{plugin}"
"""
                self.assertEqual(self.stands_in(manifest), ("built", True))
                self.assertFalse(self.unpinned)

    def test_an_adapter_built_here_stands_in_for_the_adapter_that_fronts(self):
        manifest = """[plugin]
id = "caddy"

[[service]]
id    = "caddy"
image = "ghcr.io/lemonfiber/caddy"

[[service]]
id     = "caddy-adapter"
image  = "ghcr.io/lemonfiber/caddy-adapter"
fronts = "caddy"
speaks = ["proxy.front@1"]
"""
        self.assertEqual(self.stands_in(manifest), ("adapter", True))

    def test_an_adapter_the_manifest_does_not_run_yet_stands_in_for_nothing(self):
        manifest = """[plugin]
id = "homepage"

[[service]]
id    = "homepage"
image = "ghcr.io/gethomepage/homepage"
"""
        self.assertEqual(self.stands_in(manifest), ("", False))

    def test_another_organisations_image_of_the_same_name_is_not_built_here(self):
        manifest = """[plugin]
id = "decline"

[[service]]
id    = "decline"
image = "ghcr.io/someone-else/decline"
"""
        self.assertEqual(self.stands_in(manifest), ("", False))

    def test_a_part_that_speaks_a_contract_from_its_own_image_is_recorded_from_its_pin(self):
        manifest = """[plugin]
id = "decline"

[[service]]
id     = "decline"
image  = "ghcr.io/lemonfiber/decline"
speaks = ["invite.decline@1"]
"""
        self.assertEqual(self.stands_in(manifest), ("", False))

    UPSTREAM = "sha256:" + "3a" * 32

    def before_its_first_pin(self, dockerfile: str, digest: str) -> tuple[str, bool]:
        (self.plugin / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        return self.stands_in(f"""[plugin]
id = "door"

[[service]]
id     = "door"
image  = "caddy"
digest = "{digest}"
""")

    def test_a_part_before_its_first_pin_stands_in_where_it_pins_what_its_dockerfile_builds_on(self):
        for dockerfile in (
            f"FROM caddy:2.11.6@{self.UPSTREAM}\nUSER 1000:1000\n",
            f"from --platform=$BUILDPLATFORM caddy@{self.UPSTREAM} AS door\n",
            f"FROM golang:1@sha256:{'0' * 64} AS build\nRUN true\nFROM caddy:2.11.6@{self.UPSTREAM}\n",
        ):
            with self.subTest(dockerfile=dockerfile):
                self.assertEqual(self.before_its_first_pin(dockerfile, self.UPSTREAM), ("built", True))
                self.assertTrue(self.unpinned)
                self.assertIn("ships nothing", (self.root / ".summary").read_text(encoding="utf-8"))

    def test_the_same_image_at_another_digest_is_not_what_the_dockerfile_builds_on(self):
        self.assertEqual(
            self.before_its_first_pin(f"FROM caddy:2.11.6@{self.UPSTREAM}\n", "sha256:" + "3b" * 32),
            ("", False),
        )

    def test_a_dockerfile_that_builds_on_no_digest_or_on_another_image_last_stands_in_for_nothing(self):
        for dockerfile in (
            "FROM caddy:2.11.6\n",
            f"FROM caddy:2.11.6@{self.UPSTREAM} AS build\nFROM scratch\n",
            f"FROM ghcr.io/someone-else/caddy@{self.UPSTREAM}\n",
        ):
            with self.subTest(dockerfile=dockerfile):
                self.assertEqual(self.before_its_first_pin(dockerfile, self.UPSTREAM), ("", False))

    def test_a_part_that_speaks_a_contract_is_recorded_from_its_pin_even_before_it(self):
        (self.plugin / "Dockerfile").write_text(f"FROM caddy:2.11.6@{self.UPSTREAM}\n", encoding="utf-8")
        manifest = f"""[plugin]
id = "door"

[[service]]
id     = "door"
image  = "caddy"
digest = "{self.UPSTREAM}"
speaks = ["stream.guard@1"]
"""
        self.assertEqual(self.stands_in(manifest), ("", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
