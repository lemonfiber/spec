#!/usr/bin/env python3
"""Write `gates.yml`, the shared checks as one job, from the reusables that define them.

A pull request that called the shared checks one reusable at a time ran a job
for each, most of them for under ten seconds of work after minutes waiting for
one of the organisation's twenty runners (Q-R82). `gates.yml` runs the same
checks as steps of one read-only job, `gates`, whose conclusion is the one
context a branch requires. A second job, `report`, which runs no third-party
tool and judges nothing, does what a check does to the pull request: closes it,
labels it, and posts and removes the comments.

The reusables stay the definition. This script reads them and writes
`gates.yml`, so a change to a check is made once, in its reusable, and the
generated file follows; `generated.py` refuses a `gates.yml` that has drifted.

Each reusable job is one of four kinds:

- a verdict, whose steps run in `gates` and whose result fails `gates`;
- a detector, whose steps run in `gates` to answer a reporter, and whose result
  fails nothing;
- an actor, whose steps write and so run in `report`;
- an explainer, a call to `explain-check.yml`, inlined into `report` as a step.

What a check's own job did, each check's steps still do:

- a check starts from an empty workspace, as its own runner would;
- a step runs only where every step before it in the same check succeeded, and
  a step its reusable lets fail does not stop the ones after it;
- a check's result is failure where one of its steps failed, skipped where the
  caller skipped it or its reusable's job condition was false, and success
  otherwise; one the plan gave no answer for, because it refused, fails `gates`;
- a step that needs a write token runs in `report`, where it reads what the
  check's earlier steps wrote through the `gates` job's outputs, and a job's
  outputs reach the jobs that needed it the same way.

`gates` lists every verdict and its result in the run's summary.

Every check in `gates` shares one runner, so a step that ran code out of a pull
request's tree could change what each later step runs, the step that fails
`gates` included. So no step there does: every action a check bound for `gates`
uses is one named in `INERT`, which reads the tree as data, or one named in
`GUARDED` that comes after the step giving it a tree with nothing to import;
scripts are spec's own; Python starts isolated, so a module the tree holds is
never imported in place of one Python ships; and no script carries an
expression, so what a pull request wrote reaches a shell only through `env`.
The verdict itself runs last, from an empty workspace, outside it.

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


#: The four kinds of job a reusable holds, by where their steps run.
VERDICT, DETECT, ACT, EXPLAIN = "verdict", "detect", "act", "explain"


@dataclass(frozen=True)
class Check:
    """One check: the caller's name for its reusable, the job inside it, and its kind."""

    group: str
    """The name a caller lists to run it, `hygiene` for every hygiene check."""

    source: str
    """The reusable that defines it, under `.github/workflows/`."""

    job: str
    """The job inside the reusable."""

    kind: str = VERDICT
    """Where its steps run, and whether its result fails `gates`."""


HYGIENE = "hygiene.yml"
EXPLAIN_FILE = "explain.yml"
SQUASH = "squash-message.yml"

#: Every check, in the order the jobs run them.
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
    Check("squash-message", SQUASH, "squash-message"),
    Check("explain", EXPLAIN_FILE, "detect", DETECT),
    Check("labeler", "labeler.yml", "label", ACT),
    Check("goals", "goal-automations.yml", "classify", ACT),
    Check("refs", "spec-references.yml", "comment", ACT),
    Check("cap", "pr-cap.yml", "comment", ACT),
    Check("squash-message", SQUASH, "explain", EXPLAIN),
    Check("explain", EXPLAIN_FILE, "citation", EXPLAIN),
    Check("explain", EXPLAIN_FILE, "dco", EXPLAIN),
    Check("explain", EXPLAIN_FILE, "mirror", EXPLAIN),
    Check("explain", EXPLAIN_FILE, "status", EXPLAIN),
)

#: The reusable an explainer calls, which is inlined into `report` as a step.
EXPLAINER = "./.github/workflows/explain-check.yml"

#: Steps of a read-only check that write, by the check and the step's name. They
#: run in `report`, after the check's other steps have run in `gates`.
MOVED = {
    ("spec-check", "spec-check"): frozenset({"Close the pull request, naming what it cited"}),
}

