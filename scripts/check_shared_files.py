#!/usr/bin/env python3
"""Files every repo carries a copy of are checked against their one home.

Two lint configs and a handful of brand assets exist in more than one repository
because the tools and GitHub both read them from the tree they are given. This
checks each copy against the canonical one in ``shared/`` (GOV-R12, Q-R56).

The two directories a repository adopts from rather than is required to carry —
``shared/gates/`` and ``shared/hooks/`` — are read against ``shared/adoption.toml``,
which is where adoption is stated. Without it, a gate a repository never took and
one it deleted last week arrive here as the same silence.

Usage, from the root of the repository being checked::

    check_shared_files.py --canonical <path to a spec checkout> --repo owner/name

Exit 0 = every copy agrees with its home, 1 = at least one does not.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import subprocess
import sys
import tomllib

# The members of `shared/` this file names. Named here rather than at each use so
# the accounting below and the checks above cannot come to mean different files.
#: Hook managers that write `.git/hooks`, which `core.hooksPath` makes inert.
MANAGERS = ("lefthook.yml", "lefthook.yaml", ".lefthook.yml", "captainhook.json")

MARKDOWNLINT = "markdownlint.jsonc"
TYPOS = "typos.toml"
GATES = "gates"
HOOKS = "hooks"
RUFF = "ruff.toml"
ADOPTION = "adoption.toml"

#: The list of repositories the register answers for, relative to a spec checkout.
ORG = "30-repos/repos.toml"

#: The two tables in it. `repo` is the map this specification governs and is what
#: `gen_repos.py` renders; `ungoverned` is the rest of the organisation, which is
#: rendered nowhere. Both are read here, because what decides whether a row is
#: about somebody is whether the organisation has the repository — not whether
#: the map draws it. Reading `repo` alone refused three repositories that call
#: these workflows as unknown, while refusing the row that would have answered
#: for them, so the only way out was to stop running the check.
ORG_TABLES = ("repo", "ungoverned")

#: For each canonical directory whose members are adopted rather than required:
#: where a copy lands in the adopting repository, what to call the set of them,
#: and what a copy that has gone actually costs.
CARRIED = {
    GATES: (
        "scripts",
        "gate scripts",
        ("A gate script decides whether a branch merges, so a copy that is gone "
         "is a merge gate that stopped running"),
    ),
    HOOKS: (
        ".githooks",
        "hooks",
        ("A hook that is gone is a guard that stopped running in every clone "
         "that had it turned on"),
    ),
}


def markdownlint(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The markdownlint config is copied verbatim, key order included."""
    want = canonical / "shared" / MARKDOWNLINT
    got = repo / ".markdownlint.jsonc"
    if not got.is_file():
        return [f"{got.name} is missing; copy {want} to the repo root"]
    if got.read_bytes() != want.read_bytes():
        return [f"{got.name} differs from the canonical copy; replace it with {want}"]
    return []


