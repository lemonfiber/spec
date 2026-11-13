#!/usr/bin/env python3
"""What the shared gitleaks check reads, and what reads the rest daily.

A pull request is judged by its base..head and a push by its before..after, so
a branch holding a fixture shaped like a key judges nobody else's change. The
range step runs here out of the committed `security.yml` over a real repository,
and the commits it names are listed with the `git log` gitleaks runs. The same
step in the generated `gates.yml` is checked to be the one handed to the scan,
with the range read from each event as a runner reads it. `gitleaks-history.yml`
reads every branch and tag of every repository on a schedule; its loop runs here
with `gh`, the clone and gitleaks stubbed.

Stdlib unittest plus PyYAML, as the coverage job installs.
Run:  python3 scripts/test_gitleaks_range.py
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gen_gates
from workflow_expression import evaluate

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"
SECURITY = WORKFLOWS / "security.yml"
HISTORY = WORKFLOWS / "gitleaks-history.yml"
RANGE = "The commits this event brings"
SCAN = "gitleaks (CLI)"
LOG = "--full-history --diff-filter=tuxdb"
ZERO = "0" * 40
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


def steps_of(workflow: pathlib.Path, job: str) -> list[dict]:
    read = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    return read["jobs"][job]["steps"]


def named(steps: list[dict], name: str) -> dict:
    return next(step for step in steps if step.get("name", "").endswith(name))


def git(where: pathlib.Path, *args: str) -> str:
    done = subprocess.run([*GIT, *args], cwd=where, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Range(unittest.TestCase):
    """The range step names the commits its event brings and no others."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.origin = self.root / "origin"
        self.origin.mkdir()
        git(self.origin, "init", "--quiet", "--initial-branch=main")
        self.first = self.commit("README.md")
        self.main = self.commit("main.txt")
        git(self.origin, "switch", "--quiet", "-c", "feat/fixture")
        self.fixture = self.commit("fixture.txt")
        git(self.origin, "switch", "--quiet", "-c", "feat/change", "main")
        self.change = self.commit("change.txt")
        self.later = self.commit("later.txt")
        git(self.origin, "switch", "--quiet", "main")
        self.work = self.root / "work"
        git(self.root, "clone", "--quiet", str(self.origin), str(self.work))
        git(self.work, "checkout", "--quiet", "--detach", self.later)

    def commit(self, path: str) -> str:
        (self.origin / path).write_text(path, encoding="utf-8")
        git(self.origin, "add", path)
        git(self.origin, "commit", "--quiet", "-m", path)
        return git(self.origin, "rev-parse", "HEAD")

    def opts(
        self, base="", head="", pushed="refs/pull/7/merge", default="main"
    ) -> subprocess.CompletedProcess:
        output = self.root / "output"
        output.write_text("", encoding="utf-8")
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.root),
            "BASE_SHA": base,
            "HEAD_SHA": head,
            "PUSHED": pushed,
            "DEFAULT_BRANCH": default,
            "GITHUB_OUTPUT": str(output),
        }
        script = named(steps_of(SECURITY, "gitleaks"), RANGE)["run"]
        done = subprocess.run(["bash", "-c", script], cwd=self.work, env=env, capture_output=True, text=True)
        done.said = output.read_text(encoding="utf-8")
        return done

    def read(self, **event) -> tuple[str, set[str]]:
        done = self.opts(**event)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        lines = done.said.splitlines()
        self.assertEqual(len(lines), 1, done.said)
        key, _, value = lines[0].partition("=")
        self.assertEqual(key, "log-opts")
        listed = git(self.work, "log", "-p", "-U0", "--format=%H", *value.split(" "))
        return value, {line for line in listed.splitlines() if re.fullmatch("[0-9a-f]{40}", line)}

    def test_a_pull_request_reads_its_base_to_its_head(self):
        value, commits = self.read(base=self.main, head=self.later)
        self.assertEqual(value, f"{LOG} {self.main}..{self.later}")
        self.assertEqual(commits, {self.change, self.later})

    def test_a_push_reads_its_before_to_its_after(self):
        value, commits = self.read(base=self.change, head=self.later, pushed="refs/heads/feat/change")
        self.assertEqual(value, f"{LOG} {self.change}..{self.later}")
        self.assertEqual(commits, {self.later})

    def test_a_branch_s_first_push_reads_what_the_default_branch_does_not_hold(self):
        value, commits = self.read(base=ZERO, head=self.later, pushed="refs/heads/feat/change")
        self.assertEqual(value, f"{LOG} {self.later} --not refs/remotes/origin/main")
        self.assertEqual(commits, {self.change, self.later})

    def test_a_before_the_checkout_lacks_reads_as_a_new_branch(self):
        _, commits = self.read(base="b" * 40, head=self.later, pushed="refs/heads/feat/change")
        self.assertEqual(commits, {self.change, self.later})

    def test_the_default_branch_s_first_push_reads_its_whole_history(self):
        value, commits = self.read(base=ZERO, head=self.main, pushed="refs/heads/main")
        self.assertEqual(value, f"{LOG} {self.main}")
        self.assertEqual(commits, {self.first, self.main})

    def test_no_default_branch_to_hold_against_reads_the_head_s_whole_history(self):
        _, commits = self.read(base=ZERO, head=self.later, pushed="refs/heads/feat/change", default="gone")
        self.assertEqual(commits, {self.first, self.main, self.change, self.later})

    def test_no_range_reads_every_branch_and_tag(self):
        value, commits = self.read()
        self.assertEqual(value, f"{LOG} --all")
        self.assertIn(self.fixture, commits)

    def test_no_range_reaches_a_branch_the_change_did_not_bring(self):
        for event in (
            {"base": self.main, "head": self.later},
            {"base": ZERO, "head": self.later, "pushed": "refs/heads/feat/change"},
        ):
            self.assertNotIn(self.fixture, self.read(**event)[1], event)

    def test_a_head_the_checkout_lacks_is_refused(self):
        done = self.opts(base=self.main, head="c" * 40)
        self.assertEqual(done.returncode, 1)
        self.assertIn("does not hold it", done.stdout)
        self.assertEqual(done.said, "")

    def test_a_value_that_is_no_commit_id_is_refused(self):
        for event in ({"base": "main", "head": self.later}, {"base": self.main, "head": "--all"}):
            done = self.opts(**event)
            self.assertEqual(done.returncode, 1, event)
            self.assertIn("is not a commit id", done.stdout)
            self.assertEqual(done.said, "")


