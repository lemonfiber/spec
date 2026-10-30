#!/usr/bin/env python3
"""Coverage tests for upstream_drift.py — what a repository takes, held against what main ships (Q-R68, Q-R70).

Each upstream is a real repository in a scratch directory, cloned the way a run
clones GitHub, so the readers and the comparison meet git as it answers rather
than a stand-in for it.

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_upstream_drift.py
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
import time
import unittest
import unittest.mock

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pin_window
import upstream_drift

#: A run a day and more after every commit a fixture makes, so each is past the window.
LATER = int(time.time()) + 2 * pin_window.SECONDS


def git(where: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class Upstreams:
    """Repositories of a pretend organisation, each with a `main` to commit to."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.here = self.root / "here"
        self.here.mkdir()
        self.origin = str(self.root / "org" / "{}.git")
        self.summary = self.root / "summary.md"
        patcher = unittest.mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(self.summary)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.now = LATER
        clock = unittest.mock.patch.object(upstream_drift, "clock", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def upstream(self, name: str) -> pathlib.Path:
        work = self.root / "work" / name
        work.mkdir(parents=True)
        git(work, "init", "-q", "-b", "main")
        git(work, "config", "user.email", "t@example.com")
        git(work, "config", "user.name", "T")
        return work

    def commit(self, work: pathlib.Path, files: dict[str, str | None], when: int | None = None) -> str:
        if when is not None:
            stamp = unittest.mock.patch.dict(os.environ, {"GIT_COMMITTER_DATE": f"@{when} +0000"})
            stamp.start()
            self.addCleanup(stamp.stop)
        for path, text in files.items():
            where = work / path
            if text is None:
                where.unlink()
                continue
            where.parent.mkdir(parents=True, exist_ok=True)
            where.write_text(text, encoding="utf-8")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "change")
        return git(work, "rev-parse", "HEAD")

    def publish(self, work: pathlib.Path) -> None:
        bare = pathlib.Path(self.origin.format(work.name))
        if bare.exists():
            shutil.rmtree(bare)
        bare.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True)

    def ran(self, *arguments: str) -> tuple[int, str]:
        with contextlib.redirect_stdout(io.StringIO()) as said:
            code = upstream_drift.run(list(arguments), self.here, self.origin)
        return code, said.getvalue()

    def wrote(self, path: str, text: str) -> None:
        where = self.here / path
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text, encoding="utf-8")


