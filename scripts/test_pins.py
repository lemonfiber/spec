#!/usr/bin/env python3
"""The pin check, shown refusing a pin near in time and far in commits (Q-R68).

`hygiene.yml`'s `pins` job says what shared revision a repository is actually
running. It used to decide that on age alone, and its own comment conceded the
hole: "a pin days old and dozens of commits behind reads as healthy here". That
is not a hypothetical. `brand` and `lemonfiber-media-stack` pinned this workflow
at a revision 94 commits behind and 13 days old — healthy by the day rule, and
old enough to predate the `pins` job itself, so neither repository ran a pin
check at all and nothing in either watched any shared pin, including the one
that had just been updated in both.

A claim nobody has watched fail is a claim nobody knows works, so what this
drives is the refusal: the same pin, 94 commits behind and 13 days old, put in
front of the gate and required to fail. The companion case is the one that
proves the new rule is what did it — the identical pin with the distance rule
relaxed goes green, which is the gate as it stood while the defect lived.

It drives the step as CI drives it. The shell is read out of the committed YAML
through a YAML parser, so it is the literal text that runs, and both `gh` and
`date` are replaced on a PATH prefix by stubs: `gh` answers a chosen comparison
per pin, `date` answers a chosen present, so "13 days old" means the same thing
in a year. The thresholds are read out of the workflow's own `env:` rather than
written here, because a suite holding its own 75 keeps passing after somebody
raises the workflow to 750.

Stdlib unittest plus PyYAML (the parser is the point — a hand-rolled reader would
be testing a different string than CI runs).
Run:  python3 scripts/test_pins.py
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "hygiene.yml"
STEP = "Compare each pinned shared workflow against the one maintained"

#: A fixed present, so an age written in a test means the same thing in a year.
NOW = "2026-09-05T12:00:00Z"

#: Stand-in pins. Only their shape matters — forty hex characters, which is what
#: the job's own grep looks for.
FAR = "a" * 40
NEAR = "b" * 40
GONE = "c" * 40

# Stand in for gh. It answers the one call the step makes, from a table keyed by
# the pin in the URL, and logs every call so a test can ask what was asked. A pin
# with no entry is answered the way the forge answers a revision it does not
# have: an error body on stdout, and a non-zero exit.
GH_STUB = '''#!/usr/bin/env python3
import json, os, re, sys

args = sys.argv[1:]
log = os.environ.get("GH_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(" ".join(args) + "\\n")

if args and args[0] == "api":
    url = next((a for a in args[1:] if a.startswith("repos/")), "")
    found = re.search(r"compare/([0-9a-f]{40})\\.\\.\\.main", url)
    if found:
        with open(os.environ["GH_COMPARE"], encoding="utf-8") as fh:
            table = json.load(fh)
        answer = table.get(found.group(1))
        if answer is None:
            sys.stdout.write("gh: No commit found for SHA (HTTP 404)\\n")
            sys.exit(1)
        sys.stdout.write(answer + "\\n")
        sys.exit(0)

sys.stderr.write("gh stub: nothing answers " + " ".join(args) + "\\n")
sys.exit(64)
'''

# Stand in for date. The step asks it two things: what time it is now, and what
# time an ISO-8601 string was. BSD date cannot answer the second at all, so this
# is what lets the suite run anywhere, and it stops the clock besides.
DATE_STUB = '''#!/usr/bin/env python3
import datetime, os, sys

args = sys.argv[1:]
if "-d" in args:
    when = args[args.index("-d") + 1]
else:
    when = os.environ["DATE_NOW"]
moment = datetime.datetime.fromisoformat(when.replace("Z", "+00:00"))
sys.stdout.write(str(int(moment.timestamp())) + "\\n")
'''


def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def pins_step() -> dict:
    """The step of the `pins` job, as the parser hands it to the runner."""
    named = [s for s in workflow()["jobs"]["pins"]["steps"] if s.get("name") == STEP]
    return named[0]


def step_script() -> str:
    return pins_step()["run"]


def threshold(name: str) -> int:
    """A threshold as the workflow declares it, not as this file remembers it."""
    return int(pins_step()["env"][name])


DAYS = threshold("STALE_DAYS")
COMMITS = threshold("STALE_COMMITS")


def days_ago(days: int) -> str:
    """An ISO timestamp that is `days` old against the fixed present."""
    moment = datetime.datetime.fromisoformat(NOW)
    return (moment - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def compared(ahead: int, days: int, status: str = "ahead", files: tuple = ()) -> str:
    """One `gh compare` answer, in the shape the step's --jq produces.

    The fourth field is what the commits between the pin and main touched, comma
    separated, which is how the step learns whether any of them was a workflow
    this repository runs. Empty by default: most of what lands here touches no
    workflow at all, and that is the answer the older cases were written under.
    """
    return f"{status} {ahead} {days_ago(days)} {','.join(files)}"


#: The comparison the defect had: 94 commits behind, 13 days old, which is well
#: inside the 30 days the day rule allows.
DEFECT = compared(94, 13)


class Pins(unittest.TestCase):
    """The step, run against a stubbed forge and a stopped clock."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.script = self.tmp / "step.sh"
        self.script.write_text(step_script(), encoding="utf-8")

        stubs = self.tmp / "stubs"
        stubs.mkdir()
        for name, body in (("gh", GH_STUB), ("date", DATE_STUB)):
            path = stubs / name
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)
        self.stubs = stubs
        self.log = self.tmp / "gh.log"

        self.work = self.tmp / "work"
        (self.work / ".github" / "workflows").mkdir(parents=True)

    def caller(self, name: str, *pins: str, shared: str = "hygiene.yml") -> None:
        """A caller workflow pinning the given revisions, as the fleet writes them."""
        lines = [f"name: {name}", "jobs:"]
        for index, pin in enumerate(pins):
            lines.append(f"  job{index}:")
            lines.append(
                f"    uses: lemonfiber/spec/.github/workflows/{shared}@{pin} # main"
            )
        path = self.work / ".github" / "workflows" / f"{name}.yml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_step(self, table: dict, *, commits: int | None = None):
        env = {
            "PATH": f"{self.stubs}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "GH_TOKEN": "not-a-real-token",
            "STALE_DAYS": str(DAYS),
            "STALE_COMMITS": str(COMMITS if commits is None else commits),
            "DATE_NOW": NOW,
            "GH_LOG": str(self.log),
            "GH_COMPARE": str(self.tmp / "compare.json"),
        }
        (self.tmp / "compare.json").write_text(json.dumps(table), encoding="utf-8")
        done = subprocess.run(
            ["bash", str(self.script)],
            cwd=self.work,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout + done.stderr

    def asked(self) -> str:
        return self.log.read_text(encoding="utf-8") if self.log.exists() else ""

    # --- the fixtures have to be saying something ---------------------------

    def test_the_step_was_read_out_of_the_workflow(self):
        """Every case below runs this text. An empty read would pass them all."""
        script = step_script()
        self.assertIn("STALE_COMMITS", script)
        self.assertIn("STALE_DAYS", script)
        self.assertIn("compare/", script)
        self.assertGreater(len(script.splitlines()), 40)

    def test_both_thresholds_are_declared_by_the_workflow(self):
        """Read, not remembered: a suite holding its own numbers tests nothing."""
        self.assertEqual(DAYS, 30)
        self.assertGreater(COMMITS, 0)

    def test_the_stub_answers_every_call_the_step_makes(self):
        """A stub exiting 64 unnoticed would look like a pin that was fine."""
        self.caller("ci", NEAR)
        code, out = self.run_step({NEAR: compared(3, 1)})
        self.assertNotIn("gh stub: nothing answers", out)
        self.assertEqual(code, 0, out)

    # --- the refusal this exists for ----------------------------------------

    def test_a_pin_far_behind_but_days_old_is_refused(self):
        """The defect, reproduced: 94 commits behind, 13 days old.

        Healthy under the day rule alone, and the reason `brand` and
        `lemonfiber-media-stack` ran no pin check at all.
        """
        self.caller("ci", FAR)
        code, out = self.run_step({FAR: DEFECT})
        self.assertEqual(code, 1, out)
        self.assertIn("::error::aaaaaaaa is 94 commits and 13 days behind", out)
        self.assertIn(f"more than {COMMITS} commits behind", out)
        self.assertIn("1 pin(s) need attention.", out)

    def test_the_same_pin_goes_green_with_the_distance_rule_relaxed(self):
        """The other half of the claim: distance refused it, not age.

        The identical comparison, with only the commit threshold raised out of
        the way, passes — which is the gate as it stood while the defect lived.
        """
        self.caller("ci", FAR)
        code, out = self.run_step({FAR: DEFECT}, commits=10_000)
        self.assertEqual(code, 0, out)
        self.assertIn("::notice::aaaaaaaa is 94 commits behind", out)
        self.assertNotIn("::error::", out)

    # --- what a pin is behind on, which a count cannot say -------------------

    def test_a_notice_names_the_workflow_this_repo_runs_that_changed(self):
        """The question a distance cannot answer.

        On the day SonarCloud answered 503 for half an hour, every repository's
        pin was inside both thresholds and `hygiene.yml` had gained the fix that
        morning. The count said 23; what somebody needed to read was which of
        the twenty-three.
        """
        self.caller("ci", NEAR)
        code, out = self.run_step(
            {NEAR: compared(23, 2, files=(".github/workflows/hygiene.yml",))}
        )
        self.assertEqual(code, 0, out)
        self.assertIn("and hygiene.yml changed in them", out)

    def test_a_notice_says_so_when_none_of_them_touched_one(self):
        """The other half, and the reason the first sentence means anything.

        Most of what lands in this repository is spec prose and scripts. A
        notice that named a workflow every time would be a notice nobody reads.
        """
        self.caller("ci", NEAR)
        code, out = self.run_step(
            {NEAR: compared(23, 2, files=("10-functional/features/a1.md", "scripts/gate.py"))}
        )
        self.assertEqual(code, 0, out)
        self.assertIn("none of them touched a workflow this repository runs", out)

    def test_a_workflow_this_repo_does_not_run_is_not_named(self):
        """Scoped to what the caller pins, not to what changed.

        `sonar-gate.yml` moving is news for the repositories that call it and
        noise for the ones that do not, and telling everybody about everything is
        how a notice stops being read.
        """
        self.caller("ci", NEAR, shared="hygiene.yml")
        code, out = self.run_step(
            {NEAR: compared(5, 1, files=(".github/workflows/sonar-gate.yml",))}
        )
        self.assertEqual(code, 0, out)
        self.assertIn("none of them touched a workflow this repository runs", out)
        self.assertNotIn("sonar-gate", out)

    def test_two_workflows_from_one_pin_are_both_named(self):
        self.caller("ci", NEAR, shared="hygiene.yml")
        self.caller("release", NEAR, shared="security.yml")
        code, out = self.run_step(
            {
                NEAR: compared(
                    9,
                    1,
                    files=(
                        ".github/workflows/hygiene.yml",
                        ".github/workflows/security.yml",
                        "README.md",
                    ),
                )
            }
        )
        self.assertEqual(code, 0, out)
        self.assertIn("hygiene.yml", out)
        self.assertIn("security.yml", out)
        self.assertNotIn("README.md", out)

    def test_a_refused_pin_says_it_too(self):
        """The sentence is worth more on the failure than on the notice: a pin
        that is being bumped anyway is one somebody wants to know the reason for.
        """
        self.caller("ci", FAR)
        code, out = self.run_step(
            {FAR: compared(94, 13, files=(".github/workflows/hygiene.yml",))}
        )
        self.assertEqual(code, 1, out)
        self.assertIn("and hygiene.yml changed in them", out)
        self.assertIn("whatever has been fixed there has not reached", out)

    def test_a_workflow_changing_does_not_on_its_own_fail_the_run(self):
        """Said, not gated. Failing the moment a shared workflow lands would
        redden every repository on every change here, which is the check people
        route around.
        """
        self.caller("ci", NEAR)
        code, out = self.run_step(
            {NEAR: compared(1, 0, files=(".github/workflows/hygiene.yml",))}
        )
        self.assertEqual(code, 0, out)
        self.assertIn("::notice::", out)
        self.assertNotIn("::error::", out)

    def test_one_commit_past_the_threshold_is_refused(self):
        self.caller("ci", FAR)
        code, out = self.run_step({FAR: compared(COMMITS + 1, 0)})
        self.assertEqual(code, 1, out)
        self.assertIn(f"more than {COMMITS} commits behind", out)

    def test_the_threshold_itself_is_still_a_notice(self):
        """The boundary is inclusive, so a pin exactly at it is not yet a fault."""
        self.caller("ci", FAR)
        code, out = self.run_step({FAR: compared(COMMITS, 0)})
        self.assertEqual(code, 0, out)
        self.assertIn("::notice::", out)
        self.assertNotIn("::error::", out)

    # --- the rule that was already here, kept -------------------------------

    def test_an_old_pin_is_still_refused_though_it_is_close(self):
        """Distance was added beside age, not in place of it."""
        self.caller("ci", NEAR)
        code, out = self.run_step({NEAR: compared(2, DAYS + 1)})
        self.assertEqual(code, 1, out)
        self.assertIn(f"more than {DAYS} days old", out)
        self.assertNotIn("commits behind. Bump", out)

    def test_a_pin_stale_both_ways_says_both(self):
        self.caller("ci", FAR)
        code, out = self.run_step({FAR: compared(COMMITS + 5, DAYS + 5)})
        self.assertEqual(code, 1, out)
        self.assertIn(
            f"more than {DAYS} days old, and more than {COMMITS} commits behind", out
        )

    def test_a_close_recent_pin_passes_as_a_notice(self):
        self.caller("ci", NEAR)
        code, out = self.run_step({NEAR: compared(3, 2)})
        self.assertEqual(code, 0, out)
        self.assertIn("::notice::bbbbbbbb is 3 commits behind", out)

    def test_a_pin_already_at_main_is_current(self):
        self.caller("ci", NEAR)
        code, out = self.run_step({NEAR: compared(0, 0, status="identical")})
        self.assertEqual(code, 0, out)
        self.assertIn("bbbbbbbb is current.", out)
        self.assertNotIn("::notice::", out)

    def test_a_pin_that_names_no_revision_is_refused(self):
        """gh prints its error body on stdout, so this arrives looking like a status."""
        self.caller("ci", GONE)
        code, out = self.run_step({})
        self.assertEqual(code, 1, out)
        self.assertIn("is not a revision of lemonfiber/spec", out)

    def test_a_pin_off_main_is_refused_however_close_it_is(self):
        self.caller("ci", NEAR)
        code, out = self.run_step({NEAR: compared(0, 0, status="diverged")})
        self.assertEqual(code, 1, out)
        self.assertIn("is not on lemonfiber/spec main (diverged)", out)

    def test_a_repository_pinning_nothing_passes(self):
        self.caller("ci")
        code, out = self.run_step({})
        self.assertEqual(code, 0, out)
        self.assertIn("This repository pins no shared workflow.", out)

    # --- it has to be looking at all of them --------------------------------

    def test_every_pin_is_examined_and_a_late_one_still_refuses(self):
        """The failure is in the second file, and the first is fine.

        A loop that stopped at the first healthy pin, or one whose `faults` count
        never reached the exit, would pass this repository while a stale pin sat
        in it.
        """
        self.caller("ci", NEAR)
        self.caller("release", FAR)
        code, out = self.run_step({NEAR: compared(1, 1), FAR: DEFECT})
        self.assertEqual(code, 1, out)
        self.assertIn("bbbbbbbb is 1 commits behind", out)
        self.assertIn("::error::aaaaaaaa", out)
        self.assertIn(NEAR, self.asked())
        self.assertIn(FAR, self.asked())

    def test_two_stale_pins_are_both_counted(self):
        self.caller("ci", FAR, GONE)
        code, out = self.run_step({FAR: DEFECT, GONE: compared(1, DAYS + 9)})
        self.assertEqual(code, 1, out)
        self.assertIn("2 pin(s) need attention.", out)

    def test_it_asks_the_spec_repository_about_main(self):
        self.caller("ci", NEAR)
        self.run_step({NEAR: compared(1, 1)})
        self.assertIn(f"repos/lemonfiber/spec/compare/{NEAR}...main", self.asked())

    def test_the_step_carries_no_workflow_expressions(self):
        """OPS-R28: event-derived text reaches the shell through the environment."""
        self.assertNotIn("${{", step_script())


class TheThresholdIsWhereItWasArguedToBe(unittest.TestCase):
    """The number is a judgement, and a judgement that drifts silently is a guess.

    It was placed between two measured states of the fleet: 60 commits, where the
    last coordinated fan-out deliberately left every healthy repository, and 94,
    where a pin sat while the job reading it could not run at all. Moving it
    should mean re-arguing it here rather than editing one string in a workflow.
    """

    FAN_OUT_LAG = 60
    THE_GAP_THAT_HID_THE_DEFECT = 94

    def test_the_fleets_last_fan_out_would_not_have_reddened(self):
        self.assertGreaterEqual(COMMITS, self.FAN_OUT_LAG)

    def test_the_gap_that_hid_the_defect_would_have(self):
        self.assertLess(COMMITS, self.THE_GAP_THAT_HID_THE_DEFECT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
