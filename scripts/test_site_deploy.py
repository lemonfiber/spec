#!/usr/bin/env python3
"""`site-deploy.yml` publishes only from the default branch, and hands wrangler a configuration of its own.

Driven the way `test_tell.py` drives the notifier: each step's script is read out
of the committed YAML through a YAML parser and run with a stubbed `gh`.

Stdlib unittest plus PyYAML (the parser is the point).
Run:  python3 scripts/test_site_deploy.py
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "site-deploy.yml"

GH_STUB = """#!/bin/sh
printf '%s\\n' "${DEFAULT-main}"
"""


def step(job: str, name: str) -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return next(one["run"] for one in workflow["jobs"][job]["steps"] if one.get("name") == name)


class SiteDeploy(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "bin").mkdir()
        gh = self.root / "bin" / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        self.output = self.root / "output"
        self.output.touch()

    def run_step(self, job: str, name: str, **env: str) -> subprocess.CompletedProcess:
        base = {
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(self.root),
            "GITHUB_OUTPUT": str(self.output),
        }
        return subprocess.run(
            ["bash", "-c", step(job, name)], env={**base, **env}, capture_output=True, text=True, check=False
        )

    def authorised(self, **env: str) -> subprocess.CompletedProcess:
        return self.run_step(
            "authorised",
            "Only the default branch publishes",
            **{"GH_TOKEN": "t", "REPO": "lemonfiber/site", **env},
        )

    def test_the_default_branch_publishes_for_each_trigger_a_site_has(self):
        for event in ("push", "workflow_dispatch", "schedule", "repository_dispatch"):
            with self.subTest(event):
                self.assertEqual(self.authorised(EVENT=event, REF="refs/heads/main").returncode, 0)

    def test_a_pull_request_or_another_branch_publishes_nothing(self):
        refused = [
            {"EVENT": "pull_request", "REF": "refs/heads/main"},
            {"EVENT": "pull_request_target", "REF": "refs/heads/main"},
            {"EVENT": "workflow_dispatch", "REF": "refs/heads/feature"},
            {"EVENT": "push", "REF": "refs/tags/v1.0.0"},
            {"EVENT": "push", "REF": "refs/heads/main", "DEFAULT": ""},
        ]
        for env in refused:
            with self.subTest(env):
                self.assertEqual(self.authorised(**env).returncode, 1)

    def configured(self, **env: str) -> subprocess.CompletedProcess:
        asked = {"WORKER": "website-docs", "COMPATIBILITY": "2026-10-09", "NOT_FOUND": "404-page", **env}
        return self.run_step(
            "cloudflare", "The worker's configuration, from the caller's inputs alone", **asked
        )

    def test_the_configuration_names_the_assets_and_nothing_wrangler_would_run(self):
        done = self.configured()
        self.assertEqual(done.returncode, 0, done.stdout)
        written = json.loads((self.root / "worker" / "wrangler.json").read_text(encoding="utf-8"))
        self.assertEqual(
            written,
            {
                "name": "website-docs",
                "compatibility_date": "2026-10-09",
                "assets": {
                    "directory": "./dist",
                    "html_handling": "auto-trailing-slash",
                    "not_found_handling": "404-page",
                },
                "workers_dev": True,
                "preview_urls": False,
            },
        )
        self.assertNotIn("build", written)
        self.assertNotIn("main", written)
        self.assertIn(f"dir={self.root / 'worker'}", self.output.read_text(encoding="utf-8"))

    def test_an_input_outside_its_pattern_is_refused(self):
        for env in ({"WORKER": "Docs; rm"}, {"COMPATIBILITY": "today"}, {"NOT_FOUND": "build"}):
            with self.subTest(env):
                done = self.configured(**env)
                self.assertEqual(done.returncode, 1)
                self.assertFalse((self.root / "worker" / "wrangler.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
