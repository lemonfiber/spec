#!/usr/bin/env python3
"""Write `gates.yml`, the shared gates on two runners, from the reusables that define them.

A repository that calls the shared gates one reusable at a time spends sixteen
runners on a pull request push, most of them for under ten seconds of work, out
of the twenty the organisation has. `gates.yml` runs the same checks on two: a
read-only `checks` job runs every check's steps in turn, and an `act` job, which
holds the write permissions, does what a check does to the pull request and
publishes each check as a check run under the name the branch already requires.

The reusables stay the definition. This script reads them and writes
`gates.yml`, so a change to a check is made once, in its reusable, and the
generated file follows; `generated.py` refuses a `gates.yml` that has drifted.
A pull request from a fork, whose token cannot publish a check run, goes on
calling the reusables as separate jobs.

What a check's own job did, each check's steps still do:

- a check starts from an empty workspace, as its own runner would;
- a step runs only where every step before it in the same check succeeded, and
  a step its reusable lets fail does not stop the ones after it;
- a check's conclusion is failure where one of its steps failed, skipped where
  the caller skipped it or its reusable's job condition was false, and success
  otherwise;
- a step that needs a write token runs in `act`, where it reads what the check's
  earlier steps wrote through the `checks` job's outputs.

Third-party tools run only in `checks`, whose token can read and nothing more.

Run:  python3 scripts/gen_gates.py           # write .github/workflows/gates.yml
      python3 scripts/gen_gates.py --check   # refuse a gates.yml that has drifted
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
OUTPUT = WORKFLOWS / "gates.yml"


@dataclass(frozen=True)
class Check:
    """One check: the caller's job name for its reusable, and the job inside it."""

    group: str
    """What a caller names the job that calls the reusable, `hygiene` in `hygiene / typos`."""

    source: str
    """The reusable that defines it, under `.github/workflows/`."""

    job: str
    """The job inside the reusable."""


HYGIENE = "hygiene.yml"

#: Every check, in the order `checks` runs them. The group names are the ones
#: every caller already gives the jobs that call each reusable, which is what
#: puts `hygiene / typos` in a branch's required list.
CHECKS = (
    Check("spec-check", "spec-check.yml", "spec-check"),
    Check("hygiene", HYGIENE, "actionlint"),
    Check("hygiene", HYGIENE, "pins"),
    Check("hygiene", HYGIENE, "typos"),
    Check("hygiene", HYGIENE, "links"),
    Check("hygiene", HYGIENE, "invite"),
    Check("hygiene", HYGIENE, "shared-files"),
    Check("hygiene", HYGIENE, "lines"),
    Check("hygiene", HYGIENE, "markdown"),
    Check("workflow-pins", "workflow-pins.yml", "workflow-pins"),
    Check("security", "security.yml", "gitleaks"),
    Check("security", "security.yml", "osv-scanner"),
    Check("dco", "dco.yml", "dco"),
    Check("attribution", "attribution.yml", "attribution"),
    Check("commitlint", "commitlint.yml", "commitlint"),
    Check("labeler", "labeler.yml", "label"),
    Check("goals", "goal-automations.yml", "classify"),
)

#: Checks whose every step writes to the pull request, so all of them run in `act`.
ACTING = frozenset({"labeler", "goals"})

#: Steps of a read-only check that write, by the check and the step's name. They
#: run in `act`, after the check's other steps have run in `checks`.
MOVED = {
    ("spec-check", "spec-check"): frozenset({"Close the pull request, naming what it cited"}),
}

#: The permissions each job holds. `act` holds what the acting steps need and
#: what publishing a check run needs, and runs no third-party code.
READ = {"contents": "read"}
WRITE = {"contents": "read", "pull-requests": "write", "issues": "write", "checks": "write"}

#: The condition every step and job that must run after a failure carries.
UNLESS_CANCELLED = "${{ !cancelled() }}"

#: `act`'s own condition. A fork's pull request is answered by the caller's
#: per-reusable jobs, so `act` refuses one itself rather than relying on the
#: caller's condition to keep its write token away from a fork's head.
ACT_RUNS = (
    "${{ !cancelled() && !(github.event_name == 'pull_request'"
    " && github.event.pull_request.head.repo.full_name != github.repository) }}"
)

#: A step's reference to an earlier step's result.
STEP_REF = re.compile(r"\bsteps\.([A-Za-z0-9_-]+)\.(outputs|outcome|conclusion)\b(?:\.([A-Za-z0-9_-]+))?")