class Composer(Upstreams, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.sdk = self.upstream("sdk-php")
        self.first = self.commit(
            self.sdk,
            {
                ".gitattributes": "/tests export-ignore\n/.github export-ignore\n",
                "src/Client.php": "one",
                "tests/A.php": "a",
            },
        )

    def lock(self, reference: str, url: str = "https://github.com/lemonfiber/sdk-php.git") -> None:
        self.wrote(
            "composer.lock",
            json.dumps(
                {
                    "packages": [
                        {
                            "name": "lemonfiber/sdk-php",
                            "source": {"type": "git", "url": url, "reference": reference},
                        },
                        {
                            "name": "other/thing",
                            "source": {"url": "https://github.com/other/thing.git", "reference": "x"},
                        },
                    ],
                    "packages-dev": [],
                }
            ),
        )

    def test_the_head_is_current(self):
        self.publish(self.sdk)
        self.lock(self.first)
        code, said = self.ran("composer")
        self.assertEqual(code, 0)
        self.assertIn("`lemonfiber/sdk-php` is current", said)
        self.assertIn("is current", self.summary.read_text(encoding="utf-8"))

    def test_a_change_to_what_ships_is_behind_and_names_the_command(self):
        self.lock(self.first)
        head = self.commit(self.sdk, {"src/Client.php": "two"})
        self.publish(self.sdk)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is behind sdk-php main", said)
        self.assertIn("`src/Client.php`", said)
        self.assertIn(
            "::error::lemonfiber/sdk-php is behind lemonfiber/sdk-php main — composer update lemonfiber/sdk-php",
            said,
        )
        self.assertIn(head[:7], said)

    def test_a_change_inside_the_window_warns_and_passes(self):
        self.now = 1_800_000_000
        self.lock(self.first)
        self.commit(self.sdk, {"src/Client.php": "two"}, when=self.now - 3600)
        self.publish(self.sdk)
        code, said = self.ran("composer")
        self.assertEqual(code, 0, said)
        refused = pin_window.refused_at(self.now - 3600)
        self.assertIn(
            f"::warning::lemonfiber/sdk-php is behind lemonfiber/sdk-php main, refused from {refused}", said
        )
        self.assertIn("for less than 24 hours", said)
        self.assertIn("`src/Client.php`", said)
        self.assertNotIn("::error::", said)

    def test_one_change_past_the_window_refuses(self):
        self.now = 1_800_000_000
        self.lock(self.first)
        self.commit(self.sdk, {"src/Client.php": "two"}, when=self.now - pin_window.SECONDS)
        self.commit(self.sdk, {"src/Other.php": "two"}, when=self.now - 60)
        self.publish(self.sdk)
        code, said = self.ran("composer")
        self.assertEqual(code, 1, said)
        self.assertIn("::error::lemonfiber/sdk-php is behind", said)

    def test_a_change_dated_after_the_run_counts_as_past_the_window(self):
        self.now = 1_800_000_000
        self.lock(self.first)
        self.commit(self.sdk, {"src/Client.php": "two"}, when=self.now + 3600)
        self.publish(self.sdk)
        self.assertEqual(self.ran("composer")[0], 1)

    def test_a_change_outside_what_ships_does_not_hold_the_window_open(self):
        self.now = 1_800_000_000
        self.lock(self.first)
        self.commit(self.sdk, {"src/Client.php": "two"}, when=self.now - 2 * pin_window.SECONDS)
        self.commit(self.sdk, {"tests/A.php": "b"}, when=self.now - 60)
        self.publish(self.sdk)
        self.assertEqual(self.ran("composer")[0], 1)

    def test_a_change_only_to_what_the_archive_leaves_out_is_current(self):
        self.lock(self.first)
        self.commit(self.sdk, {"tests/A.php": "b", ".github/ci.yml": "x"})
        self.publish(self.sdk)
        code, said = self.ran("composer")
        self.assertEqual(code, 0, said)
        self.assertIn("no file changed since is one this takes", said)

    def test_a_remedy_the_repository_names_is_what_is_named(self):
        self.lock(self.first)
        head = self.commit(self.sdk, {"src/Client.php": "two"})
        self.publish(self.sdk)
        code, said = self.ran("composer", "--remedy", "run `just take {name} {repo} {head}`")
        self.assertEqual(code, 1)
        self.assertIn(f"run `just take lemonfiber/sdk-php sdk-php {head}`", said)

    def test_a_pin_that_repository_does_not_have_is_named(self):
        self.publish(self.sdk)
        self.lock("f" * 40)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is not a commit in sdk-php", said)

    def test_a_pin_off_the_default_branch_is_named(self):
        git(self.sdk, "checkout", "-q", "-b", "side")
        side = self.commit(self.sdk, {"src/Client.php": "side"})
        git(self.sdk, "checkout", "-q", "main")
        self.commit(self.sdk, {"src/Client.php": "main"})
        self.publish(self.sdk)
        self.lock(side)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is not on sdk-php main", said)

    def test_a_pin_ahead_of_the_default_branch_is_named(self):
        self.publish(self.sdk)
        ahead = self.commit(self.sdk, {"src/Client.php": "ahead"})
        bare = pathlib.Path(self.origin.format("sdk-php"))
        subprocess.run(
            ["git", "-C", str(self.sdk), "push", "-q", str(bare), "main:refs/heads/later"], check=True
        )
        self.lock(ahead)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is not on sdk-php main", said)

    def test_a_reference_that_is_not_a_full_hash_is_refused(self):
        self.publish(self.sdk)
        self.lock("main")
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is not a commit", said)
        self.assertIn("not pinned to a full commit hash", said)

    def test_more_changed_files_than_are_listed_are_counted(self):
        self.lock(self.first)
        self.commit(self.sdk, {f"src/F{n}.php": "x" for n in range(25)})
        self.publish(self.sdk)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("and 5 more", said)

    def test_a_repository_that_cannot_be_cloned_is_not_reported_current(self):
        self.lock(self.first)
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("could not be cloned", said)
        self.assertIn("rerun this check", said)

    def test_an_unreadable_lock_compares_nothing_and_fails(self):
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("composer.lock could not be read", said)

    def test_a_lock_that_is_not_an_object_compares_nothing_and_fails(self):
        self.wrote("composer.lock", "[]")
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("is not a JSON object", said)

    def test_a_lock_taking_nothing_of_ours_fails_rather_than_passing_on_nothing(self):
        self.lock(self.first, url="https://github.com/other/sdk-php.git")
        code, said = self.ran("composer")
        self.assertEqual(code, 1)
        self.assertIn("so nothing was compared", said)


class Npm(Upstreams, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.sdk = self.upstream("sdk-ts")

    def pins(self, revision: str, resolved: str | None = None, declared: str | None = None) -> None:
        spec = f"github:lemonfiber/sdk-ts#{revision}"
        self.wrote(
            "package.json", json.dumps({"dependencies": {"@lemonfiber/sdk-ts": spec, "left-pad": "^1"}})
        )
        self.wrote(
            "package-lock.json",
            json.dumps(
                {
                    "packages": {
                        "": {"dependencies": {"@lemonfiber/sdk-ts": declared or spec}},
                        "node_modules/@lemonfiber/sdk-ts": {
                            "resolved": f"git+ssh://git@github.com/lemonfiber/sdk-ts.git#{resolved or revision}"
                        },
                    }
                }
            ),
        )

    def manifest(self, **fields) -> str:
        return json.dumps({"name": "@lemonfiber/sdk-ts", **fields})

    def test_a_file_the_package_ships_is_behind(self):
        first = self.commit(self.sdk, {"package.json": self.manifest(files=["dist"]), "dist/a.js": "1"})
        self.commit(self.sdk, {"dist/a.js": "2"})
        self.publish(self.sdk)
        self.pins(first)
        code, said = self.ran("npm")
        self.assertEqual(code, 1)
        self.assertIn("`dist/a.js`", said)
        self.assertIn("point @lemonfiber/sdk-ts at github:lemonfiber/sdk-ts#", said)

    def test_what_files_leaves_out_does_not_count_and_what_npm_always_packs_does(self):
        manifest = self.manifest(
            files=["dist", "!dist/*.map", "./lib/"], main="index.js", bin={"sdk": "bin/sdk"}
        )
        first = self.commit(self.sdk, {"package.json": manifest, "dist/a.map": "1", "src/x.ts": "1"})
        self.commit(self.sdk, {"dist/a.map": "2", "src/x.ts": "2"})
        self.publish(self.sdk)
        self.pins(first)
        self.assertEqual(self.ran("npm")[0], 0)

        self.commit(self.sdk, {"README.md": "read me"})
        self.publish(self.sdk)
        code, said = self.ran("npm")
        self.assertEqual(code, 1)
        self.assertIn("`README.md`", said)

    def test_the_main_entry_and_a_glob_count(self):
        manifest = self.manifest(files=["types/*.d.ts"], main="./index.js", bin="cli.js")
        first = self.commit(self.sdk, {"package.json": manifest, "index.js": "1", "types/a.d.ts": "1"})
        self.commit(self.sdk, {"index.js": "2", "types/a.d.ts": "2"})
        self.publish(self.sdk)
        self.pins(first)
        code, said = self.ran("npm")
        self.assertEqual(code, 1)
        self.assertIn("`index.js`", said)
        self.assertIn("`types/a.d.ts`", said)

    def test_a_package_built_at_install_counts_its_tree_but_its_ci_and_tests(self):
        first = self.commit(
            self.sdk, {"package.json": self.manifest(scripts={"prepare": "tsc"}), "src/a.ts": "1"}
        )
        self.commit(self.sdk, {".github/ci.yml": "x", "src/a.test.ts": "t"})
        self.publish(self.sdk)
        self.pins(first)
        self.assertEqual(self.ran("npm")[0], 0)

        self.commit(self.sdk, {"src/a.ts": "2"})
        self.publish(self.sdk)
        self.assertEqual(self.ran("npm")[0], 1)

    def test_a_manifest_naming_no_files_counts_every_path(self):
        first = self.commit(self.sdk, {"package.json": self.manifest(), "x": "1"})
        self.commit(self.sdk, {"x": "2"})
        self.publish(self.sdk)
        self.pins(first)
        self.assertEqual(self.ran("npm")[0], 1)

    def test_a_head_with_no_readable_manifest_counts_every_path(self):
        first = self.commit(self.sdk, {"package.json": "not json", "x": "1"})
        self.commit(self.sdk, {"x": "2"})
        self.publish(self.sdk)
        self.pins(first)
        self.assertEqual(self.ran("npm")[0], 1)

        self.commit(self.sdk, {"package.json": None, "x": "3"})
        self.publish(self.sdk)
        self.assertEqual(self.ran("npm")[0], 1)

    def test_a_lockfile_naming_another_revision_is_refused_even_when_the_pin_is_current(self):
        first = self.commit(self.sdk, {"package.json": self.manifest(), "x": "1"})
        self.publish(self.sdk)
        self.pins(first, resolved="e" * 40)
        code, said = self.ran("npm")
        self.assertEqual(code, 1)
        self.assertIn("The lockfile disagrees with the manifest on `@lemonfiber/sdk-ts`", said)
        self.assertIn("is current", said)

    def test_a_lockfile_copy_of_another_declaration_is_refused(self):
        first = self.commit(self.sdk, {"package.json": self.manifest(), "x": "1"})
        self.publish(self.sdk)
        self.pins(first, declared="github:lemonfiber/sdk-ts#" + "d" * 40)
        self.assertEqual(self.ran("npm")[0], 1)

    def test_a_specifier_without_a_revision_is_refused(self):
        self.commit(self.sdk, {"package.json": self.manifest()})
        self.publish(self.sdk)
        self.wrote(
            "package.json",
            json.dumps({"devDependencies": {"@lemonfiber/sdk-ts": "github:lemonfiber/sdk-ts"}}),
        )
        self.wrote("package-lock.json", json.dumps({}))
        code, said = self.ran("npm")
        self.assertEqual(code, 1)
        self.assertIn("It names `(nothing)`", said)


class Vendored(Upstreams, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.sdk = self.upstream("sdk-python")
        self.first = self.commit(
            self.sdk,
            {
                "src/lemonfiber/a.py": "a",
                "src/lemonfiber/b/c.py": "c",
                "scripts/one.py": "1",
                "README.md": "r",
            },
        )
        self.publish(self.sdk)

    def take(self, commit: str) -> None:
        self.wrote("vendor/lemonfiber/a.py", "a")
        self.wrote("vendor/lemonfiber/b/c.py", "c")
        self.wrote("vendor/lemonfiber/REVISION", commit + "\n")
        self.wrote("vendor/lemonfiber/__pycache__/a.pyc", "cache")
        self.wrote("tool/one.py", "1")

    def check(self, *more: str) -> tuple[int, str]:
        return self.ran(
            "vendored",
            "--upstream",
            "sdk-python",
            "--revision",
            "vendor/lemonfiber/REVISION",
            "--copy",
            "src/lemonfiber:vendor/lemonfiber",
            "--copy",
            "scripts/one.py:tool/one.py",
            "--remedy",
            "run `vendor take {head}`",
            *more,
        )

    def test_a_copy_that_is_its_commit_at_the_head_is_current(self):
        self.take(self.first)
        code, said = self.check()
        self.assertEqual(code, 0, said)

    def test_a_change_upstream_outside_the_copies_is_current(self):
        self.take(self.first)
        self.commit(self.sdk, {"README.md": "changed"})
        self.publish(self.sdk)
        self.assertEqual(self.check()[0], 0)

    def test_a_change_upstream_inside_a_copy_is_behind(self):
        self.take(self.first)
        head = self.commit(self.sdk, {"scripts/one.py": "2"})
        self.publish(self.sdk)
        code, said = self.check()
        self.assertEqual(code, 1)
        self.assertIn("`scripts/one.py`", said)
        self.assertIn(f"run `vendor take {head}`", said)

    def test_an_edited_copy_is_named_file_by_file(self):
        self.take(self.first)
        self.wrote("vendor/lemonfiber/a.py", "edited")
        self.wrote("vendor/lemonfiber/extra.py", "x")
        (self.here / "vendor/lemonfiber/b/c.py").unlink()
        self.wrote("tool/one.py", "edited")
        code, said = self.check()
        self.assertEqual(code, 1)
        self.assertIn("- vendor/lemonfiber/a.py differs", said)
        self.assertIn("- vendor/lemonfiber/extra.py is not in sdk-python", said)
        self.assertIn("- vendor/lemonfiber/b/c.py is missing", said)
        self.assertIn("- tool/one.py differs", said)

    def test_a_copy_that_is_not_there_is_every_file_missing(self):
        self.wrote("elsewhere/REVISION", self.first)
        code, said = self.ran(
            "vendored",
            "--upstream",
            "sdk-python",
            "--revision",
            "elsewhere/REVISION",
            "--copy",
            "src/lemonfiber:vendor/lemonfiber",
            "--remedy",
            "take",
        )
        self.assertEqual(code, 1)
        self.assertIn("- vendor/lemonfiber/a.py is missing", said)

    def test_a_path_the_commit_does_not_hold_is_named(self):
        self.take(self.first)
        code, said = self.ran(
            "vendored",
            "--upstream",
            "sdk-python",
            "--revision",
            "vendor/lemonfiber/REVISION",
            "--copy",
            "src/gone:vendor/lemonfiber",
            "--remedy",
            "take",
        )
        self.assertEqual(code, 1)
        self.assertIn("sdk-python " + self.first + " has no src/gone", said)

    def test_a_record_that_cannot_be_read_compares_nothing(self):
        code, said = self.check()
        self.assertEqual(code, 1)
        self.assertIn("could not be read, so the copy names no commit", said)

    def test_a_vendored_check_missing_what_it_needs_is_refused(self):
        code, said = self.ran("vendored", "--upstream", "sdk-python")
        self.assertEqual(code, 1)
        self.assertIn("vendored takes --upstream, --revision", said)

    def test_a_copy_that_is_not_from_and_to_is_refused(self):
        self.take(self.first)
        code, said = self.ran(
            "vendored",
            "--upstream",
            "sdk-python",
            "--revision",
            "vendor/lemonfiber/REVISION",
            "--copy",
            "src/lemonfiber",
            "--remedy",
            "take",
        )
        self.assertEqual(code, 1)
        self.assertIn("each --copy is FROM:TO", said)


class TheWorkflowStep(unittest.TestCase):
    """`upstream-drift.yml` hands the script what the caller wrote, one `--copy` per line."""

    def test_each_copy_line_is_one_argument_and_blank_lines_are_none(self):
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "scripts").mkdir()
        (root / "scripts" / "upstream_drift.py").write_text(
            "import json, sys\nprint(json.dumps(sys.argv[1:]))\n", encoding="utf-8"
        )
        workflow = yaml.safe_load(
            (
                pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/upstream-drift.yml"
            ).read_text(encoding="utf-8")
        )
        script = workflow["jobs"]["drift"]["steps"][-1]["run"]
        env = {
            "PATH": os.environ["PATH"],
            "LOCK": "vendored",
            "REMEDY": "take {head}",
            "UPSTREAM": "sdk-python",
            "REVISION": "v/REVISION",
            "COPIES": "  src/a:v/a\n\nscripts/b.py:t/b.py  \n",
            "TOOLING": str(root),
        }
        done = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(
            json.loads(done.stdout),
            [
                "vendored",
                "--remedy",
                "take {head}",
                "--upstream",
                "sdk-python",
                "--revision",
                "v/REVISION",
                "--copy",
                "src/a:v/a",
                "--copy",
                "scripts/b.py:t/b.py",
            ],
        )

        env.update(LOCK="npm", REMEDY="", UPSTREAM="", REVISION="", COPIES="")
        done = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(done.stdout), ["npm", "--remedy", ""])


class Clock(unittest.TestCase):
    def test_the_window_is_measured_from_now(self):
        self.assertAlmostEqual(upstream_drift.clock(), int(time.time()), delta=5)


class Summary(unittest.TestCase):
    def test_without_a_summary_file_it_only_prints(self):
        with (
            unittest.mock.patch.dict(os.environ, {}, clear=True),
            contextlib.redirect_stdout(io.StringIO()) as said,
        ):
            upstream_drift.say("one", "two")
        self.assertEqual(said.getvalue(), "one\ntwo\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
