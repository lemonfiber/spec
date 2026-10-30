#!/usr/bin/env python3
"""`first-party-bundle.yml`: only a push to main merging a train pin the release App
opened asks the catalogue to move a pin, judged before the job holding the key, which
runs behind the release environment — OPS-R86.

Run:  python3 scripts/test_first_party_bundle.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest

import yaml

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows"
WORKFLOW = yaml.safe_load((WORKFLOWS / "first-party-bundle.yml").read_text(encoding="utf-8"))
JOBS = WORKFLOW["jobs"]
BOT = "lemonfiber-release-train[bot]"


def step(job: str, named: str) -> dict:
    return next(one for one in JOBS[job]["steps"] if one.get("name") == named)


GH = """#!/bin/sh
printf '%s\\n' "$ANSWER"
"""


def author(answer: str) -> subprocess.CompletedProcess:
    """The author step's script, run with a `gh` answering the logins of the pull requests
    the pushed commit merged from the pin branch, as its jq filter would print them."""
    stub = pathlib.Path(tempfile.mkdtemp())
    (stub / "gh").write_text(GH, encoding="utf-8")
    (stub / "gh").chmod(0o755)
    output = stub / "output"
    done = subprocess.run(
        ["bash", "-c", step("author", "The release App opened the pin this commit merged")["run"]],
        env={
            **os.environ,
            "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}",
            "ANSWER": answer,
            "GH_TOKEN": "token",
            "REPOSITORY": "lemonfiber/plugin-sonarr",
            "BRANCH": "release/adapter-pin",
            "GITHUB_SHA": "a" * 40,
            "RELEASE_BOT": WORKFLOW["env"]["RELEASE_BOT"],
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    done.opened = output.read_text(encoding="utf-8") if output.exists() else ""
    return done


class Author(unittest.TestCase):
    def test_the_release_apps_login_is_named_once(self):
        self.assertEqual(WORKFLOW["env"]["RELEASE_BOT"], BOT)

    def test_only_a_push_to_main_in_the_organisation_is_judged(self):
        guard = JOBS["author"]["if"]
        for held in (
            "github.event_name == 'push'",
            "github.ref == 'refs/heads/main'",
            "github.repository_owner == 'lemonfiber'",
            "(inputs.pin == 'adapter' || inputs.pin == 'image')",
        ):
            self.assertIn(held, guard)

    def test_the_judge_holds_a_read_token_and_no_secret(self):
        job = JOBS["author"]
        self.assertEqual(job["permissions"], {"contents": "read", "pull-requests": "read"})
        self.assertNotIn("environment", job)
        text = yaml.safe_dump(job)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("create-github-app-token", text)

    def test_it_asks_only_about_the_pin_branch_this_commit_merged_here(self):
        script = step("author", "The release App opened the pin this commit merged")["run"]
        for held in (
            ".merged_at != null",
            '.merge_commit_sha == \\"${GITHUB_SHA}\\"',
            '.head.ref == \\"${BRANCH}\\"',
            '.head.repo.full_name == \\"${REPOSITORY}\\"',
        ):
            self.assertIn(held, script)
        self.assertEqual(
            step("author", "The release App opened the pin this commit merged")["env"]["BRANCH"],
            "release/${{ inputs.pin }}-pin",
        )

    def test_the_release_app_passes(self):
        done = author(BOT)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(done.opened, "opened=release\n")

    def test_a_commit_merging_no_pin_pins_nothing(self):
        done = author("")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.opened, "")
        self.assertIn("merges no release/adapter-pin", done.stdout)

    def test_anybody_else_is_refused_by_name(self):
        for login in ("lessevv", "dependabot[bot]", "lemonfiber-release-train", "x" + BOT, f"{BOT} lessevv"):
            with self.subTest(login):
                refused = author(login)
                self.assertEqual(refused.returncode, 1, login)
                self.assertEqual(refused.opened, "")
                self.assertIn(f"was opened by {login}, not {BOT}", refused.stdout)


class Bump(unittest.TestCase):
    def test_it_runs_only_on_the_judges_answer_behind_the_release_environment(self):
        self.assertEqual(JOBS["bump"]["needs"], "author")
        self.assertEqual(JOBS["bump"]["if"], "needs.author.outputs.opened == 'release'")
        self.assertEqual(JOBS["bump"]["environment"], "release")

    def test_every_job_reading_the_key_is_behind_the_release_environment(self):
        for name, job in JOBS.items():
            if "secrets.RELEASE_APP_KEY" in yaml.safe_dump(job):
                self.assertEqual(job.get("environment"), "release", name)

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

    def test_the_release_apps_login_is_held_to_the_tokens_own_app_before_it_asks(self):
        asked = step("bump", "Ask the catalogue to pin the merged revision")
        self.assertEqual(asked["env"]["BOT"], "${{ steps.token.outputs.app-slug }}[bot]")
        script = asked["run"]
        self.assertLess(script.index('[ "$RELEASE_BOT" = "$BOT" ]'), script.index("gh api"))

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