#: Every action a step of `gates` may use, and what it does with the tree it is
#: pointed at. `gates` runs every check on one runner, so one step that ran code
#: out of a pull request's tree could rewrite what every later step runs, the
#: verdict's own included. Each action here reads that tree as data; one not
#: here is refused until somebody has read what it does with the files.
INERT = {
    "actions/checkout": "writes the tree and runs nothing in it: no hooks, no submodules",
    "actions/setup-python": "installs the Python version the step names",
    "crate-ci/typos": "reads text, and its TOML configuration",
    "lycheeverse/lychee-action": "reads links, and its TOML configuration",
}

#: An action that imports code from the tree it reads when the tree asks it to,
#: and the id of the step that must come before it in the same check: the step
#: that puts in its place a tree holding nothing it would import. That step
#: failing skips the action, as any failed step skips the ones after it.
GUARDED = {
    "DavidAnson/markdownlint-cli2-action": "markdown-only",
}

#: The permissions each job holds. `gates` reads, the pull request included, which
#: the squash message is read from; `report` holds what the acting steps need and
#: runs no third-party code.
READ = {"contents": "read", "pull-requests": "read"}
WRITE = {"contents": "read", "pull-requests": "write", "issues": "write"}

#: The condition every step and job that must run after a failure carries.
UNLESS_CANCELLED = "${{ !cancelled() }}"

#: The workspace emptied: before each check, as its own runner had it, and
#: before the verdict, so it runs beside no file a pull request wrote.
EMPTIED = 'find "$GITHUB_WORKSPACE" -mindepth 1 -delete'

#: `report`'s own condition. A fork's pull request is handed a token that cannot
#: write, so `report` does not start for one; `gates` judges it all the same.
ACT_RUNS = (
    "${{ !cancelled() && !(github.event_name == 'pull_request'"
    " && github.event.pull_request.head.repo.full_name != github.repository) }}"
)

#: Python started any way but isolated. Code read from stdin or `-c` runs with
#: `-I`, so neither the working directory, which holds a pull request's tree,
#: nor the environment nor the user's site is on its path: a `json.py` or a
#: `sitecustomize.py` there would otherwise be imported first. A script of spec's
#: own runs with `-E -s`, which is `-I` short of `-P`: its own directory, under
#: `.spec-tooling`, stays first on the path, where its sibling modules are, and
#: the working directory is never on it.
UNISOLATED = re.compile(r"\bpython3?\b(?! -I )(?! -E -s [^\s-])")

#: A step's reference to an earlier step's result.
STEP_REF = re.compile(r"\bsteps\.([A-Za-z0-9_-]+)\.(outputs|outcome|conclusion)\b(?:\.([A-Za-z0-9_-]+))?")

#: The status functions. A step condition that names one decides for itself
#: whether an earlier failure stops it, and the guard written here would change
#: what it meant, so a reusable using one is refused rather than translated.
STATUS = re.compile(r"\b(success|failure|always|cancelled)\s*\(")

#: Keys of a reusable's job this script knows what to do with.
KNOWN_JOB_KEYS = frozenset(
    {"runs-on", "timeout-minutes", "steps", "env", "if", "permissions", "name", "outputs"}
)

#: Keys of an explainer's job, a call to `explain-check.yml`.
EXPLAINER_KEYS = frozenset({"uses", "with", "needs", "permissions", "if"})

#: A reference to another job's output, which `report` reads through `gates`.
NEEDS_REF = re.compile(r"\bneeds\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)\b")

#: An explainer's input, as `explain-check.yml` reads it.
INPUT_REF = re.compile(r"\$\{\{\s*inputs\.([A-Za-z0-9_-]+)\s*\}\}")


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