#: The status functions. A step condition that names one decides for itself
#: whether an earlier failure stops it, and the guard written here would change
#: what it meant, so a reusable using one is refused rather than translated.
STATUS = re.compile(r"\b(success|failure|always|cancelled)\s*\(")

#: Keys of a reusable's job this script knows what to do with.
KNOWN_JOB_KEYS = frozenset({"runs-on", "timeout-minutes", "steps", "env", "if", "permissions", "name"})


class Refused(ValueError):
    """A reusable this script cannot carry into `gates.yml` without changing what it does."""


def slug(check: Check) -> str:
    """A name for a check that is safe as a step id and an output name."""
    return f"{check.group}--{check.job}"


def condition(text: str) -> str:
    """An `if:` without its `${{ }}`, so it can be joined to others."""
    text = text.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2].strip()
    return text


def load(source: str) -> dict:
    """One reusable, read."""
    path = WORKFLOWS / source
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as missing:
        raise Refused(f".github/workflows/{source} could not be read ({missing.strerror})") from None


def job_of(check: Check, read: dict) -> dict:
    """The job a check is, refused where it holds a key this script cannot carry."""
    jobs = read.get("jobs") or {}
    if check.job not in jobs:
        raise Refused(f".github/workflows/{check.source} has no job {check.job!r}")
    job = jobs[check.job]
    unknown = sorted(set(job) - KNOWN_JOB_KEYS)
    if unknown:
        raise Refused(
            f".github/workflows/{check.source} job {check.job!r} holds {', '.join(unknown)}, "
            f"which gates.yml has no way to carry. Teach scripts/gen_gates.py what it means "
            f"on a shared runner first"
        )
    if job.get("runs-on") != "ubuntu-latest":
        raise Refused(
            f".github/workflows/{check.source} job {check.job!r} runs on "
            f"{job.get('runs-on')!r}, and every check in gates.yml shares one ubuntu-latest runner"
        )
    return job


def writes(read: dict, job: dict) -> bool:
    """Whether the reusable or its job asks for any write permission."""
    held = {**(read.get("permissions") or {}), **(job.get("permissions") or {})}
    return any(level == "write" for level in held.values())


def place(check: Check, read: dict, job: dict) -> None:
    """Refuse a check that writes and is put nowhere a write token is held."""
    if check.group in ACTING:
        return
    if writes(read, job) and (check.group, check.job) not in MOVED:
        raise Refused(
            f".github/workflows/{check.source} asks for a write permission, and gates.yml "
            f"would run job {check.job!r} on a read-only token. Name it in ACTING, or name "
            f"the steps that write in MOVED"
        )


def renamed(text: str, ids: dict[str, str]) -> str:
    """A step's expressions, with each earlier step's id replaced by its id here."""

    def swap(match: re.Match) -> str:
        old, kind, key = match.group(1), match.group(2), match.group(3)
        if old not in ids:
            raise Refused(f"a step refers to steps.{old}, which no earlier step of its job is")
        tail = f".{key}" if key else ""
        return f"steps.{ids[old]}.{kind}{tail}"

    return STEP_REF.sub(swap, text)


def exported(text: str, ids: dict[str, str], outputs: dict[str, str]) -> str:
    """A moved step's expressions, reading earlier steps through `needs.checks.outputs`."""

    def swap(match: re.Match) -> str:
        old, kind, key = match.group(1), match.group(2), match.group(3)
        if old not in ids:
            raise Refused(f"a step refers to steps.{old}, which no earlier step of its job is")
        name = f"{ids[old]}--{kind}" + (f"--{key}" if key else "")
        tail = f".{key}" if key else ""
        outputs[name] = f"${{{{ steps.{ids[old]}.{kind}{tail} }}}}"
        return f"needs.checks.outputs.{name}"

    return STEP_REF.sub(swap, text)


def walk(value, change):
    """Every string in a step, changed."""
    if isinstance(value, str):
        return change(value)
    if isinstance(value, dict):
        return {key: walk(item, change) for key, item in value.items()}
    if isinstance(value, list):
        return [walk(item, change) for item in value]
    return value


def both(*parts: str) -> str:
    """Conditions joined so every one must hold."""
    return " && ".join(f"({part})" for part in parts if part)


def runs(check: Check, job: dict) -> str:
    """Whether the caller asked for this check and its job's own condition holds."""
    asked = f"steps.plan.outputs.{check.group} == 'true'"
    own = condition(str(job["if"])) if "if" in job else ""
    if own and STATUS.search(own):
        raise Refused(f"{check.source} job {check.job!r} decides by a status function: {own}")
    return both(asked, own)