class Wired(unittest.TestCase):
    """The scan reads the range, in the reusable and in the generated gates."""

    def test_the_scan_is_handed_the_range(self):
        steps = steps_of(SECURITY, "gitleaks")
        range_step, scan = named(steps, RANGE), named(steps, SCAN)
        self.assertLess(steps.index(range_step), steps.index(scan))
        self.assertEqual(scan["env"]["LOG_OPTS"], "${{ steps.range.outputs.log-opts }}")
        self.assertIn('git --no-banner --redact --exit-code 1 --log-opts="$LOG_OPTS" .', scan["run"])
        checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["fetch-depth"], 0)

    def test_gates_carries_the_range_into_the_scan(self):
        steps = yaml.safe_load(gen_gates.build())["jobs"]["gates"]["steps"]
        range_step = named(steps, f"security / gitleaks: {RANGE}")
        scan = named(steps, f"security / gitleaks: {SCAN}")
        self.assertEqual(range_step["run"], named(steps_of(SECURITY, "gitleaks"), RANGE)["run"])
        self.assertEqual(scan["env"]["LOG_OPTS"], f"${{{{ steps.{range_step['id']}.outputs.log-opts }}}}")
        self.assertIn(f"steps.{range_step['id']}.outcome != 'failure'", scan["if"])

    def test_each_event_names_its_own_range(self):
        env = named(steps_of(SECURITY, "gitleaks"), RANGE)["env"]
        events = {
            "pull_request": (
                {"pull_request": {"base": {"sha": "b1"}, "head": {"sha": "h1"}}, "before": "x", "after": "y"},
                ("b1", "h1"),
            ),
            "merge_group": ({"merge_group": {"base_sha": "b2", "head_sha": "h2"}}, ("b2", "h2")),
            "push": ({"before": "b3", "after": "h3"}, ("b3", "h3")),
            "workflow_dispatch": ({}, ("", "")),
        }
        for name, (event, (base, head)) in events.items():
            context = {"github": {"event_name": name, "event": event}}
            said = [evaluate(env[key][3:-2], context) or "" for key in ("BASE_SHA", "HEAD_SHA")]
            self.assertEqual(said, [base, head], name)


