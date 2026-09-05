#!/usr/bin/env python3
"""The maintainer flag, shown refusing to announce (OPS-R26, OPS-R27).

`awaiting-maintainer.yml` labels a pull request and tells the private maintainer
channel it is ready. It used to do that on one workflow's conclusion — the one
called `ci` — and say "Passed CI with no review". In lemonfiber `ci` supplies
eleven of the nineteen checks `main` requires, so the sentence was false whenever
`build`, `codeql`, `sonar` or `release-workflow` was still running or had already
failed. A claim nobody has watched fail is a claim nobody knows works, so this
puts the gate in front of each of those states and checks that it declines.

It drives the step as CI drives it: the shell is read out of the committed YAML
through a YAML parser, so it is the literal text that runs, and `gh` is replaced
on a PATH prefix by a stub that answers with a chosen set of workflow runs and a
chosen set of required checks. What is asserted is the label call that was or was
not made and the `flagged` output the notify job rides on — the announcement
itself, not a proxy for it.

The case that matters most is the one an obvious fix would get wrong. "No pending
and no failing checks" is also true in the gap between a push and the creation of
the other workflows' runs, when nothing has started. `test_a_workflow_with_no_run
_yet_holds` is that gap: every check that has reported is green, and the gate
still refuses, because a workflow the caller triggers on has no run at this commit.

Stdlib unittest plus PyYAML (the parser is the point — a hand-rolled reader would
be testing a different string than CI runs).
Run:  python3 scripts/test_awaiting_maintainer.py
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
WORKFLOW = HERE.parent / ".github" / "workflows" / "awaiting-maintainer.yml"
STEP = "Toggle label"
LABEL = "awaiting-maintainer"

# A caller's file as the fleet writes it: the trigger list is the wait list, so
# this fixture is what decides which workflows the gate holds for. lemonfiber's
# five, which between them supply all nineteen checks its `main` requires.
CALLER = """name: awaiting-maintainer
on:
  workflow_run:
    workflows: [ci, build, codeql, sonar, release-workflow]
    types: [completed]
  pull_request_review:
    types: [submitted]
  pull_request_target:
    types: [closed]
jobs:
  awaiting:
    uses: lemonfiber/spec/.github/workflows/awaiting-maintainer.yml@main
"""

# The same file with the list written as a block sequence. Valid YAML, and not
# something this gate's reader will guess at.
CALLER_BLOCK = """name: awaiting-maintainer
on:
  workflow_run:
    workflows:
      - ci
      - build
    types: [completed]
"""

CALLER_EMPTY = """name: awaiting-maintainer
on:
  workflow_run:
    workflows: []
    types: [completed]
"""

# Stand in for gh. Every call is logged so a test can ask what was asked, and the
# answers come from files named in the environment. Dispatch is on the URL and on
# the --jq expression together, because two of the calls read the same URL.
GH_STUB = '''#!/usr/bin/env python3
import json, os, sys

args = sys.argv[1:]
log = os.environ.get("GH_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(" ".join(args) + "\\n")


def answer(var, default=""):
    path = os.environ.get(var, "")
    if not path:
        sys.stdout.write(default)
        return
    with open(path, encoding="utf-8") as fh:
        sys.stdout.write(fh.read())


if args[:2] == ["pr", "edit"]:
    sys.exit(int(os.environ.get("GH_EDIT_RC", "0")))

if args[:2] == ["pr", "checks"]:
    answer("GH_CHECKS")
    sys.stderr.write(os.environ.get("GH_CHECKS_ERR", ""))
    sys.exit(int(os.environ.get("GH_CHECKS_RC", "0")))

if args[0] == "api":
    jq = args[args.index("--jq") + 1] if "--jq" in args else ""
    url = [a for a in args[1:] if not a.startswith("-")]
    url = [u for u in url if u != jq and not u.startswith("Accept:")]
    url = url[0] if url else ""
    if "/contents/" in url:
        if os.environ.get("GH_CALLER_RC", "0") != "0":
            sys.stderr.write("gh: Not Found (HTTP 404)\\n")
            sys.exit(int(os.environ["GH_CALLER_RC"]))
        answer("GH_CALLER")
        sys.exit(0)
    if "/actions/runs" in url:
        answer("GH_RUNS", "[]")
        sys.exit(0)
    if url.endswith("/pulls"):
        sys.stdout.write(os.environ.get("GH_PR", "") + "\\n")
        sys.exit(0)
    if url.endswith("/reviews"):
        sys.stdout.write(os.environ.get("GH_APPROVED", "0") + "\\n")
        sys.exit(0)
    if "author_association" in jq:
        sys.stdout.write(os.environ.get("GH_ASSOC", "CONTRIBUTOR") + "\\n")
        sys.exit(0)
    if "labels" in jq:
        for name in json.loads(os.environ.get("GH_LABELS", "[]")):
            sys.stdout.write(name + "\\n")
        sys.exit(0)

sys.stderr.write("gh stub: nothing answers " + " ".join(args) + "\\n")
sys.exit(64)
'''


def step_script() -> str:
    """The `run:` text of the toggle step, as the parser hands it to the runner."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    named = [s for s in workflow["jobs"]["toggle"]["steps"] if s["name"] == STEP]
    return named[0]["run"]


