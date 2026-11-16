#!/usr/bin/env python3
"""Every job of spec's workflows that reads the release App's key runs behind the
calling repository's `release` environment, which deploys only from main and `v*` tags.

A job that hands the key to a reusable workflow names no environment itself: the
reusable's own job does, and is held here like any other.

Run:  python3 scripts/test_release_key_environment.py
"""

from __future__ import annotations

import pathlib
import unittest

import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows"
KEY = "secrets.RELEASE_APP_KEY"
RELEASE = "release"
#: `tell` takes its environment from its caller, and is `release` where none is named.
CALLED = "${{ inputs.environment || 'release' }}"
#: `pin-only` reads the key only where its caller sets `check-source: app`, and is `release` there.
WHERE_APP = "${{ inputs.check-source == 'app' && 'release' || '' }}"


def readers() -> list[tuple[str, str, dict]]:
    """Each job, by workflow and name, that reads the key itself."""
    found = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        jobs = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("jobs", {}) or {}
        for name, job in jobs.items():
            if "uses" not in job and KEY in yaml.safe_dump(job):
                found.append((path.name, name, job))
    return found


class Readers(unittest.TestCase):
    def test_there_are_readers_to_hold(self):
        self.assertGreater(len(readers()), 20)

    def test_every_reader_runs_behind_the_release_environment(self):
        for workflow, name, job in readers():
            with self.subTest(f"{workflow} / {name}"):
                self.assertIn(job.get("environment"), (RELEASE, CALLED, WHERE_APP))

    def test_pin_only_is_release_wherever_it_reads_the_key(self):
        verdict = yaml.safe_load((WORKFLOWS / "pin-only.yml").read_text(encoding="utf-8"))
        job = verdict["jobs"]["pin-only"]
        self.assertEqual(job["environment"], WHERE_APP)
        [mint] = [step for step in job["steps"] if KEY in yaml.safe_dump(step)]
        self.assertEqual(mint["if"], "inputs.check-source == 'app'")

    def test_tell_is_release_where_its_caller_names_none(self):
        tell = yaml.safe_load((WORKFLOWS / "tell.yml").read_text(encoding="utf-8"))
        self.assertEqual(tell[True]["workflow_call"]["inputs"]["environment"]["default"], RELEASE)
        self.assertEqual(tell["jobs"]["tell"]["environment"], CALLED)


if __name__ == "__main__":
    unittest.main()