class History(unittest.TestCase):
    """Every repository's whole history is read on a schedule, with the pinned gitleaks."""

    def setUp(self):
        self.read = yaml.safe_load(HISTORY.read_text(encoding="utf-8"))
        self.steps = self.read["jobs"]["history"]["steps"]

    def test_it_runs_daily_and_on_demand(self):
        on = self.read[True]
        self.assertEqual(len(on["schedule"]), 1)
        self.assertEqual(len(on["schedule"][0]["cron"].split()), 5)
        self.assertEqual(on["schedule"][0]["cron"].split()[2:], ["*", "*", "*"])
        self.assertIn("workflow_dispatch", on)
        self.assertEqual(set(on), {"schedule", "workflow_dispatch"})

    def test_it_reads_the_gitleaks_security_yml_pins(self):
        fetch = named(self.steps, "The gitleaks security.yml pins")["run"]
        self.assertIn(".jobs.gitleaks.env.$1", fetch)
        self.assertIn(".github/workflows/security.yml", fetch)
        pinned = yaml.safe_load(SECURITY.read_text(encoding="utf-8"))["jobs"]["gitleaks"]["env"]
        for knob in ("GITLEAKS_VERSION", "GITLEAKS_SHA256"):
            self.assertIn(f"read_pin {knob}", fetch)
            self.assertNotIn(str(pinned[knob]), HISTORY.read_text(encoding="utf-8"))
        self.assertLess(fetch.index("sha256sum --check --strict"), fetch.index("tar xzf"))

    def test_it_reads_every_branch_and_tag(self):
        scan = named(self.steps, "Every repository's history")["run"]
        self.assertIn('"${RUNNER_TEMP}/gitleaks" git --no-banner --redact --exit-code 1 .', scan)
        self.assertNotIn("--log-opts", scan)
        self.assertNotIn("--depth", scan)
        self.assertNotIn("--single-branch", scan)

    def test_a_failure_tells_the_maintainers(self):
        told = self.read["jobs"]["told"]
        self.assertEqual(told["needs"], "history")
        self.assertEqual(told["if"], "always() && needs.history.result == 'failure'")
        self.assertEqual(told["uses"], "./.github/workflows/discord-notify.yml")


class Sweep(unittest.TestCase):
    """The history loop, with `gh`, the clone and gitleaks stubbed."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.remotes = self.root / "remotes"
        self.bin = self.root / "bin"
        self.temp = self.root / "temp"
        for directory in (self.remotes, self.bin, self.temp):
            directory.mkdir()
        real = shutil.which("git")
        self.stub(
            "git",
            f'if [ "$1" = clone ]; then exec {real} clone --quiet "$REMOTES/$(basename "$3" .git)" "$4"; fi\n'
            f'exec {real} "$@"\n',
        )
        self.stub("gh", 'printf "%s\\n" $LISTED\n')
        (self.temp / "gitleaks").write_text("#!/bin/sh\n! test -e LEAK\n", encoding="utf-8")
        (self.temp / "gitleaks").chmod(0o755)

    def stub(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
        path.chmod(0o755)

    def repository(self, name: str, *files: str) -> None:
        at = self.remotes / name
        at.mkdir()
        git(at, "init", "--quiet", "--initial-branch=main")
        for path in files:
            (at / path).write_text(path, encoding="utf-8")
            git(at, "add", path)
            git(at, "commit", "--quiet", "-m", path)

    def sweep(self, *listed: str) -> tuple[subprocess.CompletedProcess, str, str]:
        output, summary = self.root / "output", self.root / "summary"
        for path in (output, summary):
            path.write_text("", encoding="utf-8")
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.root),
            "REMOTES": str(self.remotes),
            "LISTED": " ".join(listed),
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "RUNNER_TEMP": str(self.temp),
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        script = named(steps_of(HISTORY, "history"), "Every repository's history")["run"]
        done = subprocess.run(["bash", "-c", script], cwd=self.root, env=env, capture_output=True, text=True)
        return done, output.read_text(encoding="utf-8"), summary.read_text(encoding="utf-8")

    def test_a_finding_names_its_repository(self):
        self.repository("clean", "README.md")
        self.repository("leaky", "README.md", "LEAK")
        self.repository("empty")
        done, output, summary = self.sweep("clean", "empty", "leaky")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(output, "red=true\n")
        self.assertIn("1 read clean.", summary)
        self.assertIn("- lemonfiber/leaky", summary)
        self.assertNotIn("lemonfiber/clean", summary)
        self.assertEqual(list((self.temp / "history").iterdir()), [])

    def test_every_history_clean_is_green(self):
        self.repository("one", "README.md")
        self.repository("two", "README.md")
        _, output, summary = self.sweep("one", "two")
        self.assertEqual(output, "red=false\n")
        self.assertIn("2 read clean.", summary)

    def test_a_repository_that_cannot_be_cloned_is_red(self):
        self.repository("one", "README.md")
        done, output, summary = self.sweep("one", "missing")
        self.assertEqual(output, "red=true\n")
        self.assertIn("- lemonfiber/missing (not cloned)", summary)
        self.assertIn("could not be cloned", done.stdout)

    def test_no_repository_listed_is_a_failure(self):
        done, output, _ = self.sweep()
        self.assertEqual(done.returncode, 1)
        self.assertIn("No repository was listed", done.stdout)
        self.assertEqual(output, "")

    def test_the_token_reaches_git_only_masked(self):
        self.repository("one", "README.md")
        done, _, _ = self.sweep("one")
        self.assertIn("::add-mask::", done.stdout)
        self.assertNotIn("x-access-token", done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