def declared_triggers() -> list[str]:
    """The workflows this repo's own copy triggers on, read the same way."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads a bare `on:` key as the boolean it is in YAML 1.1.
    triggers = workflow.get("on", workflow.get(True))
    return list(triggers["workflow_run"]["workflows"])


def runs(**named: str) -> str:
    """A paginated-and-slurped `actions/runs` answer: workflow name → state.

    A value of "running" is a run that has not completed; anything else is a
    conclusion. A workflow left out has no run at this commit at all, which is
    the state the race window is made of.
    """
    listed = []
    for index, (name, state) in enumerate(named.items()):
        listed.append(
            {
                "name": name,
                "run_started_at": f"2026-09-05T10:0{index}:00Z",
                "status": "in_progress" if state == "running" else "completed",
                "conclusion": None if state == "running" else state,
            }
        )
    return json.dumps([{"workflow_runs": listed}])


def checks(**named: str) -> str:
    """A `gh pr checks --required --json name,bucket` answer: name → bucket."""
    return json.dumps([{"name": n, "bucket": b} for n, b in named.items()])


ALL_GREEN_RUNS = runs(
    ci="success",
    build="success",
    codeql="success",
    sonar="success",
    **{"release-workflow": "success"},
)
ALL_GREEN_CHECKS = checks(
    **{
        "spec-check / spec-check": "pass",
        "check": "pass",
        "deny": "pass",
        "sonar": "pass",
        "gate / gate": "pass",
        "analyze (rust)": "pass",
        "release-workflow": "pass",
    }
)


class Gate(unittest.TestCase):
    """The step, run against a stubbed GitHub."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(step_script(), encoding="utf-8")
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        gh = stubs / "gh"
        gh.write_text(GH_STUB, encoding="utf-8")
        gh.chmod(0o755)
        self.stubs = stubs
        self.log = self.tmp / "gh.log"
        self.output = self.tmp / "github_output"
        self.output.write_text("", encoding="utf-8")

    def file(self, name: str, text: str) -> str:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def run_step(
        self,
        *,
        event="workflow_run",
        conclusion="success",
        review_state="",
        pr_number="",
        caller=CALLER,
        caller_rc=0,
        runs_json=ALL_GREEN_RUNS,
        checks_json=ALL_GREEN_CHECKS,
        checks_rc=0,
        checks_err="",
        labels=(),
        assoc="CONTRIBUTOR",
        approved="0",
        pr="41",
        edit_rc=0,
    ):
        work = self.tmp / "work"
        work.mkdir(exist_ok=True)
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GH_TOKEN": "not-a-real-token",
            "GH_REPO": "lemonfiber/lemonfiber",
            "EVENT": event,
            "CONCLUSION": conclusion,
            "HEAD_SHA": "0123456789abcdef0123456789abcdef01234567",
            "REVIEW_STATE": review_state,
            "PR_NUMBER": pr_number,
            "WORKFLOW_REF": (
                "lemonfiber/lemonfiber/.github/workflows/"
                "awaiting-maintainer.yml@refs/heads/main"
            ),
            "DEFAULT_BRANCH": "main",
            "LABEL": LABEL,
            "GITHUB_OUTPUT": str(self.output),
            "GH_LOG": str(self.log),
            "GH_PR": pr,
            "GH_ASSOC": assoc,
            "GH_APPROVED": approved,
            "GH_LABELS": json.dumps(list(labels)),
            "GH_CALLER_RC": str(caller_rc),
            "GH_CHECKS_RC": str(checks_rc),
            "GH_CHECKS_ERR": checks_err,
            "GH_EDIT_RC": str(edit_rc),
        }
        if caller is not None:
            env["GH_CALLER"] = self.file("caller.yml", caller)
        if runs_json is not None:
            env["GH_RUNS"] = self.file("runs.json", runs_json)
        if checks_json is not None:
            env["GH_CHECKS"] = self.file("checks.json", checks_json)
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    # --- what was actually done ---------------------------------------------

    def asked(self) -> str:
        return self.log.read_text(encoding="utf-8") if self.log.exists() else ""

    def flagged(self) -> str:
        return self.output.read_text(encoding="utf-8")

    def assertNotAnnounced(self, code, out):
        """The gate declined: no label went on, and notify has nothing to ride."""
        self.assertEqual(code, 0, out)
        self.assertNotIn("--add-label", self.asked())
        self.assertNotIn("flagged=true", self.flagged())

    # --- the fixtures have to be saying something ---------------------------

    def test_the_step_was_read_out_of_the_workflow(self):
        """Every case below runs this text. An empty read would pass them all."""
        script = step_script()
        self.assertIn("--add-label", script)
        self.assertIn("--required", script)
        self.assertGreater(len(script.splitlines()), 40)

    def test_the_stub_answers_every_call_the_step_makes(self):
        """A stub that exited 64 unnoticed would look like a gate that declined."""
        code, out = self.run_step()
        self.assertNotIn("gh stub: nothing answers", out)
        self.assertEqual(code, 0, out)

    # --- the green path, so the refusals below are refusals ------------------

    def test_everything_green_flags_and_announces(self):
        code, out = self.run_step()
        self.assertEqual(code, 0, out)
        self.assertIn(f"pr edit 41 --add-label {LABEL}", self.asked())
        self.assertIn("flagged=true", self.flagged())
        self.assertIn("pr=41", self.flagged())
        self.assertIn("checks=7", self.flagged())
        self.assertIn("7 required checks, all green", out)

    def test_a_skipped_required_check_is_not_held_against_the_pull_request(self):
        code, out = self.run_step(
            checks_json=checks(**{"check": "pass", "deny": "skipping"})
        )
        self.assertEqual(code, 0, out)
        self.assertIn("flagged=true", self.flagged())

    # --- the refusals, which are the whole reason the gate exists ------------

    def test_a_pending_required_check_holds(self):
        code, out = self.run_step(
            checks_json=checks(**{"check": "pending", "deny": "pass"}),
            checks_rc=8,
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("Holding #41: check (pending)", out)

    def test_a_failing_required_check_holds(self):
        code, out = self.run_step(
            checks_json=checks(**{"check": "fail", "deny": "pass"}),
            checks_rc=1,
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("Holding #41: check (fail)", out)

    def test_a_cancelled_required_check_holds(self):
        code, out = self.run_step(checks_json=checks(**{"check": "cancel"}))
        self.assertNotAnnounced(code, out)
        self.assertIn("check (cancel)", out)

    def test_a_workflow_with_no_run_yet_holds(self):
        """The window an obvious fix announces in.

        Every check that has reported is green and none is pending, because the
        other workflows have not created their runs. Checks alone cannot tell
        this apart from a finished pull request; the trigger list can.
        """
        code, out = self.run_step(
            runs_json=runs(ci="success"),
            checks_json=checks(**{"spec-check / spec-check": "pass"}),
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("build(no run at this commit yet)", out)
        self.assertIn("codeql(no run at this commit yet)", out)
        self.assertIn("sonar(no run at this commit yet)", out)
        self.assertIn("release-workflow(no run at this commit yet)", out)

    def test_a_workflow_still_running_holds(self):
        code, out = self.run_step(
            runs_json=runs(
                ci="success",
                build="running",
                codeql="success",
                sonar="success",
                **{"release-workflow": "success"},
            )
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("build(still running)", out)

    def test_a_workflow_that_failed_holds(self):
        code, out = self.run_step(
            runs_json=runs(
                ci="success",
                build="failure",
                codeql="success",
                sonar="success",
                **{"release-workflow": "success"},
            )
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("build(failure)", out)

    def test_no_required_check_reported_holds(self):
        """gh answers "no checks reported" with an error and no JSON."""
        code, out = self.run_step(
            checks_json="", checks_rc=1, checks_err="no checks reported\n"
        )
        self.assertNotAnnounced(code, out)
        self.assertIn("No required check has reported on #41 yet", out)
        self.assertIn("no checks reported", out)

    def test_an_empty_required_check_list_holds(self):
        code, out = self.run_step(checks_json="[]")
        self.assertNotAnnounced(code, out)
        self.assertIn("No required check has reported on #41 yet", out)

    def test_the_triggering_run_having_failed_holds(self):
        code, out = self.run_step(conclusion="failure")
        self.assertNotAnnounced(code, out)
        self.assertIn("concluded failure", out)

    def test_a_maintainer_authored_pull_request_is_never_flagged(self):
        code, out = self.run_step(assoc="MEMBER")
        self.assertNotAnnounced(code, out)
        self.assertIn("maintainer-authored", out)

    def test_an_approved_pull_request_is_never_flagged(self):
        code, out = self.run_step(approved="1")
        self.assertNotAnnounced(code, out)
        self.assertIn("already approved", out)

    def test_a_commit_on_no_pull_request_is_never_flagged(self):
        code, out = self.run_step(pr="")
        self.assertNotAnnounced(code, out)
        self.assertIn("No pull request at", out)

    # --- run once per finishing workflow, announce once ----------------------

    def test_a_label_already_there_announces_nothing(self):
        """Five workflows trigger this per commit, and re-runs bring it back."""
        code, out = self.run_step(labels=[LABEL, "size/s"])
        self.assertNotAnnounced(code, out)
        self.assertIn("already carries", out)

    def test_another_label_is_not_mistaken_for_this_one(self):
        code, out = self.run_step(labels=["awaiting-maintainer-x", "needs-triage"])
        self.assertEqual(code, 0, out)
        self.assertIn("flagged=true", self.flagged())

    # --- what it does when it cannot tell ------------------------------------

    def test_a_caller_file_it_cannot_read_fails_loudly(self):
        code, out = self.run_step(caller_rc=1)
        self.assertEqual(code, 1)
        self.assertIn("Could not read", out)
        self.assertNotIn("--add-label", self.asked())

    def test_a_trigger_list_that_is_not_one_bracketed_line_fails_loudly(self):
        code, out = self.run_step(caller=CALLER_BLOCK)
        self.assertEqual(code, 1)
        self.assertIn("exactly one bracketed line (found 0)", out)
        self.assertNotIn("--add-label", self.asked())

    def test_a_trigger_list_naming_nothing_fails_loudly(self):
        code, out = self.run_step(caller=CALLER_EMPTY)
        self.assertEqual(code, 1)
        self.assertIn("names no workflow to wait for", out)
        self.assertNotIn("--add-label", self.asked())

    def test_a_label_that_will_not_attach_is_not_announced(self):
        code, out = self.run_step(edit_rc=1)
        self.assertEqual(code, 1, out)
        self.assertNotIn("flagged=true", self.flagged())

    # --- it has to be asking the right thing ---------------------------------

    def test_it_waits_for_the_list_the_caller_declares(self):
        """The wait list is read from the file, not built into the gate.

        Same runs, a shorter declaration: what it holds for changes with the
        file, which is what makes the trigger list and the wait list one thing.
        """
        short = CALLER.replace(
            "[ci, build, codeql, sonar, release-workflow]", "[ci, build]"
        )
        code, out = self.run_step(caller=short, runs_json=runs(ci="success"))
        self.assertNotAnnounced(code, out)
        self.assertIn("build(no run at this commit yet)", out)
        self.assertNotIn("sonar(", out)

    def test_it_reads_the_callers_file_on_the_default_branch(self):
        self.run_step()
        self.assertIn(
            "repos/lemonfiber/lemonfiber/contents/"
            ".github/workflows/awaiting-maintainer.yml?ref=main",
            self.asked(),
        )

    def test_it_asks_only_about_required_checks(self):
        self.run_step()
        self.assertIn("pr checks 41 --required", self.asked())

    def test_it_asks_about_this_commit(self):
        self.run_step()
        self.assertIn(
            "head_sha=0123456789abcdef0123456789abcdef01234567", self.asked()
        )

    def test_the_step_carries_no_workflow_expressions(self):
        """OPS-R28: event-derived text reaches the shell through the environment."""
        self.assertNotIn("${{", step_script())

    # --- clearing the flag ---------------------------------------------------

    def test_a_closed_pull_request_clears_the_label(self):
        code, out = self.run_step(event="pull_request_target", pr_number="41")
        self.assertEqual(code, 0, out)
        self.assertIn(f"pr edit 41 --remove-label {LABEL}", self.asked())

    def test_an_approving_review_clears_the_label(self):
        code, out = self.run_step(
            event="pull_request_review", review_state="approved", pr_number="41"
        )
        self.assertEqual(code, 0, out)
        self.assertIn(f"pr edit 41 --remove-label {LABEL}", self.asked())

    def test_changes_requested_clears_the_label(self):
        code, out = self.run_step(
            event="pull_request_review",
            review_state="changes_requested",
            pr_number="41",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("--remove-label", self.asked())

    def test_a_comment_review_clears_nothing(self):
        code, out = self.run_step(
            event="pull_request_review", review_state="commented", pr_number="41"
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("--remove-label", self.asked())


class ThisRepositoryWaitsForItsOwn(unittest.TestCase):
    """The spec repo self-triggers, so its own trigger list is a wait list too."""

    def test_it_triggers_on_more_than_one_workflow(self):
        """The defect was a list of one. A list of one cannot be complete here:
        `main` requires sixteen checks and no single workflow supplies them."""
        self.assertGreater(len(declared_triggers()), 1, declared_triggers())

    def test_it_names_the_workflows_that_supply_this_repos_required_checks(self):
        """Read off `gh pr checks --required --json workflow` on a merged PR.

        A workflow missing from the trigger list never re-evaluates the gate, so
        the flag would wait forever on a check that had already gone green.
        """
        supplies = {
            "commitlint",
            "coverage",
            "dco",
            "docs",
            "hygiene",
            "integrity",
            "security",
            "sonar",
        }
        self.assertEqual(supplies - set(declared_triggers()), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
