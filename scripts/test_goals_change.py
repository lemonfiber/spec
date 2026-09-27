#!/usr/bin/env python3
"""Coverage tests for check_goals_change.py — OPS-R31.

Each case is a real repository in a temporary directory with two commits, so
what is compared is what git answers rather than a stand-in for it. The gate is
shown refusing an unlabelled change to a staged version's goals and to a
released one's, passing the same change once labelled, passing over a planned
version and a new one, and refusing a comparison it could not make.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_goals_change.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_goals_change as gate

MANIFEST = """version = "{version}"
status = "{status}"
goals = [{goals}]
"""


def written(version: str, status: str, goals: list[str]) -> str:
    return MANIFEST.format(version=version, status=status, goals=", ".join(f'"{goal}"' for goal in goals))


class Repository:
    """A throwaway repository the gate is pointed at."""

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    def commit(self, files: dict[str, str | None]) -> str:
        for name, text in files.items():
            path = self.root / gate.VERSIONS / name
            if text is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "change")
        return self.git("rev-parse", "HEAD")


class GoalsChangeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repository(pathlib.Path(self.tmp.name))
        self.saved = gate.ROOT
        gate.ROOT = self.repo.root

    def tearDown(self) -> None:
        gate.ROOT = self.saved
        self.tmp.cleanup()

    def run_gate(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gate.main(list(argv))
        return code, out.getvalue()

    def two(self, before: dict[str, str | None], after: dict[str, str | None]) -> tuple[str, str]:
        return self.repo.commit(before), self.repo.commit(after)

    def test_an_unlabelled_change_to_a_staged_version_is_refused_and_named(self) -> None:
        base, head = self.two(
            {"0.17.0.toml": written("0.17.0", "staged", ["A-R1", "B-R2"])},
            {"0.17.0.toml": written("0.17.0", "staged", ["A-R1", "C-R3"])},
        )
        code, said = self.run_gate("--base", base, "--head", head)
        self.assertEqual(code, 1)
        self.assertIn("::error::the locked goals move — 0.17.0: +C-R3, -B-R2", said)
        self.assertIn("label this pull request `goals-change`", said)

    def test_the_label_lets_it_through_and_says_it_will_be_told(self) -> None:
        base, head = self.two(
            {"0.17.0.toml": written("0.17.0", "in_progress", ["A-R1"])},
            {"0.17.0.toml": written("0.17.0", "in_progress", ["A-R1", "C-R3"])},
        )
        code, said = self.run_gate("--base", base, "--head", head, "--labels", "documentation, goals-change")
        self.assertEqual(code, 0)
        self.assertIn("::notice::the locked goals move — 0.17.0: +C-R3", said)
        self.assertIn("the maintainer channel is told", said)

    def test_a_released_version_is_frozen_too(self) -> None:
        base, head = self.two(
            {"0.14.0.toml": written("0.14.0", "released", ["E1-R1", "E2-R1"])},
            {"0.14.0.toml": written("0.14.0", "released", ["E2-R1"])},
        )
        code, said = self.run_gate("--base", base, "--head", head, "--labels", "documentation")
        self.assertEqual(code, 1)
        self.assertIn("0.14.0: -E1-R1", said)

    def test_a_planned_version_moves_freely(self) -> None:
        base, head = self.two(
            {"0.18.0.toml": written("0.18.0", "planned", ["A-R1"])},
            {"0.18.0.toml": written("0.18.0", "planned", ["B-R1"])},
        )
        self.assertEqual(
            self.run_gate("--base", base, "--head", head),
            (0, "goals-change: no staged or released version's goals move here.\n"),
        )

    def test_a_manifest_with_no_status_reads_as_planned(self) -> None:
        base, head = self.two(
            {"0.18.0.toml": 'version = "0.18.0"\ngoals = ["A-R1"]\n'},
            {"0.18.0.toml": 'version = "0.18.0"\ngoals = ["B-R1"]\n'},
        )
        self.assertEqual(self.run_gate("--base", base, "--head", head)[0], 0)

    def test_staging_a_version_is_the_lock_and_not_a_change(self) -> None:
        base, head = self.two(
            {"README.md": "versions\n"},
            {"0.18.0.toml": written("0.18.0", "staged", ["A-R1"])},
        )
        self.assertEqual(self.run_gate("--base", base, "--head", head)[0], 0)

    def test_a_staged_version_whose_goals_hold_passes(self) -> None:
        base, head = self.two(
            {
                "0.17.0.toml": written("0.17.0", "staged", ["A-R1"]),
                "TEMPLATE.toml": written("x", "staged", ["A-R1"]),
            },
            {
                "0.17.0.toml": written("0.17.0", "releasable", ["A-R1"]),
                "TEMPLATE.toml": written("x", "staged", ["Z-R9"]),
            },
        )
        self.assertEqual(self.run_gate("--base", base, "--head", head)[0], 0)

    def test_a_deleted_manifest_takes_every_goal_out(self) -> None:
        base, head = self.two(
            {
                "0.17.0.toml": written("0.17.0", "staged", ["A-R1"]),
                "0.18.0.toml": written("0.18.0", "planned", []),
            },
            {"0.17.0.toml": None},
        )
        code, said = self.run_gate("--base", base, "--head", head)
        self.assertEqual(code, 1)
        self.assertIn("0.17.0: -A-R1", said)

    def test_the_version_falls_back_to_the_file_name(self) -> None:
        base, head = self.two(
            {"0.17.0.toml": 'status = "staged"\ngoals = ["A-R1"]\n'},
            {"0.17.0.toml": 'status = "staged"\ngoals = []\n'},
        )
        self.assertIn("0.17.0: -A-R1", self.run_gate("--base", base, "--head", head)[1])

    def test_the_summary_is_the_change_one_line_per_version_and_refuses_nothing(self) -> None:
        base, head = self.two(
            {
                "0.17.0.toml": written("0.17.0", "staged", ["A-R1"]),
                "0.16.0.toml": written("0.16.0", "released", ["B-R1"]),
            },
            {
                "0.17.0.toml": written("0.17.0", "staged", ["A-R1", "C-R3"]),
                "0.16.0.toml": written("0.16.0", "released", []),
            },
        )
        self.assertEqual(
            self.run_gate("--base", base, "--head", head, "--summary"), (0, "0.16.0: -B-R1\n0.17.0: +C-R3\n")
        )

    def test_a_revision_that_names_no_commit_is_refused(self) -> None:
        head = self.repo.commit({"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])})
        code, said = self.run_gate("--base", "0" * 40, "--head", head)
        self.assertEqual(code, 1)
        self.assertIn("names no commit here", said)

    def test_a_revision_git_could_read_as_an_option_never_reaches_it_as_one(self) -> None:
        head = self.repo.commit({"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])})
        for said in ("--output=/tmp/x", "-p", "", "a b", "HEAD;true"):
            with self.subTest(said=said):
                code, out = self.run_gate(f"--base={said}", "--head", head)
                self.assertEqual(code, 1)
                self.assertIn("names no commit here", out)

    def test_a_revision_is_resolved_to_the_commit_it_names(self) -> None:
        base, head = self.two(
            {"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])},
            {"0.17.0.toml": written("0.17.0", "staged", ["A-R1", "C-R3"])},
        )
        self.assertEqual(gate.commit(f"{head}^1"), base)
        self.assertEqual(gate.commit("main"), head)

    def test_a_manifest_that_is_not_toml_is_refused(self) -> None:
        base, head = self.two(
            {"0.17.0.toml": "status = \n"},
            {"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])},
        )
        code, said = self.run_gate("--base", base, "--head", head)
        self.assertEqual(code, 1)
        self.assertIn("is not TOML", said)

    def test_a_manifest_a_commit_does_not_have_reads_as_none(self) -> None:
        head = self.repo.commit({"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])})
        self.assertIsNone(gate.manifest(head, f"{gate.VERSIONS}/0.99.0.toml"))

    def refusing(self, first: str, second: str | None = None) -> None:
        real = gate._git

        def refused(*args: str, given: str | None = None) -> subprocess.CompletedProcess[str]:
            if args[0] == first and (second is None or args[1] == second):
                return subprocess.CompletedProcess(args, 128, "", "fatal: refused")
            return real(*args, given=given)

        gate._git = refused
        self.addCleanup(setattr, gate, "_git", real)

    def test_a_git_that_will_not_resolve_is_a_commit_named_nowhere(self) -> None:
        self.refusing("cat-file", "--batch-check")
        with self.assertRaisesRegex(gate.Unreadable, "names no commit"):
            gate.commit("HEAD")

    def test_a_comparison_git_would_not_make_is_refused(self) -> None:
        base, head = self.two({"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])}, {})
        self.refusing("diff")
        code, said = self.run_gate("--base", base, "--head", head)
        self.assertEqual(code, 1)
        self.assertIn("::error::git could not compare", said)

    def test_a_blob_git_would_not_show_is_refused(self) -> None:
        head = self.repo.commit({"0.17.0.toml": written("0.17.0", "staged", ["A-R1"])})
        self.refusing("cat-file", "blob")
        with self.assertRaisesRegex(gate.Unreadable, "could not read"):
            gate.manifest(head, f"{gate.VERSIONS}/0.17.0.toml")


if __name__ == "__main__":
    unittest.main()
