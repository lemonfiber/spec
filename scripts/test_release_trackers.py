#!/usr/bin/env python3
"""Coverage tests for the gate reading each repository's tracker.

They share the workspace and the in-process runner of
`test_release_train.py`, and live apart from it so that suite stays within the
size cap. Run:  python3 scripts/test_release_trackers.py
"""
from __future__ import annotations

import contextlib
import io
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
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def test_a_done_row_in_any_searched_repository_is_done(self):
        self.repo("checkouts/lf", trailer="Spec: B1-R4")
        self.repo("checkouts/web", trailer="Spec: C1-R3")
        self.tracker("checkouts/web", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n'
                     'evidence = ["f"]\n[[requirement]]\nid = "C1-R4"\nstate = "partial"\n')
        self.manifest("0.1.0", goals=("C1-R3", "C1-R4"))
        args = ["--manifest", "70-operations/versions/0.1.0.toml",
                "--repo", "lf=checkouts/lf", "--repo", "web=checkouts/web"]
        code, said = run_main(gate, args)
        self.assertEqual(code, 1)
        self.assertIn("lf: no tracker", said)
        self.assertIn("✓ C1-R3", said)
        self.assertIn("✗ C1-R4", said)

    def test_a_row_naming_its_commit_is_checked_in_its_own_repository(self):
        self.repo("checkouts/lf", trailer="Spec: GOV-R12")
        self.repo("checkouts/web", trailer="Spec: GOV-R13")
        sha = self.head_of("checkouts/web")
        repos = gate.parse_repos(["lf=checkouts/lf", "web=checkouts/web"])
        self.tracker("checkouts/web", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n'
                     f'evidence = ["f"]\nlanded = "{sha}"\n')
        self.tracker("checkouts/lf", '[[requirement]]\nid = "C1-R4"\nstate = "done"\n'
                     f'evidence = ["f"]\nlanded = "{sha}"\n[[requirement]]\nid = "C1-R5"\n'
                     'state = "partial"\nlanded = "{sha}"\n'.replace("{sha}", sha))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            landed = gate.tracked_landed(gate.trackers(repos), repos)
        self.assertEqual(landed, {"C1-R3"})
        self.assertIn("lf records C1-R4 as landed", out.getvalue())

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