def vetted(check: Check, job: dict) -> None:
    """Refuse a check bound for `gates` that uses an action nobody has read.

    An action that is guarded is accepted only after the step that guards it.
    """
    seen: set[str] = set()
    for step in job.get("steps") or []:
        action = str(step.get("uses", "")).split("@")[0]
        if action and action not in INERT:
            guard = GUARDED.get(action)
            if guard is None:
                raise Refused(
                    f".github/workflows/{check.source} job {check.job!r} uses {action}, which "
                    f"gates.yml has not been told reads a pull request's tree as data. Read what it "
                    f"does with the files it is pointed at, then name it in INERT or GUARDED"
                )
            if guard not in seen:
                raise Refused(
                    f".github/workflows/{check.source} job {check.job!r} uses {action} with no "
                    f"step {guard!r} before it to refuse a tree that would hand it code"
                )
        seen.add(str(step.get("id", "")))


def unexpanded(where: str, step: dict) -> None:
    """Refuse a script that carries an expression.

    An expression in a script is pasted into the shell before it runs, so text
    a pull request wrote, its title or body, would run as commands. A step reads
    such text through `env` and nowhere else.
    """
    if "${{" in str(step.get("run", "")):
        raise Refused(
            f"{where} has an expression in its script, which pastes what it reads into the "
            f"shell. Pass it through env"
        )


def isolated(where: str, step: dict) -> None:
    """Refuse a script that starts Python where the tree it reads could hand it a module."""
    if UNISOLATED.search(str(step.get("run", ""))):
        raise Refused(
            f"{where} starts Python without isolating it from the working directory, which "
            f"holds a pull request's tree. Run code with `python3 -I`, and a script of "
            f"spec's with `python3 -E -s <path>`"
        )


def writes(read: dict, job: dict) -> bool:
    """Whether the reusable or its job asks for any write permission."""
    held = {**(read.get("permissions") or {}), **(job.get("permissions") or {})}
    return any(level == "write" for level in held.values())


