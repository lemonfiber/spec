#!/usr/bin/env python3
"""`adapter-release.yml`: an adapter's image published from main and from train tags,
and its pin written by the release App behind the caller's `release` environment —
OPS-R90, OPS-R91.

Run:  python3 scripts/test_adapter_release.py
"""

from __future__ import annotations

import pathlib
import unittest

import yaml

WORKFLOW = yaml.safe_load(
    (pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/adapter-release.yml").read_text(
        encoding="utf-8"
    )
)
JOBS = WORKFLOW["jobs"]


class Called(unittest.TestCase):
    def test_it_is_called_with_the_release_apps_key_alone(self):
        called = WORKFLOW[True]["workflow_call"]
        self.assertEqual(set(called["secrets"]), {"RELEASE_APP_KEY"})
        self.assertNotIn("inputs", called)

    def test_only_a_push_in_the_organisation_publishes(self):
        self.assertEqual(
            JOBS["settle"]["if"], "github.event_name == 'push' && github.repository_owner == 'lemonfiber'"
        )
        for name in ("build", "publish", "pin"):
            self.assertIn("settle", JOBS[name]["needs"])

    def test_the_rolling_pull_request_is_spec_s_own_at_this_commit(self):
        self.assertEqual(JOBS["pull-request"]["uses"], "./.github/workflows/rolling-pull-request.yml")


class Pin(unittest.TestCase):
    def test_the_pin_waits_behind_the_release_environment(self):
        self.assertEqual(JOBS["pin"]["environment"], "release")

    def test_only_the_pin_mints_and_for_the_calling_repository_alone(self):
        minted = [
            (name, one)
            for name, job in JOBS.items()
            for one in job.get("steps", [])
            if one.get("uses", "").startswith("actions/create-github-app-token@")
        ]
        self.assertEqual([name for name, _ in minted], ["pin"])
        given = minted[0][1]["with"]
        self.assertEqual(given["repositories"], "${{ github.event.repository.name }}")
        self.assertEqual(
            {key for key in given if key.startswith("permission-")},
            {"permission-contents", "permission-pull-requests"},
        )

    def test_the_merge_of_a_pin_pins_nothing(self):
        script = next(one for one in JOBS["pin"]["steps"] if one.get("id") == "pinned")["run"]
        self.assertIn('.user.login == \\"${BOT}\\"', script)
        self.assertIn("merges a pin", script)

    def test_no_checkout_keeps_a_credential(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                if one.get("uses", "").startswith("actions/checkout@"):
                    self.assertIs(one["with"]["persist-credentials"], False)


class Interpolation(unittest.TestCase):
    def test_no_script_interpolates_an_expression(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                self.assertNotIn("${{", one.get("run", ""), one.get("name"))


if __name__ == "__main__":
    unittest.main()
