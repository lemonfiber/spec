#!/usr/bin/env python3
"""What `gen_gates.py` writes, and what the workflow it writes does when it runs.

Two questions, and the second is the one that matters. The first is whether the
generator carries each check's steps across and refuses what it cannot carry.
The second is whether the generated jobs behave as the separate jobs did: a
check's failing step stops that check's later steps and no other check's, a step
its reusable lets fail stops nothing, a check the caller skips is skipped, a
check that reported nothing fails `gates`, and every verdict reaches the run's
summary (Q-R82).

The second is answered by running the generated file: each step's condition is
evaluated with `workflow_expression`, each step is given the outcome a case
asks for, the verdicts are read from the expressions the file holds, and the
plan and verdict scripts run as written.

Stdlib unittest plus PyYAML, as the coverage job installs.
Run:  python3 scripts/test_gen_gates.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gen_gates
from workflow_expression import decides, evaluate

REPO = "lemonfiber/core"
HEAD = "a" * 40


def generated() -> dict:
    return yaml.safe_load(gen_gates.build())


def context(event_name="pull_request", head_repo=REPO, inputs=None, steps=None, needs=None) -> dict:
    event = {}
    if event_name == "pull_request":
        event = {"pull_request": {"head": {"repo": {"full_name": head_repo}, "sha": HEAD}, "number": 7}}
    return {
        "github": {"event_name": event_name, "repository": REPO, "event": event, "token": "t", "sha": HEAD},
        "inputs": {"checks": " ".join(dict.fromkeys(c.group for c in gen_gates.CHECKS)),
                   "skip": "", **(inputs or {})},
        "steps": steps or {},
        "needs": needs or {},
        "env": {},
    }


def substitute(text: str, ctx: dict) -> str:
    """Every `${{ }}` in a string replaced by its value, as a runner does."""

    def swap(match: re.Match) -> str:
        value = evaluate(match.group(1), ctx)
        if value is None:
            return ""
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    return re.sub(r"\$\{\{(.*?)\}\}", swap, text)


class Runner:
    """Runs the generated jobs' conditions: which steps start, and what each check concludes."""

    def __init__(self, failing=(), ctx_args=None, plan=None, gates_outcome="success"):
        self.workflow = generated()
        self.failing = set(failing)
        self.ctx_args = ctx_args or {}
        self.plan = plan
        self.gates_outcome = gates_outcome

    def plan_outputs(self, ctx: dict) -> dict:
        if self.plan is not None:
            return self.plan
        listed = ctx["inputs"]["checks"].split()
        skipped = ctx["inputs"]["skip"].split()
        groups = dict.fromkeys(c.group for c in gen_gates.CHECKS)
        return {g: "true" if g in listed and g not in skipped else "false" for g in groups}

    def job(self, name: str, ctx: dict) -> tuple[dict, list[str]]:
        started = []
        for step in self.workflow["jobs"][name]["steps"]:
            sid = step.get("id")
            if sid == "plan":
                ctx["steps"]["plan"] = {"outputs": self.plan_outputs(ctx), "outcome": "success"}
                continue
            if "if" in step and not decides(step["if"], ctx):
                if sid:
                    ctx["steps"][sid] = {"outcome": "skipped", "outputs": {}}
                continue
            if sid is None:
                continue
            started.append(sid)
            outcome = "failure" if sid in self.failing else "success"
            outputs = {"status": "1" if sid in self.failing else "0", "reason": "r",
                       "needed": "true", "said": "s", "citation": "needed"}
            ctx["steps"][sid] = {"outcome": outcome, "outputs": outputs}
        return ctx, started

    def run(self) -> tuple[dict, list[str], list[str]]:
        """The verdicts `gates` holds itself to, the steps it ran, and the steps `report` ran."""
        ctx = context(**self.ctx_args)
        ctx, here = self.job("gates", ctx)
        held = self.workflow["jobs"]["gates"]["steps"][-1]
        verdicts = json.loads(substitute(held["env"]["VERDICTS"], ctx))
        outputs = {k: substitute(v, ctx) for k, v in self.workflow["jobs"]["gates"]["outputs"].items()}
        if self.gates_outcome == "cancelled":
            outputs = {}
        report = context(**self.ctx_args)
        report["needs"] = {"gates": {"outputs": outputs, "result": self.gates_outcome}}
        status = "success" if self.gates_outcome == "success" else self.gates_outcome
        if not decides(self.workflow["jobs"]["report"]["if"], report, status=status):
            return verdicts, here, []
        report, there = self.job("report", report)
        return verdicts, here, there


