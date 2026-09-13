#!/usr/bin/env python3
"""Coverage tests for commit_lint.py — OPS-R11, Q-R66.

The decisions are driven against records in the shape `git log
--format=%H%x00%s` writes. What is worth holding is which subjects the changelog
generator can read and which it cannot, and building real commits to reach that
would be testing git as much as this.

Every type is driven, not one of them. The list is a string split on `|` and
compiled into an alternation, and a type dropped from it is a type that starts
failing every commit that uses it — on somebody else's branch, at the moment they
are trying to merge.

The skips get the same treatment as the exemptions in `dco_check.py`: `Merge ` and
`Revert ` are holes by design, and this holds them to the trailing space, because
without it `Merged`, `Reverting` and `Merge-of` would walk through.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_commit_lint.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import commit_lint as gate


def record(subject: str, sha: str = "abcdef1234567890") -> str:
    """One commit, in the shape git writes it."""
    return f"{sha}\x00{subject}\n"


class EveryTypeIsAccepted(unittest.TestCase):
    def test_each_type_the_list_names(self):
        for kind in gate.TYPES.split("|"):
            with self.subTest(kind=kind):
                self.assertEqual(gate.unconventional(record(f"{kind}: a thing")), [])

    def test_the_list_is_the_one_the_message_prints(self):
        # The help text builds itself from the same string, so a type added to one
        # and not the other cannot happen — this says so rather than assuming it.
        self.assertEqual(gate.TYPES.replace("|", ", ").split(", "), gate.TYPES.split("|"))


class WhatItAccepts(unittest.TestCase):
    def test_a_scope(self):
        self.assertEqual(gate.unconventional(record("feat(rehearsal): a thing")), [])

    def test_a_scope_carrying_digits_dots_and_dashes(self):
        self.assertEqual(gate.unconventional(record("fix(sdk-php.v2): a thing")), [])

    def test_a_breaking_change_marker(self):
        self.assertEqual(gate.unconventional(record("feat!: a thing")), [])

    def test_a_breaking_change_marker_after_a_scope(self):
        self.assertEqual(gate.unconventional(record("feat(api)!: a thing")), [])

    def test_nothing_between_the_two_refs_is_nothing_to_refuse(self):
        self.assertEqual(gate.unconventional(""), [])


class WhatItRefuses(unittest.TestCase):
    def test_a_subject_that_names_no_type(self):
        found = gate.unconventional(record("just did a thing"))
        self.assertEqual(found, ["abcdef12 just did a thing"])

    def test_a_type_that_is_not_on_the_list(self):
        self.assertEqual(len(gate.unconventional(record("wip: a thing"))), 1)

    def test_a_type_with_no_space_after_the_colon(self):
        self.assertEqual(len(gate.unconventional(record("feat:a thing"))), 1)

    def test_a_type_with_nothing_after_the_colon(self):
        # What follows the colon is what the changelog prints, so an empty one is a
        # changelog entry that says the type and nothing else.
        self.assertEqual(len(gate.unconventional(record("feat: "))), 1)

    def test_a_scope_in_capitals(self):
        self.assertEqual(len(gate.unconventional(record("feat(API): a thing"))), 1)

    def test_a_type_that_merely_starts_with_one(self):
        self.assertEqual(len(gate.unconventional(record("features: a thing"))), 1)

    def test_every_bad_subject_is_named_not_the_first(self):
        out = record("one", sha="1111111111") + record("two", sha="2222222222")
        self.assertEqual(len(gate.unconventional(out)), 2)


class WhatItSkips(unittest.TestCase):
    def test_a_merge_and_a_revert_are_gits_own_words(self):
        for subject in ("Merge branch 'main' into x", "Revert \"feat: a thing\""):
            with self.subTest(subject=subject):
                self.assertEqual(gate.unconventional(record(subject)), [])

    def test_the_skip_needs_the_space_that_makes_it_gits(self):
        # Without it `Merged`, `Reverting` and `Merge-of` walk through, and each is
        # a subject somebody wrote rather than one git did.
        for subject in ("Merged a thing", "Reverting a thing", "Merge-of a thing"):
            with self.subTest(subject=subject):
                self.assertEqual(len(gate.unconventional(record(subject))), 1)


class WhatItSays(unittest.TestCase):
    def setUp(self):
        self.real = gate._read
        self.addCleanup(setattr, gate, "_read", self.real)

    def test_a_clean_range_says_so_and_exits_zero(self):
        gate._read = lambda base, head: record("feat: a thing")
        self.assertEqual(gate.main(["commit_lint.py", "a", "b"]), 0)

    def test_a_bad_subject_exits_one(self):
        gate._read = lambda base, head: record("a thing")
        self.assertEqual(gate.main(["commit_lint.py", "a", "b"]), 1)

    def test_a_ref_that_is_not_one_is_refused_before_git_is_asked(self):
        def refuse(base, head):
            raise AssertionError("git was asked about a ref that should have been refused")

        gate._read = refuse
        self.assertEqual(gate.main(["commit_lint.py", "a; rm -rf /", "b"]), 1)
        self.assertEqual(gate.main(["commit_lint.py", "a", "b$(whoami)"]), 1)


class WhatGitIsAsked(unittest.TestCase):
    """The half the tests above stand in for, asked once against a real repository.

    Everything above hands `unconventional` a string. That leaves the question
    nothing else asks: does the format string still produce records of that shape.
    A field added or reordered would pass every test above and report every commit
    as unconventional.

    Against a repository built here rather than against this one. CI clones
    shallow, so `HEAD~1` is not a commit there — and a test that only runs where
    the history is deep is a test that does not run where the gate does.
    """

    def test_the_format_produces_the_shape_the_records_above_assume(self):
        where = pathlib.Path(tempfile.mkdtemp())
        git = ["git", "-C", str(where), "-c", "user.name=A Person",
               "-c", "user.email=a@example.com", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q", "-b", "main"], check=True, capture_output=True)
        shas = []
        for subject in ("feat: the first thing", "fix: the second thing"):
            (where / subject.split(": ")[1].replace(" ", "-")).write_text("x", encoding="utf-8")
            subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-q", "-m", subject], check=True, capture_output=True)
            shas.append(
                subprocess.run([*git, "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.strip()
            )

        os.chdir(where)
        out = gate._read(*shas)

        line = out.splitlines()[0]
        sha, sep, subject = line.partition("\x00")
        self.assertEqual(sep, "\x00", "the two fields are no longer separated by a NUL")
        self.assertEqual(sha, shas[1], "the first field is no longer the sha")
        self.assertEqual(subject, "fix: the second thing", "the second field is no longer the subject")

        self.assertEqual(gate.unconventional(out), [], "a conventional subject was refused")


if __name__ == "__main__":
    unittest.main(verbosity=2)
