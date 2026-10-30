#!/usr/bin/env python3
"""`pin_bump.py`, and the two workflows that move a pin with its recordings: which
recordings are stale, which reader is taken, how recording is asked and what it leaves,
which push moves only a pin, and which job holds what.

Stdlib unittest and PyYAML. No registry is asked, no lemonfiber is built and no
container is run: the reader is a stand-in answering as plugin-template's does.
Run:  python3 scripts/test_pin_bump.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pin_bump  # noqa: E402

WORKFLOWS = SCRIPTS.parent / ".github/workflows"
IMAGE = "lscr.io/linuxserver/sonarr"
DIGEST, OLD = "sha256:" + "a" * 64, "sha256:" + "0" * 64
GUARDED_BODY = "only the runner may read this"
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


class InDirectory(unittest.TestCase):
    """A working directory of its own, as every workflow step has, and a secret-looking
    file outside it that nothing may read."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.outside = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(shutil.rmtree, self.outside, True)
        self.guarded = self.outside / "guarded-file"
        self.guarded.write_text(GUARDED_BODY)
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)

    def put(self, relative: str, body) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body if isinstance(body, str) else json.dumps(body))
        return path

    def ran(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pin_bump.main(list(args))
        return code, out.getvalue(), err.getvalue()


class Stale(InDirectory):
    """Which recordings still name the image a bump replaces, read from the files."""

    def test_only_a_plain_recording_of_the_image_at_another_digest_is_stale(self):
        for path, body in (
            ("recordings/sonarr/old.json", {"recorded_from": f"{IMAGE}@{OLD}"}),
            ("recordings/sonarr/new.json", {"recorded_from": f"{IMAGE}@{DIGEST}"}),
            ("conformance/x@1/case.json", {"recorded_from": f"{IMAGE}@{OLD}"}),
            ("recordings/other/old.json", {"recorded_from": f"caddy@{OLD}"}),
            ("proofs.json", {"proofs": []}),
            (".github/reader/old.json", {"recorded_from": f"{IMAGE}@{OLD}"}),
            ("list.json", ["not", "a", "recording"]),
            ("broken.json", "{"),
            ("notes.txt", "x"),
        ):
            self.put(path, body)
        os.symlink(self.guarded, self.root / "recordings/sonarr/linked.json")
        self.guarded.chmod(0)
        self.addCleanup(self.guarded.chmod, 0o600)
        self.assertEqual(
            pin_bump.stale(self.root, IMAGE, DIGEST),
            ["conformance/x@1/case.json", "recordings/sonarr/old.json"],
        )


class Reader(InDirectory):
    """The reader's revision is the one `first-party-plugin` pins, written once."""

    def test_the_first_party_plugin_workflow_pins_one_this_reads(self):
        found = pin_bump.reader_of((WORKFLOWS / "first-party-plugin.yml").read_text(encoding="utf-8"))
        self.assertEqual(found["repository"], "lemonfiber/plugin-template")
        self.assertRegex(found["revision"], r"\A[0-9a-f]{40}\Z")

    def test_a_workflow_pinning_no_full_revision_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no reader repository and full revision"):
            pin_bump.reader_of(
                "env:\n  READER_REPOSITORY: lemonfiber/plugin-template\n  READER_REVISION: main\n"
            )

    def test_reader_prints_the_outputs(self):
        self.put("first-party-plugin.yml", (WORKFLOWS / "first-party-plugin.yml").read_text())
        code, out, _ = self.ran("reader", "--workflow", "first-party-plugin.yml")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"\Arepository=lemonfiber/plugin-template\nrevision=[0-9a-f]{40}\n\Z")


# A reader answering as plugin-template's does: `plugin` returns what lemonfiber said,
# or raises `Unasked`, and `reader.py proofs` writes `proofs.json` and exits as told.
STAND_IN = """
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Unasked(RuntimeError):
    pass


def plugin(*asked):
    (ROOT / ".lemonfiber").mkdir(exist_ok=True)
    if RECORD is None:
        raise Unasked("lemonfiber at abc did not build")
    assert asked == ("record",)
    return subprocess.CompletedProcess([], RECORD, "wrote 2 recordings\\n", "")


if __name__ == "__main__":
    assert sys.argv[1:] == ["proofs"]
    (ROOT / "proofs.json").write_text(json.dumps({"proofs": []}))
    sys.exit(PROOFS)
"""