def asked_in_act(check: Check, job: dict) -> str:
    """The same question asked from `act`, which reads the plan through `checks`."""
    asked = f"needs.checks.outputs.plan--{check.group} == 'true'"
    own = condition(str(job["if"])) if "if" in job else ""
    return both(asked, own)


class Carrier:
    """One check's steps, carried into `checks` and `act` with the guards its own job gave them.

    `here` and `there` are the steps for `checks` and for `act`; `failing_here`
    and `failing_there` the outcomes that fail the check in each; `chain_here` and
    `chain_there` the outcomes a later step in the same job waits on.
    """

    def __init__(self, check: Check, job: dict, read_only: bool, outputs: dict[str, str]):
        self.check = check
        self.base = slug(check)
        self.timeout = job.get("timeout-minutes", 10)
        self.env = job.get("env") or {}
        self.moved = MOVED.get((check.group, check.job), frozenset())
        self.read_only = read_only
        self.outputs = outputs
        self.ids: dict[str, str] = {}
        self.here: list = []
        self.there: list = []
        self.chain_here: list[str] = []
        self.chain_there: list[str] = []
        self.failing_here: list[str] = []
        self.failing_there: list[str] = []
        self.gate_here = runs(check, job)
        self.gate_there = asked_in_act(check, job)
        # Each check starts from an empty workspace, as its own runner did, so
        # nothing one check checked out or wrote is read by the next.
        (self.here if read_only else self.there).append({
            "name": f"{check.group} / {check.job}: an empty workspace, as its own runner had",
            "id": f"{self.base}--fresh",
            "if": f"${{{{ {self.gate_here if read_only else self.gate_there} }}}}",
            "run": 'find "$GITHUB_WORKSPACE" -mindepth 1 -delete',
        })
        for index, original in enumerate(job.get("steps") or []):
            self.carry(index, dict(original))

    def carry(self, index: int, step: dict) -> None:
        """One step, into the job it belongs in, guarded as its own job guarded it."""
        own = condition(str(step.pop("if"))) if "if" in step else ""
        if own and STATUS.search(own):
            raise Refused(
                f"{self.check.source} job {self.check.job!r} has a step deciding by a status function: {own}"
            )
        tolerated = bool(step.pop("continue-on-error", False))
        old_id = step.pop("id", None)
        new_id = f"{self.base}--{old_id or index}"
        name = step.pop("name", None) or step.get("uses", "").split("@")[0] or f"step {index + 1}"
        if not self.read_only or name in self.moved:
            step, gate, target, failing, chain = self.for_act(index, step, own)
        else:
            step = walk(step, lambda text: renamed(text, self.ids))
            gate = both(self.gate_here, *self.chain_here, renamed(own, self.ids) if own else "")
            target, failing, chain = self.here, self.failing_here, self.chain_here
        if self.env:
            step["env"] = {**self.env, **(step.get("env") or {})}
        target.append({
            "name": f"{self.check.group} / {self.check.job}: {name}",
            "id": new_id,
            "if": f"${{{{ {gate} }}}}",
            **step,
            "continue-on-error": True,
            "timeout-minutes": self.timeout,
        })
        self.ids[old_id or str(index)] = new_id
        if not tolerated:
            failing.append(f"steps.{new_id}.outcome == 'failure'")
            chain.append(f"steps.{new_id}.outcome != 'failure'")

    def for_act(self, index: int, step: dict, own: str) -> tuple[dict, str, list, list, list]:
        """A step that runs in `act`, reading earlier steps through the `checks` job's outputs."""
        step = walk(step, lambda text: exported(text, self.ids, self.outputs))
        own = exported(own, self.ids, self.outputs) if own else ""
        if self.read_only:
            # A step moved out of a read-only check runs where the steps before
            # it, which ran in `checks`, succeeded.
            reached = f"{self.base}--reached-{index}"
            self.outputs[reached] = f"${{{{ {both(*self.chain_here) or 'true'} }}}}"
            gate = both(self.gate_there, f"needs.checks.outputs.{reached} == 'true'", *self.chain_there, own)
        else:
            gate = both(self.gate_there, *self.chain_there, own)
        return step, gate, self.there, self.failing_there, self.chain_there


