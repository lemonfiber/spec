#!/usr/bin/env python3
"""Governance gate: verify a PR cites spec identifiers that actually exist.

Canonical here in the spec repo; every implementation repo runs it via the
reusable workflow (.github/workflows/spec-check.yml). See 50-governance/.

Enforces:
  GOV-R2  a citation is present
  GOV-R3  every cited identifier exists on spec@main — in the trailer, and in
          the lines this change adds to a file; see `named_in` for where the
          second of those stops and why

`--citation-optional` drops the first of those and keeps the second. It is for
the one event that carries no pull request to read a citation from; see the
comment over the flag.

One author cannot write a trailer, and the gate cites on its behalf: see
`by_dependabot` below (Q-R55).

Ordering (GOV-R4) — that a behavioural change's spec PR merged first — is not
machine-checked here yet; it is verified in review. Hardening this is tracked in
the spec repo, and any change to this script cites GOV-R11.

Usage:
  spec_check.py --spec-dir <path to spec checkout> --text-file <PR body+commits>
                [--diff-file <unified diff of the change>]
                [--pr-author <login of whoever opened the pull request>]
                [--citation-optional]
Exit 0 = pass, 1 = fail (with guidance), 2 = usage error.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from patterns import ADR_FILE, CITE, CITE_ANY, REQ_DEF, REQ_DEF_ROW, SPEC_TRAILER


# Identifiers the spec defines.
def defined_ids(spec_dir: pathlib.Path) -> set[str]:
    ids: set[str] = set()
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        ids.update(REQ_DEF.findall(p.read_text(encoding="utf-8", errors="ignore")))
    dec = spec_dir / "00-overview" / "decisions"
    if dec.is_dir():
        for f in dec.iterdir():
            m = ADR_FILE.match(f.name)
            if m:
                ids.add(f"ADR-{int(m.group(1)):04d}")
    return ids


# A requirement whose row says it is gone, against what its row says about where.
RETIRED = ("*Withdrawn", "*Superseded")


def retired_ids(spec_dir: pathlib.Path) -> dict[str, str]:
    """Identifiers the spec still defines and no longer offers, against why.

    `defined_ids` finds these, because a withdrawal is recorded **in place** — the
    row stays so the number is visibly retired rather than missing, which is what
    stops it being reused. That is the right shape for the spec and the wrong
    answer for a citation: `GOV-R8` retires the number permanently, and the status
    vocabulary says a Superseded one is not citable for new work.

    So the gate has to tell the two apart, and the row already says which it is
    and where the work went. Carrying that sentence into the refusal is the whole
    value: an author who cited `F3-R20` is told it moved to `F8-R12`, rather than
    being told a number that plainly exists does not.
    """
    found: dict[str, str] = {}
    for p in spec_dir.rglob("*.md"):
        if ".git" in p.parts:
            continue
        for rid, cell in REQ_DEF_ROW.findall(p.read_text(encoding="utf-8", errors="ignore")):
            if cell.strip().startswith(RETIRED):
                found[rid] = " ".join(cell.split())
    return found


def cited_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for line in SPEC_TRAILER.findall(text):
        ids.update(CITE_ANY.findall(line))
    return ids


# The files this gate is made of, which it does not read.
#
# `test_spec_check.py` exists to name identifiers that do not resolve: that is
# what a test of "refuse an unknown identifier" is. Reading it would have the
# gate refuse the pull request that teaches it to refuse, and the only way to
# satisfy it would be to write fixtures out of real requirement numbers — which
# would tie the gate's tests to whatever the spec happens to hold this week.
#
# It is the exemption a rule of this shape always needs. A rule against naming a
# requirement has to name one to say what it is refusing, and the honest answer
# is to say so here rather than to let somebody discover it. The list is two
# paths and it is not a pattern: `tests/` anywhere would be a hole wide enough
# to walk a repository through, since a test's own title is exactly the kind of
# citation this check exists to resolve.
OUR_OWN = ("scripts/spec_check.py", "scripts/test_spec_check.py")

# Where a repository declares the same thing about its own fixtures.
#
# This gate is not the only code with a test that must name an identifier
# nothing answers to. The Rust stack renders a withdrawn requirement and asserts
# the strikethrough, and refuses an id past the ceiling by asking for one — four
# lines and one, each deliberately unresolvable. Read without an answer for
# them, check 6 refuses the next pull request that touches such a line, and the
# only way to satisfy it is to write the fixture out of a real requirement
# number, which ties that repository's tests to whatever the spec holds this
# week. That is the gate making the code worse.
#
# **Exact paths, never a pattern.** A repository says which files, one per line,
# and a glob is not accepted: `tests/` anywhere would be a hole wide enough to
# walk a repository through, since a test's own title is exactly the kind of
# citation check 6 exists to resolve.
#
# **Every skip is printed**, because an exemption nobody sees is an exemption
# nobody revisits — and a gate reporting "clean" over files it never opened
# reads exactly like one that read them.
FIXTURES = ".github/spec-check-fixtures"


def declared_fixtures() -> tuple[str, ...]:
    """The paths a repository has declared name identifiers that do not resolve.

    A path that is not there is refused rather than ignored. A declaration
    outlives the file it was written for, and a list carrying an entry that
    stopped applying is one nobody trusts enough to shorten — so the day the
    file moves, the gate says which line to delete.
    """
    listed = pathlib.Path(FIXTURES)
    if not listed.is_file():
        return ()

    declared = []
    for line in listed.read_text(encoding="utf-8").splitlines():
        said = line.split("#", 1)[0].strip()
        if not said:
            continue
        if "*" in said or "?" in said:
            raise Refused(2, f"::error::{FIXTURES} names a pattern, not a path: {said}")
        if not pathlib.Path(said).is_file():
            raise Refused(
                2,
                f"::error::{FIXTURES} names a file that is not there: {said}. "
                "Delete the line, or correct it to the path the fixture moved to.",
            )
        declared.append(said)

    return tuple(declared)


def unread() -> tuple[str, ...]:
    """Every path check 6 does not open, this gate's own and the repository's."""
    declared = declared_fixtures()

    for path in declared:
        print(f"::notice::not read for identifiers, declared in {FIXTURES}: {path}")

    return OUR_OWN + declared


def added_lines(diff: str, skipping: tuple[str, ...] = OUR_OWN) -> list[str]:
    """The lines a diff adds, less the file header that shares their marker.

    Lines under {skipping} are left unread — see {FIXTURES} for why a repository
    may add to that list.
    """
    added: list[str] = []
    reading = True

    for line in diff.splitlines():
        if line.startswith("+++ "):
            reading = line[len("+++ ") :].removeprefix("b/") not in skipping
        elif reading and line.startswith("+"):
            added.append(line[1:])

    return added


def named_in(diff: str, defined: set[str]) -> set[str]:
    """Identifiers this change writes into a file, of families the spec defines.

    `GOV-R3` says every cited identifier exists on spec@main, and until now this
    gate read the pull request's body and its commit messages and nothing else.
    An identifier written into a file — the comment saying which requirement a
    rule keeps, a test's own title, the sentence a refusal prints telling
    somebody what to go and read — is cited in every sense that matters to the
    person who follows it, and was resolved against nothing at all. A digit
    slipped there names a requirement that does not exist, on a line whose whole
    job is to send a reader to one.

    **Added lines only.** A file's existing text is not this change's to answer
    for, and reading the whole file would refuse a pull request over a line
    somebody wrote two years ago — which is the shape of gate that gets switched
    off rather than fixed.

    **Only families the spec defines**, and this is where the rule stops rather
    than where it was convenient to stop. `X-R1..R4` is a placeholder in a doc
    comment meaning *any requirement of any family*; a family the spec has never
    heard of is prose about requirements rather than a citation of one. What
    that costs is worth stating plainly: a slip in the family rather than the
    number — `M1-R62` where `N1-R62` was meant — reads as prose here and is
    passed over. The number is where the slips are, and a rule that refused
    every capital-letter-and-digit token would refuse the writing that explains
    the rules.

    **Retirement is not asked of a file**, for the same reason. A comment
    recording that a number was withdrawn has to name it, and nothing here can
    tell that sentence from a citation. The trailer is where a citation is
    *made*, and that is where `GOV-R8` is enforced.
    """
    families = {rid.split("-", 1)[0] for rid in defined}

    found: set[str] = set()
    for line in added_lines(diff, unread()):
        found.update(
            rid for rid in CITE.findall(line) if rid.split("-", 1)[0] in families
        )
    return found


# The account whose pull requests carry no trailer, and the identifier the gate
# writes for them. Dependabot composes its own commit message and pull request
# body and offers no way to add a line to either, so its pull requests cite
# nothing. GOV-R12 is the identifier that governs a dependency update, and the
# gate supplies it here rather than in the text (Q-R55, ADR-0016).
#
# Supplied, not skipped: GOV-R3 still runs, so GOV-R12 must exist on spec@main
# and the run still prints what it accepted.
#
# The trap, for whoever edits this next: this keys on GitHub's record of who
# opened the pull request, and on nothing else. A label, a title, a branch name
# and a commit's author are all writable by whoever opened the pull request;
# `pull_request.user.login` is not. Widening this to any of them turns the gate
# off for anyone who can type.
DEPENDABOT = "dependabot[bot]"
ROUTINE = "GOV-R12"


def by_dependabot(pr_author: str) -> bool:
    """Whether GitHub says Dependabot opened this pull request."""
    return pr_author == DEPENDABOT


# The event that carries no pull request, and what this gate can still ask of it.
#
# A merge queue tests a batch on a branch of its own — the default branch's tip
# with every queued pull request applied — and the event asking for those checks
# carries no pull request at all: no body, no author, nothing to close. Two of
# the three things GOV-R2 reads are therefore missing, and demanding a trailer
# of what is left would refuse two changes that are not at fault: one whose
# citation sits in its pull request body, which is where GOV-R2 allows it, and
# any batch of Dependabot's, whose allowance keys on an author the event does
# not carry.
#
# So presence stops being required there, and GOV-R3 does not: every identifier
# the batch's commits do cite is still resolved against the spec. That is the
# half of the rule a queue can change — a pull request can wait in one while the
# identifier it cited is withdrawn — and the half GOV-R2 covers was settled
# before the queue accepted it, because a pull request cannot be queued until
# this gate has passed on it.
#
# The trap, for whoever edits this next: what selects this is the *event*, which
# the workflow reads from GitHub's own payload. Nothing a contributor writes can
# reach it. Wire it to a label, a title or a branch name instead and the
# citation rule becomes optional for anyone who can type.
NOTHING_CITED = (
    "spec-check: OK — nothing cited, and presence is not asked on this event. "
    "GOV-R2 was asked of every pull request in this batch before the queue took it."
)


GUIDANCE = """
This change does not cite a spec identifier that exists on spec@main.