# A `docker` that logs each call and refuses to pull the reference named in `REFUSED`.
DOCKER = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["DOCKER_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[-1] == os.environ["REFUSED"]:
    sys.exit("Error response from daemon: no such manifest")
"""


class Recorded(InDirectory):
    """`record` puts the workflow's reader into the plugin, asks it, warns of what failed,
    and leaves neither the reader nor what it built behind."""

    def recorded(self, record, proofs: int = 0) -> tuple[int, str, str]:
        self.put("plugin/plugin.toml", "schema_version = 1\n")
        self.put("taken/reader.py", f"RECORD = {record!r}\nPROOFS = {proofs}\n{STAND_IN}")
        return self.ran("record", "--manifest", "plugin/plugin.toml", "--reader", "taken")

    def test_a_record_that_finished_says_what_it_wrote_and_writes_the_proofs(self):
        code, out, _ = self.recorded(0)
        self.assertEqual(code, 0)
        self.assertIn("wrote 2 recordings", out)
        self.assertNotIn("::warning::", out)
        self.assertTrue((self.root / "plugin/proofs.json").is_file())
        self.assertFalse((self.root / "plugin/.github/reader").exists())
        self.assertFalse((self.root / "plugin/.lemonfiber").exists())

    def test_a_record_or_proofs_that_failed_or_a_lemonfiber_that_could_not_be_had_is_warned_of(self):
        for record, proofs, said in (
            (1, 0, "::warning::lemonfiber plugin record exited 1"),
            (None, 0, "::warning::lemonfiber plugin record exited 1"),
            (0, 1, "::warning::not every assertion holds on the new recordings"),
        ):
            with self.subTest(record=record, proofs=proofs):
                shutil.rmtree(self.root / "plugin", True)
                code, out, _ = self.recorded(record, proofs)
                self.assertEqual(code, 0)
                self.assertIn(said, out)
                self.assertFalse((self.root / "plugin/.github/reader").exists())

    def test_every_pinned_image_is_pulled_by_digest_before_recording_and_one_that_fails_is_warned_of(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "docker").write_text(DOCKER)
        (bin_dir / "docker").chmod(0o755)
        log = self.root / "docker.log"
        patched = mock.patch.dict(
            os.environ,
            {"PATH": f"{bin_dir}:{os.environ['PATH']}", "DOCKER_LOG": str(log), "REFUSED": f"caddy@{OLD}"},
        )
        patched.start()
        self.addCleanup(patched.stop)
        manifest = "".join(
            f'[[service]]\nid = "s{at}"\nimage = "{image}"\ndigest = "{digest}"\n\n'
            for at, (image, digest) in enumerate(
                ((IMAGE, DIGEST), (IMAGE, DIGEST), ("caddy", OLD), ("--rm", DIGEST), (IMAGE, "latest"))
            )
        )
        self.put("plugin/plugin.toml", manifest)
        self.put("taken/reader.py", f"RECORD = 0\nPROOFS = 0\n{STAND_IN}")
        code, out, _ = self.ran("record", "--manifest", "plugin/plugin.toml", "--reader", "taken")
        self.assertEqual(code, 0)
        self.assertEqual(
            [json.loads(line) for line in log.read_text().splitlines()],
            [["pull", "--quiet", f"caddy@{OLD}"], ["pull", "--quiet", f"{IMAGE}@{DIGEST}"]],
        )
        self.assertIn(
            f"::warning::caddy@{OLD} could not be pulled: Error response from daemon: no such manifest", out
        )
        self.assertLess(out.index("could not be pulled"), out.index("wrote 2 recordings"))

    def test_a_plugin_carrying_a_reader_or_a_linked_github_is_refused_and_nothing_is_run(self):
        self.put("plugin/.github/reader/reader.py", "raise SystemExit('the plugin ran its own')")
        code, _, err = self.recorded(0)
        self.assertEqual(code, 1)
        self.assertIn(".github/reader is in the plugin", err)
        shutil.rmtree(self.root / "plugin/.github")
        os.symlink(self.outside, self.root / "plugin/.github")
        code, _, err = self.recorded(0)
        self.assertEqual(code, 1)
        self.assertIn(".github in the plugin is not a plain directory", err)
        self.assertEqual(os.listdir(self.outside), ["guarded-file"])


class PinsOnly(InDirectory):
    """Which push changes nothing but a pin: no image is published from it."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        self.put("plugin.toml", "schema_version = 1\n")
        self.put("src/main.rs", "fn main() {}\n")
        self.before = self.commit()

    def commit(self) -> str:
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "--allow-empty", "-m", "c"], cwd=self.root, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout.strip()

    def asked(self, *changed: str, directory: str = ".", before: str = "") -> str:
        for path in changed:
            self.put(path, f"changed {path}\n")
        after = self.commit()
        code, out, _ = self.ran(
            "pins-only", "--before", before or self.before, "--after", after, "--directory", directory
        )
        self.assertEqual(code, 0)
        return out.strip()

    def test_a_pin_its_recordings_its_proofs_and_its_target_are_only_a_pin(self):
        self.assertEqual(
            self.asked("plugin.toml", "recordings/x/a.json", "proofs.json", "targets.toml"), "yes"
        )

    def test_anything_else_beside_them_is_not(self):
        for path in ("src/main.rs", "README.md", "conformance/x@1/a.json", "nested/plugin.toml"):
            with self.subTest(path=path):
                self.assertEqual(self.asked("plugin.toml", path), "no")

    def test_a_plugin_in_a_directory_is_read_there(self):
        self.assertEqual(self.asked("door/plugin.toml", "door/recordings/a.json", directory="door/"), "yes")
        self.assertEqual(self.asked("plugin.toml", directory="door"), "no")

    def test_nothing_changed_or_no_commit_before_publishes(self):
        self.assertEqual(self.asked(), "no")
        self.assertEqual(self.asked("plugin.toml", before="0" * 40), "no")
        self.assertEqual(self.asked("plugin.toml", before="f" * 40), "no")

    def test_a_commit_after_that_cannot_be_read_fails(self):
        code, _, err = self.ran("pins-only", "--before", self.before, "--after", "f" * 40)
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)


