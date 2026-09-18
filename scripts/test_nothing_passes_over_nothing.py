#!/usr/bin/env python3
"""No gate reports clean about a collection it found nothing in.

The shape this refuses is one defect wearing many costumes. A gate reads a set —
the goals a manifest locks, the repositories it will search, the pages under a
directory, the files a canonical copy names — and answers a question about every
member of it. Where the set comes back empty the loop body never runs, nothing is
appended to `problems`, and the run prints that everything is in order. The answer
is true and it is about nothing, and nobody reading a green tick can tell the
difference.

It is worth its own suite because each instance looks unremarkable in its own
file. `gate.py` refused an empty goal set and searched an empty repository list
without complaint; `check_stageable.py` refused a withdrawn goal and staged a
version that locked none. Each of those is one missing `if`, and the pair of them
is a pattern — so what this holds is the pattern, in the two places it takes.

**A walk that finds nothing, and a gate handed nothing.** The first is answered by
bounding every walk of this repository's own tree with the one answer to which
files are ours, so a walk cannot quietly wander into an agent's worktree or a
vendored copy and report about somebody else's text. The second is answered by
driving each gate with the empty collection and requiring a refusal.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_nothing_passes_over_nothing.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import re
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import attribution_check  # noqa: E402
import check_local_command  # noqa: E402
import check_shared_files  # noqa: E402
import check_stageable  # noqa: E402
import gate  # noqa: E402

#: A walk over this repository's markdown, whoever starts it.
WALKS = re.compile(r'\brglob\("\*\.md"\)')

#: The one answer to which files this repository wrote, by the name every walk
#: that asks it calls it by.
ASKS = "elsewhere("

#: Walks confined to a directory this repository owns outright, and the constant
#: that confines each of them.
#:
#: Not a licence to skip the question. A confined walk cannot meet a worktree or a
#: vendored copy, because both arrive at the root — so the constant named here is
#: what makes the answer true, and the test checks the script still carries it.
SCOPED = {
    "check_binding_order.py": "FEATURES",
    "check_goal_coverage.py": "FEATURES",
    "check_order.py": "FEATURES",
    "gen_redirects.py": "SECTIONS",
}


def walkers() -> set[str]:
    """Every script that walks this repository's markdown."""
    return {
        path.name
        for path in SCRIPTS.glob("*.py")
        if not path.name.startswith("test_")
        and WALKS.search(path.read_text(encoding="utf-8"))
    }


