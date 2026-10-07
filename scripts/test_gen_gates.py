#!/usr/bin/env python3
"""What `gen_gates.py` writes, and what the workflow it writes does when it runs.

Two questions, and the second is the one that matters. The first is whether the
generator carries each check's steps across and refuses what it cannot carry.
The second is whether the generated jobs behave as the sixteen jobs did: a
check's failing step stops that check's later steps and no other check's, a step
its reusable lets fail stops nothing, a check the caller skips is published as
skipped, a check that reported nothing is published as failed, and every check
reaches the merge box under the name the branch requires.

The second is answered by running the generated file: each step's condition is
evaluated with `workflow_expression`, each step is given the outcome a case
asks for, the verdicts are read from the expressions the file holds, and the
plan, verdict and publish scripts run as written, the last against a local
server standing in for the checks API.

Stdlib unittest plus PyYAML, as the coverage job installs.
Run:  python3 scripts/test_gen_gates.py
"""

from __future__ import annotations

import contextlib
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from typing import ClassVar
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
                   "skip": "", "names": "caller", **(inputs or {})},
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

    def __init__(self, failing=(), ctx_args=None, plan=None, checks_outcome="success"):
        self.workflow = generated()
        self.failing = set(failing)
        self.ctx_args = ctx_args or {}
        self.plan = plan
        self.checks_outcome = checks_outcome

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
            outputs = {"status": "1" if sid in self.failing else "0", "reason": "r"}
            ctx["steps"][sid] = {"outcome": outcome, "outputs": outputs}
        return ctx, started

    def run(self) -> tuple[dict, list[str], list[str]]:
        ctx = context(**self.ctx_args)
        ctx, here = self.job("checks", ctx)
        outputs = {k: substitute(v, ctx) for k, v in self.workflow["jobs"]["checks"]["outputs"].items()}
        if self.checks_outcome != "success":
            outputs = {}
        act = context(**self.ctx_args)
        act["needs"] = {"checks": {"outputs": outputs, "result": self.checks_outcome}}
        act, there = self.job("act", act)
        publish = self.workflow["jobs"]["act"]["steps"][-1]
        verdicts = json.loads(substitute(publish["env"]["VERDICTS"], act))
        return verdicts, here, there