def verdict_checks() -> list:
    return [c for c in gen_gates.CHECKS if c.kind == gen_gates.VERDICT]


class Generation(unittest.TestCase):
    def test_no_step_writes_a_verdict(self):
        held = json.loads(generated()["jobs"]["gates"]["steps"][-1]["env"]["VERDICTS"])
        for check in verdict_checks():
            said = held[gen_gates.slug(check)]
            # The plan runs first, before any step that reads a pull request's
            # files, and is the one step whose output a verdict may read.
            self.assertEqual(set(re.findall(r"steps\.([\w-]+)\.outputs", said)), {"plan"}, check)
            self.assertIn(".outcome", said, check)

    def test_only_verdicts_are_held(self):
        held = json.loads(generated()["jobs"]["gates"]["steps"][-1]["env"]["VERDICTS"])
        self.assertEqual(list(held), [gen_gates.slug(c) for c in verdict_checks()])
        self.assertNotIn("explain--detect", held)

    def test_gates_holds_no_secret_and_writes_nothing(self):
        workflow = generated()
        self.assertNotIn("secrets", workflow[True]["workflow_call"])
        self.assertNotIn("secrets.", gen_gates.build())
        self.assertEqual(workflow["jobs"]["gates"]["permissions"], {"contents": "read", "pull-requests": "read"})
        self.assertEqual(workflow["permissions"], {"contents": "read", "pull-requests": "read"})

    def test_the_committed_file_is_what_the_reusables_say(self):
        self.assertEqual(gen_gates.OUTPUT.read_text(encoding="utf-8"), gen_gates.build())

    def test_two_jobs_and_the_permissions_each_holds(self):
        jobs = generated()["jobs"]
        self.assertEqual(list(jobs), ["gates", "report"])
        self.assertEqual(jobs["report"]["permissions"],
                         {"contents": "read", "pull-requests": "write", "issues": "write"})
        self.assertEqual(jobs["report"]["needs"], "gates")

    def test_no_check_is_published_as_a_check_run_of_its_own(self):
        # One context, `gates / gates`, is what a branch requires (Q-R82).
        text = gen_gates.build()
        self.assertNotIn("check-runs", text)
        self.assertNotIn("checks: write", text)

    def test_no_third_party_action_runs_beside_the_write_token(self):
        for step in generated()["jobs"]["report"]["steps"]:
            uses = step.get("uses", "")
            self.assertTrue(uses == "" or uses.startswith("actions/"), uses)

    def test_a_consumer_runs_only_spec_s_scripts_at_this_workflow_s_commit(self):
        # Every script a consumer runs is spec's, from the commit gates.yml was
        # called at, and never one of the canonical spec's, which is read as data.
        # The one other reader a step may pick is spec's own, in a branch taken
        # where the repository is lemonfiber/spec, which the plan refuses before
        # any step runs. report's workspace holds spec at main and nothing else.
        spec_branch = re.compile(r'^if \[ "\$(REPO|GITHUB_REPOSITORY)" = "lemonfiber/spec" \]; then$')
        for job in generated()["jobs"].values():
            for step in job["steps"]:
                readers: set[str] = set()
                in_spec = False
                for line in (raw.strip() for raw in step.get("run", "").splitlines()):
                    if spec_branch.match(line):
                        in_spec = True
                        continue
                    if in_spec:
                        in_spec = not re.match(r"(else|elif|fi)\b", line)
                        continue
                    assigned = re.match(r"(\w+)=[\"']?([^\"'\s]*)", line)
                    if assigned and ("scripts" in assigned[2] or "canonical" in assigned[2]):
                        self.assertTrue(assigned[2].startswith((".spec-canonical", ".spec-tooling")),
                                        (step["id"], line))
                        if assigned[2].startswith(".spec-tooling"):
                            readers.add(assigned[1])
                    ran = re.search(r"python3 [\"']?([^\"'\s]+)", line)
                    if not ran or ran[1] in ("-", "-c"):
                        continue
                    said = ran[1]
                    variable = re.match(r"\$\{?(\w+)", said)
                    if variable:
                        self.assertIn(variable[1], readers, (step["id"], line))
                    else:
                        self.assertTrue(said.startswith((".spec-tooling/", "scripts/")), (step["id"], line))

    def test_spec_s_scripts_are_checked_out_at_the_commit_gates_was_called_at(self):
        # So a caller pinned at a revision runs that revision's scripts, with the
        # arguments that revision's steps pass them.
        tooling = [step for job in generated()["jobs"].values() for step in job["steps"]
                   if step.get("with", {}).get("path") == ".spec-tooling"]
        self.assertTrue(tooling)
        for step in tooling:
            self.assertEqual(step["with"]["repository"], "lemonfiber/spec", step["id"])
            self.assertEqual(step["with"]["ref"], "${{ job.workflow_sha }}", step["id"])

    def test_gates_runs_only_actions_that_read_the_tree_as_data(self):
        seen: list[str] = []
        for step in generated()["jobs"]["gates"]["steps"]:
            action = step.get("uses", "").split("@")[0]
            if action:
                self.assertIn(action, {**gen_gates.INERT, **gen_gates.GUARDED}, step["id"])
            seen.append(action or step.get("id", ""))
        for action, guard in gen_gates.GUARDED.items():
            lint = seen.index(action)
            self.assertTrue(seen[lint - 1].endswith(f"--{guard}"), seen[lint - 1])

    def test_no_script_carries_an_expression(self):
        for job in generated()["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("${{", step.get("run", ""), step.get("id"))

    def test_the_scanner_runs_shut_in_and_builds_nothing(self):
        osv = next(s for s in generated()["jobs"]["gates"]["steps"] if s["id"] == "security--osv-scanner--1")
        words = osv["run"].split("docker run", 1)[1].split()
        self.assertNotIn("uses", osv)
        for word in ("--no-call-analysis=all", "--cap-drop", "no-new-privileges", '"${GITHUB_WORKSPACE}:/src:ro"'):
            self.assertIn(word, words)
        self.assertFalse([w for w in words if w == "-e" or w.startswith(("--env", "--privileged", "--network=host", "--mount"))], words)
        self.assertEqual([w for w in words if w.startswith(("--volume", "-v"))], ["--volume"])
        image = osv["env"]["OSV_IMAGE"]
        self.assertRegex(image, r"^ghcr\.io/google/osv-scanner-action:v[0-9.]+@sha256:[0-9a-f]{64}$")
        self.assertIn(f":v{osv['env']['OSV_VERSION']}@", image)

    def test_each_hand_fetched_scanner_is_watched_by_one_script(self):
        steps = generated()["jobs"]["gates"]["steps"]
        watches = [s for s in steps if s["name"].endswith("is not far behind the latest release")]
        self.assertEqual({s["env"]["KNOB"] for s in watches}, {"GITLEAKS_VERSION", "OSV_VERSION"})
        self.assertEqual(len({s["run"] for s in watches}), 1)
        for watch in watches:
            self.assertIn(watch["env"]["KNOB"], watch["env"])

    def test_every_checkout_drops_its_credentials(self):
        for job in generated()["jobs"].values():
            for step in job["steps"]:
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertIs(step.get("with", {}).get("persist-credentials"), False, step["id"])

    def test_every_source_step_is_carried_once(self):
        workflow = generated()
        carried = [s for job in workflow["jobs"].values() for s in job["steps"]]
        for check in gen_gates.CHECKS:
            if check.kind == gen_gates.EXPLAIN:
                continue
            read = yaml.safe_load((gen_gates.WORKFLOWS / check.source).read_text(encoding="utf-8"))
            for index, step in enumerate(read["jobs"][check.job]["steps"]):
                sid = f"{gen_gates.slug(check)}--{step.get('id', index)}"
                found = [s for s in carried if s.get("id") == sid]
                self.assertEqual(len(found), 1, sid)
                if "uses" in step:
                    self.assertEqual(found[0]["uses"], step["uses"])

    def test_each_explainer_is_inlined_into_report_with_what_it_passed(self):
        report = {s["id"]: s for s in generated()["jobs"]["report"]["steps"]}
        citation = report["explain--citation--0"]
        self.assertEqual(citation["env"]["CHECK"], "citation-gate")
        self.assertIn("needs.gates.outputs.explain--detect--out--suggest", citation["env"]["BODY"])
        self.assertIn("needs.gates.outputs.explain--detect--out--citation", citation["env"]["NEEDED"])
        self.assertIn("github.event_name == 'pull_request'", citation["if"])
        squash = report["squash-message--explain--0"]
        self.assertIn("needs.gates.outputs.squash-message--squash-message--out--said", squash["env"]["BODY"])
        self.assertIn("needs.gates.outputs.squash-message--squash-message--out--needed", squash["if"])

    def test_a_jobs_outputs_are_carried_out_of_gates(self):
        outputs = generated()["jobs"]["gates"]["outputs"]
        self.assertEqual(outputs["explain--detect--out--citation"], "${{ steps.explain--detect--d.outputs.citation }}")
        self.assertEqual(outputs["squash-message--squash-message--out--needed"],
                         "${{ steps.squash-message--squash-message--check.outputs.needed }}")

    def test_each_pin_keeps_the_version_its_reusable_names(self):
        for line in gen_gates.build().splitlines():
            if re.search(r"uses: \S+@[0-9a-f]{40}", line):
                self.assertRegex(line, r"# \S")

    def test_each_check_starts_from_an_empty_workspace(self):
        steps = [s for job in generated()["jobs"].values() for s in job["steps"]]
        ids = [s.get("id") for s in steps]
        for check in gen_gates.CHECKS:
            if check.kind == gen_gates.EXPLAIN:
                continue
            base = gen_gates.slug(check)
            first = next(i for i, sid in enumerate(ids) if sid and sid.startswith(base + "--") and sid != base + "--fresh")
            self.assertEqual(ids[first - 1], base + "--fresh", check)
            self.assertEqual(steps[first - 1]["run"], 'find "$GITHUB_WORKSPACE" -mindepth 1 -delete')

    def test_a_step_that_can_fail_its_check_is_in_its_verdict(self):
        held = json.loads(generated()["jobs"]["gates"]["steps"][-1]["env"]["VERDICTS"])
        self.assertIn("steps.spec-check--spec-check--0.outcome == 'failure'", held["spec-check--spec-check"])
        self.assertIn("steps.hygiene--typos--1.outcome == 'failure'", held["hygiene--typos"])

    def test_a_step_its_reusable_lets_fail_is_not_in_its_verdict(self):
        held = json.loads(generated()["jobs"]["gates"]["steps"][-1]["env"]["VERDICTS"])
        self.assertNotIn("spec-check--spec-check--citation.outcome", held["spec-check--spec-check"])

    def test_the_line_cap_reads_the_sources_the_generator_reads(self):
        import generated

        entry = generated.owner_of(".github/workflows/gates.yml")
        self.assertIsNotNone(entry)
        read = {f".github/workflows/{check.source}" for check in gen_gates.CHECKS}
        read.add(".github/workflows/explain-check.yml")
        self.assertEqual(set(entry.sources), read)
        self.assertEqual(len(entry.sources), len(read))

    def test_the_header_names_the_generator(self):
        self.assertIn("GENERATED by scripts/gen_gates.py", gen_gates.build()[:400])


class Behaviour(unittest.TestCase):
    def test_everything_passing_holds_every_verdict_green(self):
        verdicts, here, there = Runner().run()
        self.assertEqual(set(verdicts.values()), {"success"})
        self.assertEqual(len(verdicts), len(verdict_checks()))
        self.assertIn("hygiene--typos--1", here)
        self.assertIn("explain--detect--d", here)
        self.assertIn("labeler--label--0", there)
        self.assertIn("explain--citation--0", there)
        # Nothing to close where every citation resolved.
        self.assertNotIn("spec-check--spec-check--7", there)

    def test_a_failing_step_fails_its_check_and_stops_its_later_steps_only(self):
        verdicts, here, _ = Runner(failing={"hygiene--links--0"}).run()
        self.assertEqual(verdicts["hygiene--links"], "failure")
        self.assertNotIn("hygiene--links--1", here)
        self.assertIn("hygiene--markdown--0", here)
        others = {k: v for k, v in verdicts.items() if k != "hygiene--links"}
        self.assertEqual(set(others.values()), {"success"})

    def test_a_failing_detector_fails_no_verdict(self):
        verdicts, _, _ = Runner(failing={"explain--detect--d"}).run()
        self.assertEqual(set(verdicts.values()), {"success"})

    def test_a_step_its_reusable_lets_fail_stops_nothing(self):
        _, here, there = Runner(failing={"spec-check--spec-check--citation"}).run()
        self.assertIn("spec-check--spec-check--8", here)
        # The citation's own refusal comes from the step after it, as before.
        self.assertIn("spec-check--spec-check--7", there)

    def test_the_closing_step_waits_for_the_steps_before_it(self):
        _, _, there = Runner(failing={"spec-check--spec-check--3", "spec-check--spec-check--citation"}).run()
        self.assertNotIn("spec-check--spec-check--7", there)

    def test_an_actor_failing_fails_no_verdict(self):
        verdicts, _, there = Runner(failing={"goals--classify--1"}).run()
        self.assertEqual(set(verdicts.values()), {"success"})
        self.assertNotIn("goals--classify--2", there)

    def test_a_skipped_check_is_held_as_skipped_and_runs_nothing(self):
        verdicts, here, there = Runner(ctx_args={"inputs": {"skip": "labeler spec-check"}}).run()
        self.assertEqual(verdicts["spec-check--spec-check"], "skipped")
        self.assertFalse([s for s in here + there if s.startswith(("labeler", "spec-check"))])

    def test_a_reusables_own_job_condition_skips_its_check(self):
        # goals classifies only a pull request whose head is here, so a push skips it.
        _, _, there = Runner(ctx_args={"event_name": "push"}).run()
        self.assertFalse([s for s in there if s.startswith(("goals", "explain"))])

    def test_a_fork_pull_request_is_judged_and_nothing_is_written(self):
        verdicts, here, there = Runner(ctx_args={"head_repo": "someone/core"}).run()
        self.assertTrue(verdicts)
        self.assertIn("dco--dco--1", here)
        self.assertEqual(there, [])

    def test_a_plan_that_refused_fails_every_verdict(self):
        verdicts, here, _ = Runner(plan={}).run()
        self.assertEqual(len(verdicts), len(verdict_checks()))
        for key, said in verdicts.items():
            self.assertEqual(said, gen_gates.UNREPORTED, key)
        self.assertFalse([s for s in here if not s.endswith("--fresh")])

    def test_report_starts_for_no_fork_and_after_a_failed_gates(self):
        said = generated()["jobs"]["report"]["if"]
        self.assertFalse(decides(said, context(head_repo="someone/core")))
        self.assertTrue(decides(said, context()))
        self.assertTrue(decides(said, context(), status="failure"))
        self.assertTrue(decides(said, context(event_name="push")))
        self.assertFalse(decides(said, context(), status="cancelled"))


def bash(script: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], env={**os.environ, **env},
                          capture_output=True, text=True, check=False)


class Scripts(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "output"
        self.out.write_text("")
        self.summary = self.tmp / "summary.md"
        self.summary.write_text("")

    def outputs(self) -> dict:
        return dict(line.split("=", 1) for line in self.out.read_text().splitlines())

    def test_the_plan_runs_what_is_listed_and_not_skipped(self):
        said = bash(gen_gates.PLAN, {"KNOWN": "a b c", "CHECKS": "a b", "SKIP": "b",
                                     "REPO": REPO, "EVENT": "pull_request",
                                     "GITHUB_OUTPUT": str(self.out)})
        self.assertEqual(said.returncode, 0, said.stdout + said.stderr)
        self.assertEqual(self.outputs(), {"a": "true", "b": "false", "c": "false"})

    def test_the_plan_refuses_a_name_that_is_no_check(self):
        said = bash(gen_gates.PLAN, {"KNOWN": "a b", "CHECKS": "a sanity", "SKIP": "",
                                     "REPO": REPO, "EVENT": "push",
                                     "GITHUB_OUTPUT": str(self.out)})
        self.assertEqual(said.returncode, 1)
        self.assertIn("sanity is not one of the shared gates", said.stdout)

    def test_the_plan_refuses_the_spec_repository(self):
        said = bash(gen_gates.PLAN, {"KNOWN": "a", "CHECKS": "a", "SKIP": "", "REPO": "lemonfiber/spec",
                                     "EVENT": "pull_request", "GITHUB_OUTPUT": str(self.out)})
        self.assertEqual(said.returncode, 1)
        self.assertIn("runs its gates as its own workflows", said.stdout)
        self.assertEqual(self.out.read_text(), "")

    def test_the_plan_refuses_an_event_that_is_not_its_callers(self):
        for event in ("pull_request_target", "workflow_run", "issue_comment"):
            said = bash(gen_gates.PLAN, {"KNOWN": "a", "CHECKS": "a", "SKIP": "", "REPO": REPO,
                                         "EVENT": event, "GITHUB_OUTPUT": str(self.out)})
            self.assertEqual(said.returncode, 1, event)
            self.assertIn(f"not {event}", said.stdout)

    def held(self, verdicts: dict) -> subprocess.CompletedProcess:
        return bash(gen_gates.HELD, {"VERDICTS": json.dumps(verdicts),
                                     "GITHUB_STEP_SUMMARY": str(self.summary)})

    def test_a_failure_fails_the_job_and_every_result_is_in_the_summary(self):
        said = self.held({"x--y": "failure", "z--w": "success", "a--b": "skipped"})
        self.assertEqual(said.returncode, 1)
        self.assertIn("x / y failed", said.stdout)
        summary = self.summary.read_text()
        for row in ("| x / y | failure |", "| z / w | success |", "| a / b | skipped |"):
            self.assertIn(row, summary)

    def test_the_verdicts_pass_when_nothing_failed(self):
        self.assertEqual(self.held({"x--y": "skipped", "x--z": "success"}).returncode, 0)

    def test_a_check_with_no_conclusion_fails_the_job(self):
        for conclusion in (gen_gates.UNREPORTED, ""):
            said = self.held({"x--y": "success", "x--z": conclusion})
            self.assertEqual(said.returncode, 1, conclusion)
            self.assertIn("x / z failed", said.stdout)
            self.assertIn("| x / z | did not report |", self.summary.read_text())


class Refusals(unittest.TestCase):
    """What the generator will not carry, each named."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patches = [
            mock.patch.object(gen_gates, "WORKFLOWS", self.tmp),
            mock.patch.object(gen_gates, "OUTPUT", self.tmp / "gates.yml"),
            mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job"),)),
            mock.patch.object(gen_gates, "MOVED", {}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def source(self, job: str, top: str = "permissions:\n  contents: read\n") -> None:
        text = f"name: one\non:\n  workflow_call:\n{top}jobs:\n  job:\n{job}"
        (self.tmp / "one.yml").write_text(text, encoding="utf-8")

    STEP = (
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@" + "1" * 40 + " # v7\n"
    )

    def refused(self, *words: str) -> None:
        with self.assertRaises(gen_gates.Refused) as caught:
            gen_gates.build()
        for word in words:
            self.assertIn(word, str(caught.exception))

    def test_a_source_that_is_not_there(self):
        self.refused("one.yml could not be read")

    def test_a_job_in_a_source_that_no_check_names(self):
        self.source(self.STEP + "  other:\n" + self.STEP)
        self.refused("one.yml job 'other' is in a reusable gates.yml is made of", "Add it to CHECKS")

    def test_a_job_that_is_not_there(self):
        self.source(self.STEP)
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "other"),)):
            self.refused("has no job 'other'")

    def test_a_key_it_cannot_carry(self):
        self.source(self.STEP + "    services:\n      db:\n        image: x\n")
        self.refused("holds services")

    def test_a_runner_that_is_not_the_shared_one(self):
        self.source(self.STEP.replace("ubuntu-latest", "macos-latest"))
        self.refused("runs on 'macos-latest'")

    def test_an_action_nobody_has_read(self):
        self.source(self.STEP + "      - uses: someone/tool@" + "2" * 40 + " # v1\n")
        self.refused("uses someone/tool", "name it in INERT or GUARDED")

    def test_a_guarded_action_with_no_guard_before_it(self):
        lint = "      - uses: DavidAnson/markdownlint-cli2-action@" + "3" * 40 + " # v24\n"
        self.source(self.STEP + lint)
        self.refused("uses DavidAnson/markdownlint-cli2-action with no step 'markdown-only' before it")
        self.source(self.STEP + lint + "      - id: markdown-only\n        run: 'true'\n")
        self.refused("with no step 'markdown-only' before it")

    def test_a_guarded_action_after_its_guard_is_carried(self):
        lint = "      - uses: DavidAnson/markdownlint-cli2-action@" + "3" * 40 + " # v24\n"
        self.source(self.STEP + "      - id: markdown-only\n        run: 'true'\n" + lint)
        self.assertIn("markdownlint-cli2-action@", gen_gates.build())

    def test_an_actor_is_not_asked_about_its_actions(self):
        # report runs only actions/ ones, which a test of the generated file holds.
        self.source(self.STEP + "      - uses: someone/tool@" + "2" * 40 + " # v1\n",
                    top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)):
            self.assertIn("someone/tool@", gen_gates.build())

    def test_a_script_carrying_an_expression(self):
        self.source(self.STEP + "      - run: echo ${{ github.event.pull_request.title }}\n")
        self.refused("has an expression in its script", "Pass it through env")

    def test_an_explainer_script_carrying_an_expression(self):
        called = (pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/explain-check.yml").read_text(
            encoding="utf-8")
        (self.tmp / "explain-check.yml").write_text(
            called.replace('set -euo pipefail\n', 'set -euo pipefail\n          echo "${{ inputs.title }}"\n', 1),
            encoding="utf-8")
        self.source("    uses: ./.github/workflows/explain-check.yml\n"
                    "    with:\n      check: x\n      title: t\n      body: b\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)):
            self.refused("explain-check.yml job 'explain' has an expression in its script")

    def test_a_write_permission_put_nowhere(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        self.refused("asks for a write permission")

    def test_a_write_permission_on_a_check_that_acts_is_carried(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)):
            self.assertIn("one / job", gen_gates.build())

    def test_an_explainer_that_is_not_a_plain_call(self):
        self.source("    uses: ./.github/workflows/other.yml\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)):
            self.refused("is not a plain call")

    def test_an_explainer_missing_an_input(self):
        shutil.copy(pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/explain-check.yml",
                    self.tmp / "explain-check.yml")
        self.source("    uses: ./.github/workflows/explain-check.yml\n    with:\n      check: x\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)):
            self.refused("reads inputs.title, which an explainer does not pass")

    def test_a_job_read_that_nothing_carries(self):
        self.source(self.STEP + "      - name: write\n        run: echo \"$X\"\n        env:\n          X: ${{ needs.elsewhere.outputs.x }}\n",
                    top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)):
            self.refused("reads needs.elsewhere.outputs.x")

    def test_a_job_deciding_by_a_status_function(self):
        self.source("    if: always()\n" + self.STEP)
        self.refused("decides by a status function")

    def test_a_step_deciding_by_a_status_function(self):
        self.source(self.STEP + "      - run: echo\n        if: failure()\n")
        self.refused("step deciding by a status function")

    def test_a_reference_to_a_step_that_is_not_earlier(self):
        self.source(self.STEP + "      - run: echo \"$X\"\n        env:\n          X: ${{ steps.later.outputs.x }}\n")
        self.refused("steps.later")

    def test_a_moved_step_referring_to_a_step_that_is_not_earlier(self):
        self.source(self.STEP + "      - name: write\n        run: echo \"$X\"\n        env:\n          X: ${{ steps.later.outputs.x }}\n",
                    top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "MOVED", {("one", "job"): frozenset({"write"})}):
            self.refused("steps.later")

    def test_a_pin_with_no_version(self):
        self.source(self.STEP.replace(" # v7", ""))
        self.refused("pinned with no version comment")

    def test_one_pin_named_two_ways(self):
        self.source(self.STEP + "      - uses: actions/checkout@" + "1" * 40 + " # v8\n")
        self.refused("is called 'v7' in one reusable and 'v8' in another")

    def test_a_job_environment_reaches_each_step(self):
        self.source("    env:\n      KEPT: 'yes'\n" + self.STEP)
        self.assertIn("KEPT: 'yes'", gen_gates.build())

    def test_a_wrapped_condition_and_a_list_are_carried(self):
        self.source(self.STEP + "      - run: echo\n        if: ${{ github.event_name == 'push' }}\n"
                    "        with:\n          many: [a, b]\n")
        workflow = yaml.safe_load(gen_gates.build())
        step = workflow["jobs"]["gates"]["steps"][-2]
        self.assertTrue(step["if"].endswith("&& (github.event_name == 'push') }}"), step["if"])
        self.assertEqual(step["with"]["many"], ["a", "b"])

    def test_a_moved_step_waits_on_the_steps_before_it_in_gates(self):
        self.source(self.STEP + "      - run: make\n      - name: write\n        run: echo\n",
                    top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "MOVED", {("one", "job"): frozenset({"write"})}):
            workflow = yaml.safe_load(gen_gates.build())
        moved = next(s for s in workflow["jobs"]["report"]["steps"] if s["id"] == "one--job--2")
        self.assertIn("needs.gates.outputs.one--job--reached-2 == 'true'", moved["if"])
        reached = workflow["jobs"]["gates"]["outputs"]["one--job--reached-2"]
        self.assertIn("steps.one--job--0.outcome != 'failure'", reached)
        self.assertIn("steps.one--job--1.outcome != 'failure'", reached)

    def test_a_job_condition_and_an_unnamed_step(self):
        self.source("    if: github.event_name == 'pull_request'\n" + self.STEP + "      - run: echo\n")
        text = gen_gates.build()
        self.assertIn("(github.event_name == 'pull_request')", text)
        self.assertIn("one / job: step 2", text)


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patch = mock.patch.object(gen_gates, "OUTPUT", self.tmp / "gates.yml")
        patch.start()
        self.addCleanup(patch.stop)

    def call(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen_gates.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_write_then_check(self):
        self.assertEqual(self.call()[0], 0)
        code, out, _ = self.call("--check")
        self.assertEqual((code, out.strip()), (0, "gates.yml is what the reusables say"))

    def test_a_check_against_a_drifted_copy(self):
        (self.tmp / "gates.yml").write_text("edited by hand\n")
        code, _, err = self.call("--check")
        self.assertEqual(code, 1)
        self.assertIn("Run `python3 scripts/gen_gates.py`", err)

    def test_a_check_against_no_copy(self):
        self.assertEqual(self.call("--check")[0], 1)

    def test_a_refusal_is_said_and_fails(self):
        with mock.patch.object(gen_gates, "build", side_effect=gen_gates.Refused("no")):
            code, _, err = self.call()
        self.assertEqual((code, err.strip()), (1, "::error::no"))


if __name__ == "__main__":
    unittest.main()