def place(check: Check, read: dict, job: dict) -> None:
    """Refuse a check that writes and is put nowhere a write token is held."""
    if check.kind == ACT:
        return
    if writes(read, job) and (check.group, check.job) not in MOVED:
        raise Refused(
            f".github/workflows/{check.source} asks for a write permission, and gates.yml "
            f"would run job {check.job!r} on a read-only token. Make it an actor, or name "
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
    """A moved step's expressions, reading earlier steps through `needs.gates.outputs`."""

    def swap(match: re.Match) -> str:
        old, kind, key = match.group(1), match.group(2), match.group(3)
        if old not in ids:
            raise Refused(f"a step refers to steps.{old}, which no earlier step of its job is")
        name = f"{ids[old]}--{kind}" + (f"--{key}" if key else "")
        tail = f".{key}" if key else ""
        outputs[name] = f"${{{{ steps.{ids[old]}.{kind}{tail} }}}}"
        return f"needs.gates.outputs.{name}"

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
    """The same question asked from `report`, which reads the plan through `gates`."""
    asked = f"needs.gates.outputs.plan--{check.group} == 'true'"
    own = condition(str(job["if"])) if "if" in job else ""
    return both(asked, own)


class Carrier:
    """One check's steps, carried into `gates` and `report` with the guards its own job gave them.

    `here` and `there` are the steps for `gates` and for `report`; `failing_here`
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
            "run": EMPTIED,
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
        unexpanded(f".github/workflows/{self.check.source} job {self.check.job!r}", step)
        isolated(f".github/workflows/{self.check.source} job {self.check.job!r}", step)
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
        """A step that runs in `report`, reading earlier steps through the `gates` job's outputs."""
        step = walk(step, lambda text: needed(exported(text, self.ids, self.outputs), self.check.source))
        own = exported(own, self.ids, self.outputs) if own else ""
        if self.read_only:
            # A step moved out of a read-only check runs where the steps before
            # it, which ran in `checks`, succeeded.
            reached = f"{self.base}--reached-{index}"
            self.outputs[reached] = f"${{{{ {both(*self.chain_here) or 'true'} }}}}"
            gate = both(self.gate_there, f"needs.gates.outputs.{reached} == 'true'", *self.chain_there, own)
        else:
            gate = both(self.gate_there, *self.chain_there, own)
        return step, gate, self.there, self.failing_there, self.chain_there


def carried(check: Check, job: dict, read_only: bool, outputs: dict[str, str]) -> tuple[list, list, str, str]:
    """A check's steps for `gates` and for `report`, and what fails the check in each.

    A read-only job's own outputs are carried into the `gates` job's, so a job
    that needed it reads them from `report` as `needs.gates.outputs`.
    """
    carrier = Carrier(check, job, read_only, outputs)
    if read_only:
        for name, expression in (job.get("outputs") or {}).items():
            outputs[f"{slug(check)}--out--{name}"] = renamed(str(expression), carrier.ids)
    return (
        carrier.here,
        carrier.there,
        " || ".join(carrier.failing_here),
        " || ".join(carrier.failing_there),
    )


def needed(text: str, source: str) -> str:
    """An expression reading another job of the same reusable, read through `gates`.

    `report` is one job, so a job's `needs.<job>.outputs.<name>` is answered by
    the output `carried` exported for that job. A job the reusable holds that no
    check carries into `gates` is refused rather than read as empty.
    """

    def swap(match: re.Match) -> str:
        job, name = match.group(1), match.group(2)
        if job == "gates":
            # Already read through `gates`, by `exported`.
            return match.group(0)
        for check in CHECKS:
            if check.source == source and check.job == job and check.kind in (VERDICT, DETECT):
                return f"needs.gates.outputs.{slug(check)}--out--{name}"
        raise Refused(f".github/workflows/{source} reads needs.{job}.outputs.{name}, and {job!r} runs nowhere gates.yml reads from")

    return NEEDS_REF.sub(swap, text)


def inputs_of(text: str, given: dict) -> str:
    """`explain-check.yml`'s text with each input replaced by what the explainer passed."""

    def swap(match: re.Match) -> str:
        name = match.group(1)
        if name not in given:
            raise Refused(f"explain-check.yml reads inputs.{name}, which an explainer does not pass")
        return str(given[name]).rstrip("\n")

    return INPUT_REF.sub(swap, text)


def explainer(check: Check, job: dict) -> list:
    """An explainer's call to `explain-check.yml`, as steps of `report`."""
    unknown = sorted(set(job) - EXPLAINER_KEYS)
    if job.get("uses") != EXPLAINER or unknown:
        raise Refused(
            f".github/workflows/{check.source} job {check.job!r} is an explainer and is not "
            f"a plain call to {EXPLAINER}"
        )
    called = job_of(Check(check.group, "explain-check.yml", "explain"), load("explain-check.yml"))
    given = job.get("with") or {}
    own = needed(condition(str(job["if"])), check.source) if "if" in job else ""
    gate = both(
        f"needs.gates.outputs.plan--{check.group} == 'true'",
        condition(str(called["if"])) if "if" in called else "",
        own,
    )
    steps = []
    for index, original in enumerate(called.get("steps") or []):
        unexpanded(".github/workflows/explain-check.yml job 'explain'", original)
        isolated(".github/workflows/explain-check.yml job 'explain'", original)
        step = walk(dict(original), lambda text: needed(inputs_of(text, given), check.source))
        name = step.pop("name", None) or f"step {index + 1}"
        steps.append({
            "name": f"{check.group} / {check.job}: {name}",
            "id": f"{slug(check)}--{index}",
            "if": f"${{{{ {gate} }}}}",
            **step,
            "continue-on-error": True,
            "timeout-minutes": called.get("timeout-minutes", 10),
        })
    return steps


#: The conclusion of a check the plan said nothing about. The publish step reads
#: any word but success, failure and skipped as a check that did not report.
UNREPORTED = "unreported"


def planned(plan: str) -> str:
    """Whether the plan answered for a check, given the expression reading its answer.

    A plan that refused wrote no answer at all, and a check with no answer ran
    nothing: read as "not asked for", it would be published as skipped, which a
    branch's required list accepts.
    """
    return f"{plan} == 'true' || {plan} == 'false'"


def verdict(plan: str, gate: str, failing: str) -> str:
    """A check's conclusion as an expression: unreported, skipped, failure or success."""
    failed = f"({failing}) && 'failure' || 'success'" if failing else "'success'"
    return f"${{{{ !({planned(plan)}) && '{UNREPORTED}' || !({gate}) && 'skipped' || {failed} }}}}"


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
cd "$RUNNER_TEMP"
python3 -I - <<'PY'
import json, os
said = json.loads(os.environ["VERDICTS"])
lines = ["| Check | Result |", "|---|---|"]
for key, conclusion in said.items():
    shown = conclusion if conclusion in ("success", "failure", "skipped") else "did not report"
    lines.append(f"| {key.replace('--', ' / ')} | {shown} |")
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("\n".join(lines) + "\n")
failed = [key for key, conclusion in said.items() if conclusion not in ("success", "skipped")]
for key in failed:
    print(f"::error::{key.replace('--', ' / ')} failed. Its steps above say why.")
raise SystemExit(1 if failed else 0)
PY
"""

HEADER = """\
# The shared checks as one job. GENERATED by scripts/gen_gates.py from the
# reusable workflows each check names below; do not edit this file. Change the
# reusable, then run `python3 scripts/gen_gates.py`. generated.py refuses a
# copy that has drifted (Q-R82).
#
# A caller lists the checks it runs, by group, and skips any of them for an
# event:
#
#   on:
#     pull_request:
#       types: [opened, edited, synchronize, reopened, ready_for_review]
#   jobs:
#     gates:
#       permissions:
#         contents: read
#         pull-requests: write
#         issues: write
#       uses: lemonfiber/spec/.github/workflows/gates.yml@<sha>
#       with:
#         checks: spec-check hygiene workflow-pins security dco attribution commitlint squash-message explain labeler goals refs cap
#
# `gates` holds no write permission and runs every check's steps, each check in
# an empty workspace, each step only where the steps before it in the same check
# succeeded. No step runs code out of the pull request's tree, which is read as
# data. It lists each verdict in the run's summary and fails when one failed, so
# a branch requires `gates / gates` alone, and a pull request from a fork runs it
# as it is. `report` closes, labels, classifies, and posts and removes the
# comments, its own and no one else's; it judges nothing, runs no third-party
# tool, and starts for no pull request from a fork.
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
    for check in CHECKS:
        read = load(check.source)
        if check.kind == EXPLAIN:
            there_steps += explainer(check, (read.get("jobs") or {}).get(check.job) or {})
            continue
        job = job_of(check, read)
        place(check, read, job)
        read_only = check.kind != ACT
        if read_only:
            vetted(check, job)
        here, there, failing_here, _ = carried(check, job, read_only, outputs)
        here_steps += here
        there_steps += there
        if check.kind == VERDICT:
            # The verdict is an expression over the steps' outcomes, which the
            # runner sets. No step writes it, so no step a pull request's files
            # can reach decides another check's conclusion.
            verdicts[slug(check)] = verdict(f"steps.plan.outputs.{check.group}", runs(check, job), failing_here)

    missing = unlisted()
    if missing:
        raise Refused(
            f"{', '.join(missing)} is in a reusable gates.yml is made of and in no check "
            f"there, so it would never run. Add it to CHECKS in scripts/gen_gates.py"
        )
    gates_job = {
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
                "name": "An empty workspace, before the verdict",
                "if": UNLESS_CANCELLED,
                "run": EMPTIED,
            },
            {
                "name": "Every check held",
                "if": UNLESS_CANCELLED,
                "env": {"VERDICTS": json.dumps(verdicts)},
                "run": HELD,
            },
        ],
    }
    report_job = {
        "needs": "gates",
        "if": ACT_RUNS,
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 30,
        "permissions": WRITE,
        "steps": there_steps,
    }
    workflow = {
        "name": "gates",
        "on": {
            "workflow_call": {
                "inputs": {
                    "checks": {
                        "description": "The checks this caller runs, by group, separated by spaces.",
                        "type": "string",
                        "default": " ".join(groups),
                    },
                    "skip": {
                        "description": "Checks to skip for this event, separated by spaces.",
                        "type": "string",
                        "default": "",
                    },
                },
            },
        },
        "permissions": READ,
        "jobs": {"gates": gates_job, "report": report_job},
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