class Generation(unittest.TestCase):
    def test_no_step_writes_a_verdict(self):
        checks = generated()["jobs"]["checks"]
        for check in gen_gates.CHECKS:
            if check.group in gen_gates.ACTING:
                continue
            said = checks["outputs"][gen_gates.slug(check)]
            # The plan runs first, before any step that reads a pull request's
            # files, and is the one step whose output a verdict may read.
            self.assertEqual(re.findall(r"steps\.([\w-]+)\.outputs", said), ["plan"], check)
            self.assertIn(".outcome", said, check)

    def test_the_checks_job_holds_no_secret_and_reads_only(self):
        workflow = generated()
        self.assertNotIn("secrets", workflow[True]["workflow_call"])
        self.assertNotIn("secrets.", gen_gates.build())
        self.assertEqual(workflow["jobs"]["checks"]["permissions"], {"contents": "read"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})

    def test_the_committed_file_is_what_the_reusables_say(self):
        self.assertEqual(gen_gates.OUTPUT.read_text(encoding="utf-8"), gen_gates.build())

    def test_two_jobs_and_the_permissions_each_holds(self):
        jobs = generated()["jobs"]
        self.assertEqual(list(jobs), ["checks", "act"])
        self.assertEqual(jobs["checks"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["act"]["permissions"]["checks"], "write")
        self.assertEqual(jobs["act"]["needs"], "checks")

    def test_no_third_party_action_runs_beside_the_write_token(self):
        for step in generated()["jobs"]["act"]["steps"]:
            uses = step.get("uses", "")
            self.assertTrue(uses == "" or uses.startswith("actions/"), uses)

    def test_a_consumer_runs_only_the_canonical_scripts(self):
        # The one other reader a step may pick is spec's own, in a branch taken
        # where the repository is lemonfiber/spec, which the plan refuses before
        # any step runs. act's workspace holds spec at main and nothing else.
        spec_branch = re.compile(r'^if \[ "\$(REPO|GITHUB_REPOSITORY)" = "lemonfiber/spec" \]; then$')
        for name, job in generated()["jobs"].items():
            for step in job["steps"]:
                canonical: set[str] = set()
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
                        self.assertTrue(assigned[2].startswith(".spec-canonical"), (step["id"], line))
                        canonical.add(assigned[1])
                    ran = re.search(r"python3 [\"']?([^\"'\s]+)", line)
                    if not ran or ran[1] in ("-", "-c"):
                        continue
                    said = ran[1]
                    variable = re.match(r"\$\{?(\w+)", said)
                    if name == "act":
                        self.assertTrue(said.startswith("scripts/"), (step["id"], line))
                    elif variable:
                        self.assertIn(variable[1], canonical, (step["id"], line))
                    else:
                        self.assertTrue(said.startswith(".spec-canonical/"), (step["id"], line))

    def test_every_checkout_drops_its_credentials_and_spec_is_read_at_main(self):
        jobs = generated()["jobs"]
        for name, job in jobs.items():
            for step in job["steps"]:
                if not step.get("uses", "").startswith("actions/checkout@"):
                    continue
                said = step.get("with", {})
                self.assertIs(said.get("persist-credentials"), False, step["id"])
                if said.get("repository") == "lemonfiber/spec" or name == "act":
                    self.assertEqual(said.get("repository"), "lemonfiber/spec", step["id"])
                    self.assertEqual(said.get("ref"), "main", step["id"])

    def test_every_source_step_is_carried_once(self):
        workflow = generated()
        carried = [s for job in workflow["jobs"].values() for s in job["steps"]]
        for check in gen_gates.CHECKS:
            read = yaml.safe_load((gen_gates.WORKFLOWS / check.source).read_text(encoding="utf-8"))
            for index, step in enumerate(read["jobs"][check.job]["steps"]):
                sid = f"{gen_gates.slug(check)}--{step.get('id', index)}"
                found = [s for s in carried if s.get("id") == sid]
                self.assertEqual(len(found), 1, sid)
                for key in ("run", "uses", "with"):
                    if key in step and key == "uses":
                        self.assertEqual(found[0][key], step[key])

    def test_each_pin_keeps_the_version_its_reusable_names(self):
        text = gen_gates.build()
        for line in text.splitlines():
            if re.search(r"uses: \S+@[0-9a-f]{40}", line):
                self.assertRegex(line, r"# \S")

    def test_each_check_starts_from_an_empty_workspace(self):
        steps = [s for job in generated()["jobs"].values() for s in job["steps"]]
        ids = [s.get("id") for s in steps]
        for check in gen_gates.CHECKS:
            base = gen_gates.slug(check)
            first = next(i for i, sid in enumerate(ids) if sid and sid.startswith(base + "--") and sid != base + "--fresh")
            self.assertEqual(ids[first - 1], base + "--fresh", check)
            self.assertEqual(steps[first - 1]["run"], 'find "$GITHUB_WORKSPACE" -mindepth 1 -delete')

    def test_every_read_only_check_is_wiped_for_inside_checks(self):
        checks = [s.get("id") for s in generated()["jobs"]["checks"]["steps"]]
        for check in gen_gates.CHECKS:
            if check.group not in gen_gates.ACTING:
                self.assertIn(gen_gates.slug(check) + "--fresh", checks, check)

    def test_a_step_that_can_fail_its_check_is_in_its_verdict(self):
        outputs = generated()["jobs"]["checks"]["outputs"]
        self.assertIn("steps.spec-check--spec-check--0.outcome == 'failure'", outputs["spec-check--spec-check"])
        self.assertIn("steps.hygiene--typos--1.outcome == 'failure'", outputs["hygiene--typos"])

    def test_a_step_its_reusable_lets_fail_is_not_in_its_verdict(self):
        said = generated()["jobs"]["checks"]["outputs"]["spec-check--spec-check"]
        self.assertNotIn("spec-check--spec-check--citation.outcome", said)

    def test_the_line_cap_reads_the_sources_the_generator_reads(self):
        import generated

        entry = generated.owner_of(".github/workflows/gates.yml")
        self.assertIsNotNone(entry)
        read = {f".github/workflows/{check.source}" for check in gen_gates.CHECKS}
        self.assertEqual(set(entry.sources), read)
        self.assertEqual(len(entry.sources), len(read))

    def test_the_header_names_the_generator(self):
        self.assertIn("GENERATED by scripts/gen_gates.py", gen_gates.build()[:400])


class Behaviour(unittest.TestCase):
    def test_everything_passing_publishes_every_check_green(self):
        verdicts, here, there = Runner().run()
        self.assertEqual(set(verdicts.values()), {"success"})
        self.assertEqual(len(verdicts), len(gen_gates.CHECKS))
        self.assertIn("hygiene--typos--1", here)
        self.assertIn("labeler--label--0", there)
        # Nothing to close where every citation resolved.
        self.assertNotIn("spec-check--spec-check--6", there)

    def test_a_failing_step_fails_its_check_and_stops_its_later_steps_only(self):
        verdicts, here, _ = Runner(failing={"hygiene--links--0"}).run()
        self.assertEqual(verdicts["hygiene--links"], "failure")
        self.assertNotIn("hygiene--links--1", here)
        self.assertIn("hygiene--markdown--0", here)
        others = {k: v for k, v in verdicts.items() if k != "hygiene--links"}
        self.assertEqual(set(others.values()), {"success"})

    def test_a_step_its_reusable_lets_fail_stops_nothing(self):
        _, here, there = Runner(failing={"spec-check--spec-check--citation"}).run()
        self.assertIn("spec-check--spec-check--7", here)
        # The citation's own refusal comes from the step after it, as before.
        self.assertIn("spec-check--spec-check--6", there)

    def test_the_closing_step_waits_for_the_steps_before_it(self):
        _, _, there = Runner(failing={"spec-check--spec-check--2", "spec-check--spec-check--citation"}).run()
        self.assertNotIn("spec-check--spec-check--6", there)

    def test_a_failing_moved_step_fails_its_check(self):
        verdicts, _, _ = Runner(failing={"spec-check--spec-check--citation", "spec-check--spec-check--6"}).run()
        self.assertEqual(verdicts["spec-check--spec-check"], "failure")

    def test_a_check_in_act_fails_on_its_own_step(self):
        verdicts, _, there = Runner(failing={"goals--classify--1"}).run()
        self.assertEqual(verdicts["goals--classify"], "failure")
        self.assertNotIn("goals--classify--2", there)

    def test_a_skipped_check_is_published_as_skipped_and_runs_nothing(self):
        verdicts, here, there = Runner(ctx_args={"inputs": {"skip": "labeler spec-check"}}).run()
        self.assertEqual(verdicts["labeler--label"], "skipped")
        self.assertEqual(verdicts["spec-check--spec-check"], "skipped")
        self.assertFalse([s for s in here + there if s.startswith(("labeler", "spec-check"))])

    def test_a_reusables_own_job_condition_skips_its_check(self):
        verdicts, _, there = Runner(ctx_args={"head_repo": "someone/core"}).run()
        self.assertEqual(verdicts["goals--classify"], "skipped")
        self.assertFalse([s for s in there if s.startswith("goals")])

    def test_a_fork_pull_request_starts_no_act(self):
        said = generated()["jobs"]["act"]["if"]
        self.assertFalse(decides(said, context(head_repo="someone/core")))
        self.assertFalse(decides(said, context(head_repo="someone/core"), status="failure"))
        self.assertTrue(decides(said, context()))
        self.assertTrue(decides(said, context(), status="failure"))
        for event in ("merge_group", "push"):
            self.assertTrue(decides(said, context(event_name=event)), event)
        self.assertFalse(decides(said, context(), status="cancelled"))

    def test_a_checks_job_that_reported_nothing_leaves_every_verdict_empty(self):
        verdicts, _, _ = Runner(checks_outcome="failure").run()
        for check in gen_gates.CHECKS:
            if check.group not in gen_gates.ACTING:
                self.assertEqual(verdicts[gen_gates.slug(check)], "", check)


def bash(script: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], env={**os.environ, **env},
                          capture_output=True, text=True, check=False)