def carried(check: Check, job: dict, read_only: bool, outputs: dict[str, str]) -> tuple[list, list, str, str]:
    """A check's steps for `checks` and for `act`, and what fails the check in each."""
    carrier = Carrier(check, job, read_only, outputs)
    return (
        carrier.here,
        carrier.there,
        " || ".join(carrier.failing_here),
        " || ".join(carrier.failing_there),
    )


def verdict(gate: str, failing: str) -> str:
    """A check's conclusion as an expression: skipped, failure or success."""
    failed = f"({failing}) && 'failure' || 'success'" if failing else "'success'"
    return f"${{{{ !({gate}) && 'skipped' || {failed} }}}}"


PLAN = r"""set -euo pipefail
# The checks run the canonical copies of spec's scripts, from its `main`. In the
# spec repository a step chooses the pull request's own copy instead, and that
# copy would share this runner with every other check, so spec's pull requests
# test their scripts in spec's own jobs and never call this. A
# `pull_request_target` caller would hand the checks a base-branch context over
# a pull request's files; this is called from `pull_request`, `merge_group` and
# `push` only.
if [ "${REPO}" = "lemonfiber/spec" ]; then
  echo "::error::lemonfiber/spec runs its gates as its own workflows, so its pull requests' scripts never share a runner with another check's verdict."
  exit 1
fi
case "${EVENT}" in
pull_request | merge_group | push) ;;
*)
  echo "::error::The shared gates are called from pull_request, merge_group or push, not ${EVENT}."
  exit 1
  ;;
esac
# A check runs when the caller lists it and does not skip it. The lists are
# words separated by spaces, and a word that names no check is refused, so a
# misspelt name cannot quietly run nothing.
known=" ${KNOWN} "
for word in ${CHECKS} ${SKIP}; do
  case "$known" in
  *" ${word} "*) ;;
  *)
    echo "::error::${word} is not one of the shared gates. They are:${known% }"
    exit 1
    ;;
  esac
done
for group in ${KNOWN}; do
  case " ${CHECKS} " in
  *" ${group} "*)
    case " ${SKIP} " in
    *" ${group} "*) echo "${group}=false" >>"$GITHUB_OUTPUT" ;;
    *) echo "${group}=true" >>"$GITHUB_OUTPUT" ;;
    esac
    ;;
  *) echo "${group}=false" >>"$GITHUB_OUTPUT" ;;
  esac
done
"""

HELD = r"""set -euo pipefail
python3 - <<'PY'
import json, os
said = json.loads(os.environ["VERDICTS"])
failed = sorted(key for key, conclusion in said.items() if conclusion == "failure")
for key in failed:
    print(f"::error::{key.replace('--', ' / ')} failed. Its steps above say why.")
raise SystemExit(1 if failed else 0)
PY
"""

PUBLISH = r"""set -euo pipefail
python3 - <<'PY'
import json, os, urllib.request

# Each check, as the caller's branch requires it: `hygiene / typos` where the
# caller calls the reusable from a job named `hygiene`, or `typos` alone.
listed = json.loads(os.environ["LISTED"])
said = json.loads(os.environ["VERDICTS"])
bare = os.environ["NAMES"] == "job"
url = f"{os.environ['GITHUB_API_URL']}/repos/{os.environ['GITHUB_REPOSITORY']}/check-runs"
details = (f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
           f"/actions/runs/{os.environ['GITHUB_RUN_ID']}")
asked = set(os.environ["CHECKS"].split())
unpublished = []
for group, job, key in listed:
    if group not in asked:
        continue
    name = job if bare else f"{group} / {job}"
    conclusion = said.get(key) or ""
    if conclusion not in ("success", "failure", "skipped"):
        # A check that reported nothing is a runner lost or a job cut short. It
        # is published as failed, because a required check that never appears
        # is read as waiting and one that appears green would be a lie.
        summary = "This check did not report a conclusion, so it is published as failed."
        conclusion = "failure"
    else:
        summary = f"The `{name}` check ran in the shared gates; its steps are in the run's log."
    body = json.dumps({
        "name": name,
        "head_sha": os.environ["HEAD_SHA"],
        "status": "completed",
        "conclusion": conclusion,
        "details_url": details,
        "output": {"title": f"{name}: {conclusion}", "summary": summary},
    }).encode()
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            print(f"{name}: {conclusion} (HTTP {answer.status})")
    except Exception as error:  # every refusal is named below, none is swallowed
        unpublished.append(f"{name} ({error})")
for one in unpublished:
    print(f"::error::{one} could not be published, so it is missing from the merge box.")
raise SystemExit(1 if unpublished else 0)
PY
"""

