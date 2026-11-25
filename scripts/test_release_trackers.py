#!/usr/bin/env python3
"""Coverage tests for the gate reading each repository's tracker.

They share the workspace and the in-process runner of
`test_release_train.py`, and live apart from it so that suite stays within the
size cap. Run:  python3 scripts/test_release_trackers.py
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate  # noqa: E402
from test_release_train import Workspace, run_main  # noqa: E402


class PerRepositoryTrackers(Workspace):
    """Each searched repository's status.toml is a tracker the gate reads — OPS-R74."""

    def tracker(self, path, body):
        p = pathlib.Path(path) / "status.toml"
        p.write_text(body, encoding="utf-8")

    def head_of(self, path):
        return subprocess.run(
            ["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()

    def test_a_done_row_in_any_searched_repository_is_done(self):
        self.repo("checkouts/lf", trailer="Spec: B1-R4")
        self.repo("checkouts/web", trailer="Spec: C1-R3")
        self.tracker(
            "checkouts/web",
            '[[requirement]]\nid = "C1-R3"\nstate = "done"\n'
            'evidence = ["f"]\n[[requirement]]\nid = "C1-R4"\nstate = "partial"\n',
        )
        self.manifest("0.1.0", goals=("C1-R3", "C1-R4"))
        args = [
            "--manifest",
            "70-operations/versions/0.1.0.toml",
            "--repo",
            "lf=checkouts/lf",
            "--repo",
            "web=checkouts/web",
        ]
        code, said = run_main(gate, args)
        self.assertEqual(code, 1)
        self.assertIn("lf: no tracker", said)
        self.assertIn("✓ C1-R3", said)
        self.assertIn("✗ C1-R4", said)

    def test_a_row_in_another_state_in_any_searched_repository_holds_it_open(self):
        self.repo("checkouts/lf", trailer="Spec: C1-R1, C1-R2, C1-R3")
        self.repo("checkouts/web", trailer="Spec: C1-R4")
        self.tracker(
            "checkouts/lf",
            '[[requirement]]\nid = "C1-R1"\nstate = "done"\nevidence = ["f"]\n'
            '[[requirement]]\nid = "C1-R2"\nstate = "done"\nevidence = ["f"]\n'
            '[[requirement]]\nid = "C1-R3"\nstate = "done"\nevidence = ["f"]\n',
        )
        self.tracker(
            "checkouts/web",
            '[[requirement]]\nid = "C1-R1"\nstate = "done"\nevidence = ["f"]\n'
            '[[requirement]]\nid = "C1-R2"\nstate = "partial"\n'
            '[[requirement]]\nid = "C1-R3"\nstate = "open"\n',
        )
        self.manifest("0.1.0", goals=("C1-R1", "C1-R2", "C1-R3"))
        args = ["--manifest", "70-operations/versions/0.1.0.toml", "--repo", "lf=checkouts/lf"]
        args += ["--repo", "web=checkouts/web"]
        code, said = run_main(gate, args)
        self.assertEqual(code, 1)
        self.assertRegex(said, r"✓ C1-R1 .*tracked-done=yes\n")
        self.assertRegex(said, r"✗ C1-R2 .*tracked-done=NO +held open by web\n")
        self.assertRegex(said, r"✗ C1-R3 .*tracked-done=NO +held open by web\n")
        self.assertIn("2 goal(s) unmet: C1-R2, C1-R3", said)
        code, said = run_main(gate, [*args, "--format", "json"])
        verdict = json.loads(said)
        self.assertEqual(code, 1)
        self.assertFalse(verdict["releasable"])
        self.assertEqual(
            [(g["id"], g["done"], g["held_in"]) for g in verdict["goals"]],
            [("C1-R1", True, []), ("C1-R2", False, ["web"]), ("C1-R3", False, ["web"])],
        )

    def test_a_markdown_tick_is_held_open_by_a_repository_tracker_too(self):
        self.repo("checkouts/web")
        self.tracker("checkouts/web", '[[requirement]]\nid = "B1-R4"\nstate = "partial"\n')
        with contextlib.redirect_stdout(io.StringIO()):
            rows = gate.trackers(gate.parse_repos(["web=checkouts/web"]))
        legacy = gate.done_ids(gate.within_cwd(self.status_file()))
        self.assertIn("B1-R4", legacy)
        done = gate.tracked_done(rows, legacy)
        self.assertNotIn("B1-R4", done)
        self.assertIn("C1-R3", done)
        self.assertEqual(gate.holders(rows), {"B1-R4": ["web"]})

    def test_a_row_naming_its_commit_is_checked_in_its_own_repository(self):
        self.repo("checkouts/lf", trailer="Spec: GOV-R12")
        self.repo("checkouts/web", trailer="Spec: GOV-R13")
        sha = self.head_of("checkouts/web")
        repos = gate.parse_repos(["lf=checkouts/lf", "web=checkouts/web"])
        self.tracker(
            "checkouts/web",
            f'[[requirement]]\nid = "C1-R3"\nstate = "done"\nevidence = ["f"]\nlanded = "{sha}"\n',
        )
        self.tracker(
            "checkouts/lf",
            '[[requirement]]\nid = "C1-R4"\nstate = "done"\n'
            f'evidence = ["f"]\nlanded = "{sha}"\n[[requirement]]\nid = "C1-R5"\n'
            'state = "partial"\nlanded = "{sha}"\n'.replace("{sha}", sha),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            landed, faults = gate.tracked_landed(gate.trackers(repos), repos)
        self.assertEqual(landed, {"C1-R3"})
        self.assertEqual(len(faults), 1)
        self.assertIn("lf records C1-R4 as landed", faults[0])

    def test_the_old_milestone_shape_is_left_to_the_markdown_reading(self):
        self.repo("checkouts/lf")
        self.tracker("checkouts/lf", '[[milestone]]\nname = "M1"\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rows = gate.trackers(gate.parse_repos(["lf=checkouts/lf"]))
        self.assertEqual(rows, [])

    def test_a_tracker_that_cannot_be_read_stops_the_gate(self):
        self.repo("checkouts/lf")
        self.tracker("checkouts/lf", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n')
        repos = gate.parse_repos(["lf=checkouts/lf"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            gate.trackers(repos)
        self.assertEqual(exit.exception.code, 2)
        self.assertIn("names no evidence", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