class Scripts(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "output"
        self.out.write_text("")

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

    def test_a_failure_fails_the_job_and_writes_nothing(self):
        said = bash(gen_gates.HELD, {"VERDICTS": json.dumps({"x--y": "failure", "z--w": "success"}),
                                     "GITHUB_OUTPUT": str(self.out)})
        self.assertEqual(said.returncode, 1)
        self.assertIn("x / y failed", said.stdout)
        self.assertEqual(self.out.read_text(), "")

    def test_the_verdicts_pass_when_nothing_failed(self):
        said = bash(gen_gates.HELD, {"VERDICTS": json.dumps({"x--y": "skipped"}),
                                     "GITHUB_OUTPUT": str(self.out)})
        self.assertEqual(said.returncode, 0)


class Recorder(http.server.BaseHTTPRequestHandler):
    received: ClassVar[list] = []
    answer = 201

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        Recorder.received.append((self.path, self.headers["Authorization"], json.loads(self.rfile.read(length))))
        self.send_response(Recorder.answer)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


class Publishing(unittest.TestCase):
    def setUp(self):
        Recorder.received = []
        Recorder.answer = 201
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def publish(self, verdicts: dict, checks="hygiene dco", names="caller") -> subprocess.CompletedProcess:
        listed = [["hygiene", "typos", "hygiene--typos"], ["dco", "dco", "dco--dco"],
                  ["goals", "classify", "goals--classify"]]
        return bash(gen_gates.PUBLISH, {
            "LISTED": json.dumps(listed), "VERDICTS": json.dumps(verdicts), "NAMES": names,
            "CHECKS": checks, "HEAD_SHA": HEAD, "GH_TOKEN": "secret",
            "GITHUB_API_URL": f"http://127.0.0.1:{self.server.server_port}",
            "GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": REPO, "GITHUB_RUN_ID": "9",
        })

    def test_each_listed_check_is_published_under_the_callers_name(self):
        said = self.publish({"hygiene--typos": "success", "dco--dco": "skipped"})
        self.assertEqual(said.returncode, 0, said.stdout + said.stderr)
        sent = {body["name"]: body for _, _, body in Recorder.received}
        self.assertEqual(set(sent), {"hygiene / typos", "dco / dco"})
        self.assertEqual(sent["hygiene / typos"]["conclusion"], "success")
        self.assertEqual(sent["dco / dco"]["conclusion"], "skipped")
        self.assertEqual(sent["dco / dco"]["head_sha"], HEAD)
        self.assertEqual(sent["dco / dco"]["status"], "completed")
        self.assertTrue(sent["dco / dco"]["details_url"].endswith("/actions/runs/9"))
        path, auth, _ = Recorder.received[0]
        self.assertEqual(path, f"/repos/{REPO}/check-runs")
        self.assertEqual(auth, "Bearer secret")

    def test_the_bare_name_where_the_caller_asks_for_it(self):
        self.publish({"hygiene--typos": "failure", "dco--dco": "success"}, names="job")
        self.assertEqual({body["name"] for _, _, body in Recorder.received}, {"typos", "dco"})

    def test_a_check_that_reported_nothing_is_published_as_failed(self):
        self.publish({"hygiene--typos": "", "dco--dco": "pending"})
        for _, _, body in Recorder.received:
            self.assertEqual(body["conclusion"], "failure")
            self.assertIn("did not report", body["output"]["summary"])

    def test_a_check_that_could_not_be_published_fails_the_job_and_is_named(self):
        Recorder.answer = 403
        said = self.publish({"hygiene--typos": "success", "dco--dco": "success"})
        self.assertEqual(said.returncode, 1)
        self.assertIn("hygiene / typos", said.stdout)
        self.assertIn("could not be published", said.stdout)


class Refusals(unittest.TestCase):
    """What the generator will not carry, each named."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patches = [
            mock.patch.object(gen_gates, "WORKFLOWS", self.tmp),
            mock.patch.object(gen_gates, "OUTPUT", self.tmp / "gates.yml"),
            mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job"),)),
            mock.patch.object(gen_gates, "ACTING", frozenset()),
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

    def test_a_write_permission_put_nowhere(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        self.refused("asks for a write permission")

    def test_a_write_permission_on_a_check_that_acts_is_carried(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "ACTING", frozenset({"one"})):
            self.assertIn("one / job", gen_gates.build())

    def test_a_job_deciding_by_a_status_function(self):
        self.source("    if: always()\n" + self.STEP)
        self.refused("decides by a status function")

    def test_a_step_deciding_by_a_status_function(self):
        self.source(self.STEP + "      - run: echo\n        if: failure()\n")
        self.refused("step deciding by a status function")

    def test_a_reference_to_a_step_that_is_not_earlier(self):
        self.source(self.STEP + "      - run: echo ${{ steps.later.outputs.x }}\n")
        self.refused("steps.later")

    def test_a_moved_step_referring_to_a_step_that_is_not_earlier(self):
        self.source(self.STEP + "      - name: write\n        run: echo ${{ steps.later.outputs.x }}\n",
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
        step = workflow["jobs"]["checks"]["steps"][-2]
        self.assertTrue(step["if"].endswith("&& (github.event_name == 'push') }}"), step["if"])
        self.assertEqual(step["with"]["many"], ["a", "b"])

    def test_a_moved_step_waits_on_the_steps_before_it_in_checks(self):
        self.source(self.STEP + "      - run: make\n      - name: write\n        run: echo\n",
                    top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(gen_gates, "MOVED", {("one", "job"): frozenset({"write"})}):
            workflow = yaml.safe_load(gen_gates.build())
        moved = next(s for s in workflow["jobs"]["act"]["steps"] if s["id"] == "one--job--2")
        self.assertIn("needs.checks.outputs.one--job--reached-2 == 'true'", moved["if"])
        reached = workflow["jobs"]["checks"]["outputs"]["one--job--reached-2"]
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