HEADER = """\
# The shared gates on two runners. GENERATED by scripts/gen_gates.py from the
# reusable workflows each check names below; do not edit this file. Change the
# reusable, then run `python3 scripts/gen_gates.py`. generated.py refuses a
# copy that has drifted (Q-R77).
#
# A caller lists the checks it runs, by the names it gives the jobs that would
# call each reusable, and skips any of them for an event:
#
#   gates:
#     if: >-
#       !(github.event_name == 'pull_request'
#         && github.event.pull_request.head.repo.full_name != github.repository)
#     permissions:
#       contents: read
#       pull-requests: write
#       issues: write
#       checks: write
#     uses: lemonfiber/spec/.github/workflows/gates.yml@<sha>
#     with:
#       checks: spec-check hygiene workflow-pins security dco attribution commitlint labeler
#       skip: ${{ github.event_name != 'pull_request' && 'labeler' || '' }}
#
# A pull request from a fork is handed a token that cannot publish a check run,
# so a caller keeps its jobs calling each reusable for that case alone, under
# the condition above negated; they report under the same names.
#
# `checks` holds no write permission and runs every check's steps, each check in
# an empty workspace, each step only where the steps before it in the same check
# succeeded. `act` labels, classifies and closes, and publishes every check as a
# check run with that check's own conclusion. A check that reported nothing is
# published as failed. `act` runs for no pull request from a fork, whatever the
# caller's condition says.
"""


def unlisted() -> list[str]:
    """Every job a source reusable holds that no check names.

    A job added to a reusable is a context a caller's branch can require, and a
    gates.yml that left it out would never publish it: the pull request waits on
    a check that cannot arrive. So every job of every source is a check here, or
    the generator refuses.
    """
    named = {(check.source, check.job) for check in CHECKS}
    missing = []
    for source in dict.fromkeys(check.source for check in CHECKS):
        for job in (load(source).get("jobs") or {}):
            if (source, job) not in named:
                missing.append(f".github/workflows/{source} job {job!r}")
    return missing


def build() -> str:
    """The text of gates.yml."""
    groups = list(dict.fromkeys(check.group for check in CHECKS))
    here_steps: list = []
    there_steps: list = []
    outputs: dict[str, str] = {f"plan--{group}": f"${{{{ steps.plan.outputs.{group} }}}}" for group in groups}
    verdicts: dict[str, str] = {}
    here_verdicts: dict[str, str] = {}
    listed = []
    for check in CHECKS:
        read = load(check.source)
        job = job_of(check, read)
        place(check, read, job)
        read_only = check.group not in ACTING
        here, there, failing_here, failing_there = carried(check, job, read_only, outputs)
        here_steps += here
        there_steps += there
        key = slug(check)
        display = job.get("name") or check.job
        listed.append([check.group, display, key])
        if read_only:
            # The verdict is an expression over the steps' outcomes, which the
            # runner sets. No step writes it, so no step a pull request's files
            # can reach decides another check's conclusion.
            outputs[key] = here_verdicts[key] = verdict(runs(check, job), failing_here)
            if failing_there:
                verdicts[key] = (
                    f"${{{{ needs.checks.outputs.{key} == 'success' && ({failing_there}) "
                    f"&& 'failure' || needs.checks.outputs.{key} }}}}"
                )
            else:
                verdicts[key] = f"${{{{ needs.checks.outputs.{key} }}}}"
        else:
            verdicts[key] = verdict(asked_in_act(check, job), failing_there)

    missing = unlisted()
    if missing:
        raise Refused(
            f"{', '.join(missing)} is in a reusable gates.yml is made of and in no check "
            f"there, so it would never be published. Add it to CHECKS in scripts/gen_gates.py"
        )
    checks_job = {
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 60,
        "permissions": READ,
        "outputs": outputs,
        "steps": [
            {
                "name": "Which checks this caller runs",
                "id": "plan",
                "env": {
                    "REPO": "${{ github.repository }}",
                    "EVENT": "${{ github.event_name }}",
                    "KNOWN": " ".join(groups),
                    "CHECKS": "${{ inputs.checks }}",
                    "SKIP": "${{ inputs.skip }}",
                },
                "run": PLAN,
            },
            *here_steps,
            {
                "name": "Every check that ran here held",
                "if": UNLESS_CANCELLED,
                "env": {"VERDICTS": json.dumps(here_verdicts)},
                "run": HELD,
            },
        ],
    }
    act_job = {
        "needs": "checks",
        "if": ACT_RUNS,
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 30,
        "permissions": WRITE,
        "steps": [
            *there_steps,
            {
                "name": "Publish each check under the name the branch requires",
                "if": UNLESS_CANCELLED,
                "env": {
                    "GH_TOKEN": "${{ github.token }}",
                    "HEAD_SHA": "${{ github.event.pull_request.head.sha || github.event.merge_group.head_sha || github.sha }}",
                    "NAMES": "${{ inputs.names }}",
                    "CHECKS": "${{ inputs.checks }}",
                    "LISTED": json.dumps(listed),
                    "VERDICTS": json.dumps(verdicts),
                },
                "run": PUBLISH,
            },
        ],
    }
    workflow = {
        "name": "gates",
        "on": {
            "workflow_call": {
                "inputs": {
                    "checks": {
                        "description": "The checks this caller runs, by the names of the jobs that would call each reusable, separated by spaces.",
                        "type": "string",
                        "default": " ".join(groups),
                    },
                    "skip": {
                        "description": "Checks to publish as skipped for this event, separated by spaces.",
                        "type": "string",
                        "default": "",
                    },
                    "names": {
                        "description": "`caller` publishes `hygiene / typos`; `job` publishes `typos`.",
                        "type": "string",
                        "default": "caller",
                    },
                },
            },
        },
        "permissions": READ,
        "jobs": {"checks": checks_job, "act": act_job},
    }
    return HEADER + dump(workflow)