def typos(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The typos config is a floor: a repo may add entries, never contradict one."""
    want_path = canonical / "shared" / TYPOS
    got_path = repo / TYPOS
    if not got_path.is_file():
        return [f"typos.toml is missing; copy {want_path} to the repo root"]
    want = tomllib.loads(want_path.read_text(encoding="utf-8"))
    got = tomllib.loads(got_path.read_text(encoding="utf-8"))
    problems = []

    want_words = want.get("default", {}).get("extend-words", {})
    got_words = got.get("default", {}).get("extend-words", {})
    if not want_words:
        return [
            (f"shared/{TYPOS} extends no words, so every repository's copy would "
             "pass this having been compared against nothing")
        ]
    for word, value in want_words.items():
        if word not in got_words:
            problems.append(f"typos.toml is missing the shared word {word!r}")
        elif got_words[word] != value:
            problems.append(
                f"typos.toml maps {word!r} to {got_words[word]!r}, shared is {value!r}"
            )

    want_res = want.get("default", {}).get("extend-ignore-re", [])
    got_res = got.get("default", {}).get("extend-ignore-re", [])
    for pattern in want_res:
        if pattern not in got_res:
            problems.append(f"typos.toml is missing the shared pattern {pattern!r}")
    return problems


def ruff(repo: pathlib.Path, canonical: pathlib.Path) -> list[str]:
    """The lint config is a floor one way and a ceiling the other.

    A repository may select more rules than the shared config does. It may not
    select fewer, and it may not ignore something the shared config keeps. The
    asymmetry is the point: adding a rule raises that repository's standard and
    costs nobody anything, while adding an ignore lowers the standard everybody
    is held to while looking like a local decision.

    Not compared byte for byte, as `markdownlint.jsonc` is. Each copy opens with
    a preamble saying what that repository's scripts are and why they are worth
    linting, and those paragraphs are different because the scripts are. What
    has to agree is the two lists and the width.

    Conditional, as `hooks` is: a repository with no Python has nothing to lint,
    and requiring the file would mean carrying a config for a language it does
    not use. Four repositories carry one today, every one of them with the same
    lists — which is four lists that agree until the first is edited.
    """
    got_path = repo / RUFF
    if not got_path.is_file():
        return []

    want = tomllib.loads((canonical / "shared" / RUFF).read_text(encoding="utf-8"))
    got = tomllib.loads(got_path.read_text(encoding="utf-8"))
    problems = []

    want_select = want.get("lint", {}).get("select", [])
    got_select = got.get("lint", {}).get("select", [])
    # The floor read out of an empty list is no floor, and the ignore arm below
    # would then flag every ignore any repository holds. One half goes silent and
    # the other cries wolf, which is how a gate comes to be switched off — and
    # `ruff.toml` has a second legal layout (`[tool.ruff.lint]`) that produces
    # exactly this without anything looking wrong.
    if not want_select:
        return [
            (f"shared/{RUFF} selects no rules, so the floor every repository is "
             "held to was read as empty")
        ]
    for rule in want_select:
        if rule not in got_select:
            problems.append(
                f"ruff.toml does not select {rule!r}, which the shared config does"
            )

    want_ignore = want.get("lint", {}).get("ignore", [])
    got_ignore = got.get("lint", {}).get("ignore", [])
    for rule in got_ignore:
        if rule not in want_ignore:
            problems.append(
                f"ruff.toml ignores {rule!r}, which the shared config does not. "
                f"Silencing a rule here lowers the floor every repository is held "
                f"to; add it to shared/ruff.toml with the reason, or fix what it "
                f"reports"
            )

    want_width = want.get("line-length")
    got_width = got.get("line-length")
    if got_width is not None and want_width is not None and got_width > want_width:
        problems.append(
            f"ruff.toml allows {got_width} columns, shared allows {want_width}"
        )
    return problems


def asset_rows(canonical: pathlib.Path):
    """Yield (digest, path, home_repo, home_path) for each row of the manifest."""
    manifest = canonical / "shared" / "assets.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, path, home = line.split()
        home_repo, home_path = home.split(":", 1)
        yield digest, path, home_repo, home_path


def assets(repo: pathlib.Path, canonical: pathlib.Path, name: str) -> list[str]:
    """Every copy present in this repo matches the file it was taken from.

    In the repository that *is* a row's home, the row is read the other way
    round: the home file is checked against the digest instead. Without that,
    the digest is a number only the copies are ever held to, and the home can
    move away from every copy of it with nothing anywhere saying so. That is
    not a hypothetical — three of the six brand assets here had drifted from
    their homes, and eight repositories carried a wordmark in a colour the
    brand had replaced, each of them in perfect agreement with a record that
    had stopped describing anything.

    It takes nothing away from the home. Brand still changes its own files
    whenever it likes; what it may not do is change one and leave the record
    behind, because the record is what every copy is following. The digest and
    the copies move in the same round, and this is what says so on the day
    rather than months later.
    """
    problems = []
    for digest, path, home_repo, home_path in asset_rows(canonical):
        target = repo / path
        if home_repo == name:
            problems += home(repo / home_path, digest, home_path)
            continue
        if not target.is_file():
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            problems.append(
                f"{path} differs from {home_repo}/{home_path}; "
                f"copy it again rather than editing it here"
            )
    return problems


def home(target: pathlib.Path, digest: str, home_path: str) -> list[str]:
    """The original still hashes to what the manifest says it does."""
    if not target.is_file():
        return [
            (
                f"{home_path} is named as a home in shared/assets.sha256 and is "
                f"not here; every copy of it is following a record of a file "
                f"that is gone"
            )
        ]
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual == digest:
        return []
    return [
        (
            f"{home_path} no longer hashes to what shared/assets.sha256 records "
            f"for it. Changing the original is fine; leaving the record behind "
            f"is not, because every copy of this file is checked against the "
            f"record rather than against the original. Put {actual} in the "
            f"manifest and refresh the copies in the same round (GOV-R12)"
        )
    ]


def manager(repo: pathlib.Path) -> list[str]:
    """A hook-manager config, which cannot run here and turns off the hook that can.

    Not a style preference. `core.hooksPath .githooks` is what makes the pre-push
    guard run at all, and git then reads *only* that directory — so anything a
    manager writes into `.git/hooks` is ignored. lefthook 2.x detects the setting,
    refuses to install, and offers `--reset-hooks-path`, which unsets it. The one
    command that repairs the dead config disables the working one.

    Six repositories carried a `lefthook.yml` and one a `captainhook.json`, none
    of them ever installed, and one named a script that had been renamed
    underneath it. They are all gone. This is what keeps them gone: a file that
    looks like hook configuration, is not, and whose repair is destructive is
    worth refusing by name rather than explaining again later.
    """
    return [
        (
            f"{found} is a hook manager's config, and this repository's hooks are "
            f"files in `.githooks/` reached through `core.hooksPath`. Git reads only "
            f"that directory, so this cannot run — and installing it would unset the "
            f"setting and turn off the pre-push guard with it. Take it out, and put "
            f"the checks in `.githooks/pre-commit` (OPS-R51)"
        )
        for found in MANAGERS
        if (repo / found).is_file()
    ]


def codeowners(repo: pathlib.Path, canonical: pathlib.Path, name: str) -> list[str]:
    """`OPS-R17`: a repo's CODEOWNERS is generated from the registry.

    Required rather than conditional, unlike the hooks above. A hook a repo has
    not adopted is a repo that has not adopted hooks; a missing CODEOWNERS is a
    repo GitHub routes no review request for, and the requirement says each repo
    has one. Five of seven had none, and the absence satisfied "never
    hand-edited" in the only sense anything was asking about.

    Generated here rather than compared against a stored copy, because the file
    is per-repository output rather than a copy of one shared original: the same
    registry produces a different file for each name.
    """
    got = repo / ".github" / "CODEOWNERS"
    generator = canonical / "scripts" / "gen_codeowners.py"
    if not name:
        # Without a name there is nothing to generate for, and comparing against
        # a guess would be worse than saying so.
        return ["--repo was not given, so CODEOWNERS could not be checked"]
    written = subprocess.run(
        [sys.executable, str(generator), name],
        capture_output=True,
        text=True,
        check=False,
    )
    if written.returncode != 0:
        return [
            (
                f"gen_codeowners.py could not generate for {name}: "
                f"{written.stderr.strip() or 'no output'}"
            )
        ]
    if not got.is_file():
        return [
            (
                ".github/CODEOWNERS is missing; generate it with "
                f"`python3 scripts/gen_codeowners.py {name}` from a spec checkout "
                "(OPS-R17)"
            )
        ]
    if got.read_text(encoding="utf-8") != written.stdout:
        return [
            (
                ".github/CODEOWNERS differs from what the registry generates; "
                f"regenerate it with `python3 scripts/gen_codeowners.py {name}` "
                "rather than editing it (OPS-R17)"
            )
        ]
    return []


def register(canonical: pathlib.Path) -> tuple[dict, list[str]]:
    """Every repository's declared adoption, read from `shared/adoption.toml`.

    `shared/gates/` and `shared/hooks/` are adopted per repository, and a check
    that reads absence as *not adopted* cannot tell that from *deleted*. One of
    those two is a merge gate that stopped running and nobody was told. So the
    answer is declared and read here rather than inferred from what a tree
    happens to hold.

    The register failing to arrive is a refusal rather than an org in which
    nobody has adopted anything: a file that is missing, unparsable, naming no
    repository, or naming one with no name at all answers nothing, and
    answering nothing while reporting clean is the whole of what this replaces.
    """
    path = canonical / "shared" / ADOPTION
    if not path.is_file():
        return {}, [
            (f"shared/{ADOPTION} is not here, so every repository reads as having "
             f"adopted nothing, and every copy that has been deleted reads as one "
             f"that was never taken")
        ]
    try:
        held = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as unreadable:
        return {}, [
            (f"shared/{ADOPTION} could not be read, so no repository's copies were "
             f"held to a declaration: {unreadable}")
        ]
    rows = held.get("repo", [])
    if not rows:
        return {}, [
            (f"shared/{ADOPTION} names no repository, so every repository in the "
             f"org would be refused as unknown and none would be compared")
        ]
    named = {row.get("name", ""): row for row in rows}
    if "" in named:
        return {}, [
            (f"shared/{ADOPTION} holds a row with no `name`, which declares "
             f"adoption for nobody")
        ]
    return named, []


def unregistered(canonical: pathlib.Path, rows: dict) -> list[str]:
    """The register answers for every repository in the org, and for no other.

    A repository with no row is refused where it runs — but only where it runs,
    which is somebody else's pull request, weeks later. This is the half that
    fails here instead, on the change that opened the hole: a repository added
    to the org and not to the register, a row for one the org no longer has, and
    a row naming a file `shared/` does not hold.

    The org is both tables of the registry, not the governed map alone. The map
    is what the specification draws and it says in its own prose that the org
    holds repositories it does not list; a repository outside the map still
    calls these workflows, so the question *which shared hooks does it carry*
    is asked about it and has to have an answer.

    The last of those is the same failure as an unaccounted shared file, one
    level up. A row naming a gate that has been renamed is compared against
    nothing, because the comparison walks the canonical directory and never
    reaches a name that is no longer in it.
    """
    listed = canonical / ORG
    if not listed.is_file():
        return [
            (f"{ORG} is not here, so shared/{ADOPTION} was compared against no "
             f"list of repositories and a missing row could not be seen")
        ]
    read = tomllib.loads(listed.read_text(encoding="utf-8"))
    known = [
        one.get("name", "")
        for table in ORG_TABLES
        for one in read.get(table, [])
    ]
    if not known:
        return [
            (f"{ORG} names no repository, so shared/{ADOPTION} was compared "
             f"against nothing and any row could be missing from it")
        ]
    problems = [
        (f"{one} is a repository in {ORG} with no row in shared/{ADOPTION}, so "
         f"nothing records which shared gates and hooks it carries. Add a row "
         f"naming them, an empty list included (Q-R74)")
        for one in known if one not in rows
    ]
    problems += [
        (f"shared/{ADOPTION} holds a row for {one}, which is not a repository "
         f"{ORG} lists in either of its tables. A row nothing is ever checked "
         f"against is a declaration about nobody")
        for one in rows if one not in known
    ]
    for holds in sorted(CARRIED):
        held = {
            one.name for one in (canonical / "shared" / holds).iterdir() if one.is_file()
        }
        problems += [
            (f"shared/{ADOPTION} says {who} carries {holds}/{gone}, which "
             f"shared/{holds}/ does not hold. A row naming a file that is not "
             f"there is compared against nothing")
            for who, row in rows.items()
            for gone in sorted(set(row.get(holds, [])) - held)
        ]
    return problems


def copies(repo: pathlib.Path, canonical: pathlib.Path, name: str, row: dict,
           holds: str) -> list[str]:
    """One canonical directory's members, against what this repository declares.

    Three answers rather than two. A file declared and present is compared byte
    for byte — read as bytes, because reading both as text folds CRLF endings to
    LF and calls a script the kernel will not run identical to the one it would.
    A file declared and absent is refused by name. A file present and undeclared
    is refused too: a copy nobody wrote down is a copy nobody is holding to the
    canonical version, and it is how a second, older gate comes to sit in a
    repository unnoticed.

    Listed from the canonical directory rather than named here, so a file added
    to `shared/gates/` is compared everywhere rather than copied everywhere and
    compared nowhere.
    """
    where, kind, cost = CARRIED[holds]
    names = sorted(
        one.name for one in (canonical / "shared" / holds).iterdir() if one.is_file()
    )
    # An empty directory is zero comparisons and a clean report, which reads as
    # the copies matching — about every repository in the org, and about files
    # that decide merges.
    if not names:
        return [
            (f"shared/{holds}/ holds no file, so no repository's {kind} were "
             f"compared against anything")
        ]
    declared = set(row.get(holds, []))
    complaints = []
    for one in names:
        got = repo / where / one
        want = canonical / "shared" / holds / one
        if one not in declared:
            if got.is_file():
                complaints.append(
                    f"{where}/{one} is here and shared/{ADOPTION} does not record "
                    f"{name} as carrying it. An undeclared copy is one nothing "
                    f"holds to the canonical version: add it to this repository's "
                    f"row, or take the file out (Q-R73)"
                )
            continue
        if not got.is_file():
            complaints.append(
                f"shared/{ADOPTION} records {name} as carrying {where}/{one} and "
                f"it is not here. {cost}. Copy it again from {want}, or take the "
                f"name out of this repository's row in the same change (Q-R73)"
            )
            continue
        if got.read_bytes() != want.read_bytes():
            complaints.append(
                f"{where}/{one} differs from the canonical copy; replace it with {want}"
            )
    return complaints


def hooks(repo: pathlib.Path, canonical: pathlib.Path, name: str,
          row: dict) -> list[str]:
    """The hooks this repository declares it carries.

    Adopted rather than required: a repository that has not turned hooks on is
    not asked for one. What it is asked for is an answer — the hooks it says it
    carries are the hooks it carries, and no others.
    """
    return copies(repo, canonical, name, row, HOOKS)


def gates(repo: pathlib.Path, canonical: pathlib.Path, name: str,
          row: dict) -> list[str]:
    """The gate scripts this repository declares it carries.

    Held to the same three answers as the hooks, and it matters more here. These
    decide whether a branch merges, and a gate that has quietly drifted is worse
    than none because it is trusted — `no_open_codeql_alert.py` spent its whole
    life reading an empty alert list as a clean one, and a repository still
    carrying that version would be reporting a pass it had not earned. A gate
    that has quietly *gone* is worse again, because there is nothing left to
    read.
    """
    return copies(repo, canonical, name, row, GATES)


def adoption(repo: pathlib.Path, canonical: pathlib.Path, name: str) -> list[str]:
    """What this repository declares it carries, and whether it does.

    The register is read once. Where it did not arrive there is one thing to
    say, and saying it three times — once for the register, once for the gates,
    once for the hooks — would turn one broken file into an account of three
    problems. The copies go uncompared in that case, and the run is red with a
    sentence saying exactly which file has to be fixed first.
    """
    rows, refused = register(canonical)
    if refused:
        return refused
    structure = unregistered(canonical, rows)
    if not name:
        return [
            *structure,
            (f"--repo was not given, so shared/{ADOPTION} could not be read for "
             f"this repository and its gates and hooks were compared against "
             f"nothing"),
        ]
    if name not in rows:
        return [
            *structure,
            (f"{name} has no row in shared/{ADOPTION}, so whether it has adopted "
             f"any shared gate or hook is recorded nowhere — and an unknown "
             f"repository is exactly the silence a conditional check reads as a "
             f"pass. Add a row naming what it carries, an empty list included, "
             f"and name the repository in {ORG} too if neither of its tables "
             f"holds it yet (Q-R74)"),
        ]
    return [
        *structure,
        *hooks(repo, canonical, name, rows[name]),
        *gates(repo, canonical, name, rows[name]),
    ]


# Every member of `shared/` that a check above compares, and the ones nothing
# compares because they are not copies. `README.md` documents the directory,
# `assets.sha256` is the manifest `assets()` reads, and `adoption.toml` is the
# register `register()` reads — none of the three is a file any repo carries.
COMPARED = {MARKDOWNLINT, TYPOS, HOOKS, RUFF, GATES}
NOT_A_COPY = {"README.md", "assets.sha256", ADOPTION}


def unaccounted(canonical: pathlib.Path) -> list[str]:
    """What sits in `shared/` that no check here looks at.

    The checks are named one by one below, which is what this directory held when
    they were written. A file added since is copied into every repository by
    whoever adds it and compared in none — and the run still says the copies
    match, which is true of the ones it looked at and reads as an account of all
    of them.

    Dot-named entries are a tool's leavings, not a shared file: every canonical
    member here is undotted and lands in the copying repository under whatever
    name that repository wants (`markdownlint.jsonc` becomes `.markdownlint.jsonc`
    there). Running ruff with `shared/` as the working directory leaves a
    `.ruff_cache/` behind, and this named it as a shared file nothing compares —
    a red check, on every recipe that runs afterwards, about a directory no
    repository has ever carried. A gate that cries about a cache is a gate people
    learn to run past.
    """
    held = {
        one.name for one in (canonical / "shared").iterdir()
        if not one.name.startswith(".")
    }
    missed = sorted(held - COMPARED - NOT_A_COPY)
    if not missed:
        return []
    return [
        f"shared/{name} is compared by nothing here, so a repository's copy of it "
        f"may differ and this check will still pass"
        for name in missed
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default=".", help="path to a lemonfiber/spec checkout")
    ap.add_argument("--repo", default="", help="owner/name of the repo being checked")
    ap.add_argument("--root", default=".", help="root of the repo being checked")
    args = ap.parse_args()

    repo = pathlib.Path(args.root).resolve()
    canonical = pathlib.Path(args.canonical).resolve()
    name = args.repo.split("/")[-1]

    if not (canonical / "shared").is_dir():
        print(f"::error::no shared/ directory under {canonical}")
        return 1

    problems = unaccounted(canonical) + (
        markdownlint(repo, canonical)
        + typos(repo, canonical)
        + ruff(repo, canonical)
        + assets(repo, canonical, name)
        + adoption(repo, canonical, name)
        + manager(repo)
        + codeowners(repo, canonical, name)
    )
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(f"\n{len(problems)} shared file(s) out of step with {canonical / 'shared'}.")
        return 1
    print("shared files: lint configs, brand assets and CODEOWNERS match their one home, "
          "and the hooks and gate scripts here are the ones this repository declares")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
