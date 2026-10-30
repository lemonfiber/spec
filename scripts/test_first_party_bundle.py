#!/usr/bin/env python3
"""`first-party-bundle.yml`: only a merged train pin the release App opened asks the
catalogue to move a pin, judged before any job holding a token — OPS-R86.

Run:  python3 scripts/test_first_party_bundle.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import unittest

import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows"
WORKFLOW = yaml.safe_load((WORKFLOWS / "first-party-bundle.yml").read_text(encoding="utf-8"))
JOBS = WORKFLOW["jobs"]
BOT = "lemonfiber-release-train[bot]"


def step(job: str, named: str) -> dict:
    return next(one for one in JOBS[job]["steps"] if one.get("name") == named)


def author(login: str) -> subprocess.CompletedProcess:
    """The author step's script, run as a pull request `login` opened."""
    return subprocess.run(
        ["bash", "-c", step("author", "The release App opened it")["run"]],
        env={
            **os.environ,
            "AUTHOR": login,
            "BRANCH": "release/adapter-pin",
            "RELEASE_BOT": WORKFLOW["env"]["RELEASE_BOT"],
            "GITHUB_OUTPUT": os.devnull,
        },
        capture_output=True,
        text=True,
        check=False,
    )


class Author(unittest.TestCase):
    def test_the_release_apps_login_is_named_once(self):
        self.assertEqual(WORKFLOW["env"]["RELEASE_BOT"], BOT)

    def test_only_a_merged_pin_of_the_named_kind_in_the_organisation_is_judged(self):
        guard = JOBS["author"]["if"]
        for held in (
            "github.event_name == 'pull_request'",
            "github.event.pull_request.merged == true",
            "(inputs.pin == 'adapter' || inputs.pin == 'image')",
            "github.event.pull_request.head.ref == format('release/{0}-pin', inputs.pin)",
            "github.event.pull_request.head.repo.full_name == github.repository",
            "github.repository_owner == 'lemonfiber'",
        ):
            self.assertIn(held, guard)

    def test_the_judge_holds_no_token_and_no_secret(self):
        job = JOBS["author"]
        self.assertEqual(job["permissions"], {})
        text = yaml.safe_dump(job)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("create-github-app-token", text)

    def test_the_release_app_passes(self):
        self.assertEqual(author(BOT).returncode, 0)

    def test_anybody_else_is_refused_by_name(self):
        for login in ("lessevv", "dependabot[bot]", "lemonfiber-release-train", "x" + BOT):
            refused = author(login)
            self.assertEqual(refused.returncode, 1, login)
            self.assertIn(f"was opened by {login}, not {BOT}", refused.stdout)


class Bump(unittest.TestCase):
    def test_it_runs_only_on_the_judges_answer(self):
        self.assertEqual(JOBS["bump"]["needs"], "author")
        self.assertEqual(JOBS["bump"]["if"], "needs.author.outputs.opened == 'release'")

    def test_only_bump_mints_and_for_the_catalogue_alone(self):
        minted = [
            (name, one)
            for name, job in JOBS.items()
            for one in job.get("steps", [])
            if one.get("uses", "").startswith("actions/create-github-app-token@")
        ]
        self.assertEqual([name for name, _ in minted], ["bump"])
        given = minted[0][1]["with"]
        self.assertEqual(given["repositories"], "lemonfiber-plugins")
        self.assertEqual({key for key in given if key.startswith("permission-")}, {"permission-actions"})

    def test_the_author_is_held_to_the_tokens_own_app_before_it_asks(self):
        asked = step("bump", "Ask the catalogue to pin the merged revision")
        self.assertEqual(asked["env"]["BOT"], "${{ steps.token.outputs.app-slug }}[bot]")
        script = asked["run"]
        self.assertLess(script.index('[ "$AUTHOR" = "$BOT" ]'), script.index("gh api"))

    def test_no_checkout_keeps_a_credential(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                if one.get("uses", "").startswith("actions/checkout@"):
                    self.assertIs(one["with"]["persist-credentials"], False)


class Branches(unittest.TestCase):
    """The pins it follows are the branches the train's pins are opened on."""

    def test_adapter_release_opens_the_adapter_pin(self):
        release = yaml.safe_load((WORKFLOWS / "adapter-release.yml").read_text(encoding="utf-8"))
        self.assertEqual(release["env"]["TAG_PIN_BRANCH"], "release/adapter-pin")

    def test_manifest_pin_opens_the_image_pin(self):
        self.assertIn("release/image-pin", (WORKFLOWS / "manifest-pin.yml").read_text(encoding="utf-8"))


class Interpolation(unittest.TestCase):
    def test_no_script_interpolates_an_expression(self):
        for job in JOBS.values():
            for one in job.get("steps", []):
                self.assertNotIn("${{", one.get("run", ""), one.get("name"))


if __name__ == "__main__":
    unittest.main()