class Workflows(unittest.TestCase):
    """Both workflows that move a pin hold the image and the build apart from the token."""

    NAMES = ("upstream-pin.yml", "manifest-pin.yml")

    @staticmethod
    def jobs(name: str) -> dict:
        return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]

    def test_nothing_that_runs_the_image_or_builds_lemonfiber_shares_a_job_with_a_secret(self):
        for name in self.NAMES:
            with self.subTest(workflow=name):
                record, commit = self.jobs(name)["record"], self.jobs(name)["commit"]
                self.assertNotIn("secrets.", json.dumps(record))
                self.assertNotIn("environment", record)
                self.assertEqual(record["permissions"], {"contents": "read"})
                self.assertEqual(
                    (commit["environment"], commit["permissions"]), ("release", {"contents": "read"})
                )
                ran = json.dumps(commit["steps"])
                for untrusted in ("reader", "plugin record", "pin_bump.py record", "proofs", "setup-python"):
                    self.assertNotIn(untrusted, ran.replace("first-party-plugin", ""))
                for job in (record, commit):
                    for one in job["steps"]:
                        if one.get("uses", "").startswith("actions/checkout@"):
                            self.assertFalse(one["with"]["persist-credentials"])

    def test_the_token_job_checks_the_plugin_out_beside_its_own_scratch_and_admits_before_minting(self):
        for name in self.NAMES:
            with self.subTest(workflow=name):
                steps = self.jobs(name)["commit"]["steps"]
                self.assertEqual(steps[0]["with"]["path"], "${{ env.PLUGIN }}")
                names = [one.get("name", "") for one in steps]
                self.assertLess(
                    names.index("Only the move, admitted"), names.index("Mint a token that can commit here")
                )

    def test_both_record_and_stage_through_this_script(self):
        for name in self.NAMES:
            with self.subTest(workflow=name):
                ran = "\n".join(one.get("run", "") for one in self.jobs(name)["record"]["steps"])
                for asked in ("reader", "record", "stage"):
                    self.assertIn(f"scripts/pin_bump.py {asked} ", ran)


class Main(InDirectory):
    """The command, as each workflow step runs it."""

    def test_a_manifest_path_that_names_no_manifest_is_refused(self):
        code, _, err = self.ran("record", "--manifest", "main.toml", "--reader", ".")
        self.assertEqual(code, 1)
        self.assertIn("is not a plugin.toml", err)


if __name__ == "__main__":
    unittest.main()
