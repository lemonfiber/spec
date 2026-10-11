"""`first-party-plugin.yml`'s own steps: what counts as a change the verdict reads, the
reader taken into a plugin that carries none, and the record the run writes."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/first-party-plugin.yml"
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")


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
        subprocess.run(["bash", "-c", step("scope", number=1)], cwd=self.root, env=env, check=True,
                       capture_output=True)
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
        env = {"PATH": os.environ["PATH"], "READER": ".github/reader",
               "TAKEN": str(self.root / ".first-party-reader")}
        script = step("plugin", "The reader is this workflow's, and the plugin carries none")
        return subprocess.run(["bash", "-c", script], cwd=self.plugin, env=env, capture_output=True, text=True)

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
            "import pathlib\npathlib.Path('proofs.json').write_text('{\"proofs\": []}\\n')\n", encoding="utf-8"
        )

    def proved(self) -> subprocess.CompletedProcess:
        script = step("plugin", "Every claim, proof and contributed check, against its recording")
        env = {"PATH": os.environ["PATH"]}
        return subprocess.run(["bash", "-e", "-c", script], cwd=self.root, env=env, capture_output=True, text=True)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