class Literal(str):
    """A string written as a block, which is how a script reads best."""


def _literal(dumper: yaml.SafeDumper, value: Literal):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")


def _string(dumper: yaml.SafeDumper, value: str):
    if "\n" in value:
        return _literal(dumper, Literal(value))
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


class Dumper(yaml.SafeDumper):
    """A dumper that writes scripts as blocks, never sorts a key, and repeats a
    value rather than writing an anchor a reader has to chase."""

    def ignore_aliases(self, data) -> bool:
        return True


Dumper.add_representer(str, _string)
Dumper.add_representer(Literal, _literal)


#: A pinned action and the version its comment names, as a reusable writes it.
PINNED = re.compile(r"uses: (?P<ref>[^\s@]+@[0-9a-f]{40}) # (?P<version>\S[^\n]*)")

#: A pinned action as the dumper writes it, at the end of its line.
DUMPED = re.compile(r"uses: (?P<ref>[^\s@]+@[0-9a-f]{40})$", re.MULTILINE)


def versions() -> dict[str, str]:
    """Every pinned action's version comment, read from the reusables gates.yml is made of.

    A dumped YAML file loses its comments, and the comment beside a pin is what
    names the version a reader and the dependency bot compare. Two reusables
    pinning one revision under two different names is refused, because the
    generated file can carry only one.
    """
    found: dict[str, str] = {}
    for source in dict.fromkeys(check.source for check in CHECKS):
        for match in PINNED.finditer((WORKFLOWS / source).read_text(encoding="utf-8")):
            ref, version = match.group("ref"), match.group("version").rstrip()
            if found.setdefault(ref, version) != version:
                raise Refused(f"{ref} is called {found[ref]!r} in one reusable and {version!r} in another")
    return found


def dump(workflow: dict) -> str:
    """The workflow as YAML, `on` written as the word GitHub reads and each pin with its version."""
    text = yaml.dump(workflow, Dumper=Dumper, sort_keys=False, width=1000, allow_unicode=True)
    text = text.replace("\n'on':\n", "\non:\n", 1)
    named = versions()

    def comment(match: re.Match) -> str:
        line, ref = match.group(0), match.group("ref")
        if ref not in named:
            raise Refused(f"{ref} is pinned with no version comment in the reusable that calls it")
        return f"{line} # {named[ref]}"

    return DUMPED.sub(comment, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="refuse a gates.yml that has drifted")
    args = parser.parse_args(argv)
    try:
        text = build()
    except Refused as refused:
        print(f"::error::{refused}", file=sys.stderr)
        return 1
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != text:
            print(
                "::error file=.github/workflows/gates.yml::gates.yml is not what "
                "scripts/gen_gates.py writes from the reusables it is generated from. "
                "Run `python3 scripts/gen_gates.py` and commit the result",
                file=sys.stderr,
            )
            return 1
        print("gates.yml is what the reusables say")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print("wrote .github/workflows/gates.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