The lemonfiber spec is canonical: every change references something already in
https://github.com/lemonfiber/spec

Add a `Spec:` trailer to a commit AND the PR body, for example:

    Spec: B2-R1

  - Implementing something specified?  Cite the requirement.
  - Changing behaviour?  Open a spec PR first, then cite the new ID.
  - Routine maintenance (deps, formatting, CI)?  Cite GOV-R12.

Guide: https://github.com/lemonfiber/spec/blob/main/50-governance/contributing.md
"""


RETIRED_GUIDANCE = """
A retired identifier still appears in the spec, and that is deliberate: the row
stays so the number is visibly gone rather than missing, which is what stops it
being reused. It is not something to build against.

Cite the identifier the row names in its place. Where it names none, the work it
described is gone rather than moved, and what you are doing needs a requirement
that exists.
"""


NAMED_GUIDANCE = """
An identifier written into a file is a citation to whoever reads it. A comment
saying which requirement a rule keeps, a test's title, the sentence a refusal
prints — each sends somebody to the spec, and one naming a number that is not
there sends them nowhere and reads as though the rule rests on something.

Correct the number, or open the spec PR that brings it into being and let it
merge first. Only lines this change adds were read, and only identifiers whose
family the spec defines.
"""


class Refused(Exception):
    """A refusal, carrying the code the gate should leave with.

    Raised rather than returned because the two file arguments are read in the
    middle of gathering input, and threading a sentinel back out through each
    of them is what pushed `main()` past the complexity this repository allows.
    Two is the code for *the gate could not run*, which is not the same answer
    as *the change is wrong* and must never be mistaken for it.
    """

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def within_cwd(arg: str, what: str) -> pathlib.Path:
    """The path an argument names, refused unless it sits under this checkout.

    Both files this gate reads are written by the workflow beside it. A path
    that climbs out of the checkout is the gate reading something the pull
    request did not write.
    """
    path = pathlib.Path(arg).resolve()
    if not path.is_relative_to(pathlib.Path.cwd().resolve()):
        raise Refused(2, f"::error::{what} must be within the working directory")
    return path


def the_diff(arg: str) -> str:
    """What the change writes into files, or nothing where none was asked for."""
    if not arg:
        return ""

    path = within_cwd(arg, "diff-file")
    if not path.is_file():
        # Loud rather than empty. A diff that did not arrive reads exactly like
        # a change that named nothing, and this half of GOV-R3 would then be off
        # in every repo with nobody able to see that it was.
        raise Refused(2, f"::error::diff-file not found: {arg}")

    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    try:
        return gate()
    except Refused as refused:
        print(refused)
        return refused.code


def gate() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--pr-author", default="", help="login that opened the PR")
    ap.add_argument(
        "--diff-file",
        default="",
        help="unified diff of the change; identifiers its added lines name are resolved too",
    )
    ap.add_argument(
        "--citation-optional",
        action="store_true",
        help="citing nothing is not a refusal; GOV-R3 still runs on what is cited",
    )
    a = ap.parse_args()

    spec_dir = pathlib.Path(a.spec_dir)
    if not spec_dir.is_dir():
        print(f"::error::spec dir not found: {spec_dir}")
        return 2

    text = within_cwd(a.text_file, "text-file").read_text(
        encoding="utf-8", errors="ignore"
    )
    diff = the_diff(a.diff_file)

    defined = defined_ids(spec_dir)
    if not defined:
        print("::error::no identifiers found in spec checkout — cannot verify")
        return 2

    # Asked before the trailer is, and asked whatever the trailer turns out to
    # say. A change may cite perfectly and still write a number that is not
    # there into a file, and on a merge group — where presence is not asked and
    # a batch citing nothing returns early below — this would otherwise be the
    # one event that skipped it. GOV-R3 is precisely the half a queue can
    # change while a pull request waits in it.
    named = named_in(diff, defined)
    unnamed = sorted(rid for rid in named if rid not in defined)
    if unnamed:
        print(
            "::error::this change names identifiers that do not exist on spec@main: "
            f"{', '.join(unnamed)}"
        )
        print(NAMED_GUIDANCE)
        return 1

    cited = cited_ids(text)
    if by_dependabot(a.pr_author):
        cited.add(ROUTINE)
    if not cited:
        if a.citation_optional:
            print(NOTHING_CITED)
            return 0
        print("::error::no `Spec:` citation found")
        print(GUIDANCE)
        return 1

    unknown = sorted(i for i in cited if i not in defined)
    if unknown:
        print(f"::error::cited identifiers do not exist on spec@main: {', '.join(unknown)}")
        print(GUIDANCE)
        return 1

    retired = retired_ids(spec_dir)
    gone = sorted(i for i in cited if i in retired)
    if gone:
        for rid in gone:
            print(f"::error::{rid} is retired: {retired[rid]}")
        print(RETIRED_GUIDANCE)
        return 1

    print(f"spec-check: OK — cites {', '.join(sorted(cited))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