def said(run) -> tuple[int, str]:
    """What a callable printed, and what it returned or exited with."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            code = run()
        except SystemExit as stopped:
            code = stopped.code if isinstance(stopped.code, int) else 1
            if isinstance(stopped.code, str):
                out.write(stopped.code)
    return code, out.getvalue()


class EveryWalkIsBounded(unittest.TestCase):
    """A walk of this tree is bounded, or is confined to a directory we own."""

    def test_the_sweep_found_walks_to_hold(self):
        """Assert what is being read before what it says.

        A pattern that matched nothing would make every assertion below vacuous,
        and the whole file would pass by finding no walkers at all — which is the
        defect this suite exists for, in the suite itself.
        """
        found = walkers()
        self.assertGreater(len(found), 5, f"the sweep found {found}")

    def test_every_walker_is_bounded_or_declared_scoped(self):
        for name in sorted(walkers()):
            with self.subTest(script=name):
                text = (SCRIPTS / name).read_text(encoding="utf-8")
                # The answer rather than the haystack. `assertIn` over a whole script
                # prints the script on failure, which buries the one sentence saying
                # what is wrong under nine hundred lines that are not.
                if name in SCOPED:
                    confined = SCOPED[name] in text
                    self.assertTrue(
                        confined,
                        f"{name} is declared confined to {SCOPED[name]} and no longer "
                        "names it",
                    )
                    continue
                bounded = ASKS in text
                self.assertTrue(
                    bounded,
                    f"{name} walks this tree and never asks which files are ours, so it "
                    "reads an agent's worktree or a vendored copy as this repository's "
                    "own text",
                )

    def test_a_scoped_declaration_names_a_script_that_exists(self):
        """A declaration for a script that is gone is a rule watching nothing."""
        for name in SCOPED:
            with self.subTest(script=name):
                self.assertTrue((SCRIPTS / name).is_file(), f"{name} is not here")
                self.assertIn(name, walkers(), f"{name} no longer walks anything")


class EveryGateRefusesAnEmptyCollection(unittest.TestCase):
    """Handed nothing, a gate refuses rather than reporting about nothing."""

    def test_a_manifest_locking_no_goal_is_refused(self):
        with tempfile.TemporaryDirectory() as where:
            manifest = pathlib.Path(where) / "0.1.0.toml"
            manifest.write_text('version = "0.1.0"\ngoals = []\n', encoding="utf-8")
            code, out = said(lambda: gate.load_goals(manifest))
        self.assertNotEqual(code, 0)
        self.assertIn("locks no goals", out)

    def test_a_search_of_no_repository_is_refused(self):
        code, out = said(lambda: gate.parse_repos([]))
        self.assertNotEqual(code, 0)
        self.assertIn("nowhere to read citations from", out)

    def test_staging_a_version_that_locks_no_goal_is_refused(self):
        problems = check_stageable.unstageable(
            pathlib.Path("0.1.0.toml"), {"status": "planned", "repos": ["lf"]}
        )
        self.assertTrue(
            any("locks no goal" in one for one in problems), f"got {problems}"
        )

    def test_a_commit_range_holding_nothing_is_refused(self):
        was = attribution_check._read
        self.addCleanup(setattr, attribution_check, "_read", was)
        attribution_check._read = lambda base, head: ""
        code, out = said(
            lambda: attribution_check.main(["attribution_check.py", "a", "b"])
        )
        self.assertNotEqual(code, 0)
        self.assertIn("no commit between", out)

    def test_a_canonical_directory_holding_nothing_is_refused(self):
        """Both copy checks read their list from the canonical directory.

        Which is what stops a file being copied everywhere and compared nowhere —
        and costs this: an empty directory is zero comparisons and a clean report.
        """
        with tempfile.TemporaryDirectory() as where:
            canonical = pathlib.Path(where) / "canonical"
            for holds in (check_shared_files.GATES, check_shared_files.HOOKS):
                (canonical / "shared" / holds).mkdir(parents=True)
            repo = pathlib.Path(where) / "repo"
            repo.mkdir()
            for asked in (check_shared_files.gates, check_shared_files.hooks):
                with self.subTest(check=asked.__name__):
                    complaints = asked(repo, canonical, "cli", {})
                    self.assertTrue(
                        complaints, f"{asked.__name__} was happy about nothing"
                    )

    def test_a_register_declaring_nothing_is_refused(self):
        """What the two checks above decide *adoption* by.

        `shared/gates/` and `shared/hooks/` are carried by the repositories that
        declare them, so a register that answers for nobody makes every
        repository unknown and every deleted gate one that was never taken. Read
        as an empty answer it would pass each of them over in silence, which is
        the whole of what declaring adoption replaces.
        """
        with tempfile.TemporaryDirectory() as where:
            canonical = pathlib.Path(where) / "canonical"
            (canonical / "shared").mkdir(parents=True)
            register = canonical / "shared" / check_shared_files.ADOPTION
            for answered in ("# nobody yet\n", '[[repo]]\ngates = []\n'):
                with self.subTest(register=answered):
                    register.write_text(answered, encoding="utf-8")
                    rows, refused = check_shared_files.register(canonical)
                    self.assertFalse(rows)
                    self.assertTrue(refused, "the register was happy about nothing")

    def test_a_repository_describing_nothing_is_refused(self):
        """The claim check reads a sentence, and an empty tree has none.

        Everything it decides is decided by finding prose. A repository with no
        local command, and one whose command carries no description, both arrive
        as *no sentence claims to be CI* — which is the same answer a repository
        whose every claim is honest gives, and is the one answer that must not be
        reported as clean.
        """
        with tempfile.TemporaryDirectory() as where:
            repo = pathlib.Path(where)
            problems, counted = check_local_command.check(repo)
            self.assertTrue(problems, "an empty repository was happy about nothing")
            self.assertEqual(counted, 0)

            (repo / "justfile").write_text("ci: lint\n", encoding="utf-8")
            problems, counted = check_local_command.check(repo)
            self.assertTrue(problems, "an undescribed command was happy about nothing")
            self.assertEqual(counted, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
