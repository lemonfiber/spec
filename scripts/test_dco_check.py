#!/usr/bin/env python3
"""Coverage tests for dco_check.py — GOV-R29, GOV-R30, Q-R66.

The decisions are driven against records in exactly the shape `git log
--format=%H%x00%an%x00%ae%x00%P%x00%b%x01` writes, rather than against commits
built in a temporary repository. What is worth holding here is whose sign-off
counts and who is exempt, and a suite that had to make real commits to reach
those would be testing git as much as this.

The exemptions are the half worth the most care. Both of them are holes by
design — a merge commit and a bot commit have nobody to attest — and a hole
nothing tests is a hole that widens: `is_bot` decides on a suffix, a substring
and one literal address, and each of the three is a line somebody could relax
without noticing what it lets through.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_dco_check.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import dco_check as gate

SIGNED = "Signed-off-by: A Person <a@example.com>"


def record(
    sha: str = "abcdef1234567890",
    name: str = "A Person",
    email: str = "a@example.com",
    parents: str = "1111111",
    body: str = SIGNED,
) -> str:
    """One commit, in the shape git writes it."""
    return "\x00".join([sha, name, email, parents, body]) + "\x01\n"


class WhatItRefuses(unittest.TestCase):
    def test_a_commit_with_no_sign_off_at_all(self):
        found = gate.unsigned(record(body="Just a message.\n"))
        self.assertEqual(len(found), 1)
        self.assertIn("abcdef12", found[0])
        self.assertIn("lacks a matching Signed-off-by", found[0])

    def test_a_sign_off_belonging_to_somebody_else(self):
        found = gate.unsigned(record(body="Signed-off-by: Someone <b@example.com>"))
        self.assertEqual(len(found), 1)

    def test_every_unsigned_commit_is_named_not_the_first(self):
        out = record(sha="1111111111", body="no") + record(sha="2222222222", body="no")
        found = gate.unsigned(out)
        self.assertEqual(len(found), 2)

    def test_a_sign_off_that_is_not_on_its_own_line(self):
        # Trailing text after the address would let a sentence mentioning somebody's
        # address read as their attestation.
        found = gate.unsigned(record(body=f"{SIGNED} and some more"))
        self.assertEqual(len(found), 1)


class WhatItAccepts(unittest.TestCase):
    def test_a_sign_off_matching_the_author(self):
        self.assertEqual(gate.unsigned(record()), [])

    def test_the_address_is_matched_whatever_its_case(self):
        self.assertEqual(
            gate.unsigned(record(email="A.Person@Example.COM", body="Signed-off-by: X <a.person@example.com>")),
            [],
        )

    def test_one_matching_sign_off_among_several(self):
        body = "Signed-off-by: Other <b@example.com>\n" + SIGNED
        self.assertEqual(gate.unsigned(record(body=body)), [])

    def test_a_body_with_the_trailer_after_other_lines(self):
        self.assertEqual(gate.unsigned(record(body=f"Why this happened.\n\n{SIGNED}")), [])


class WhoIsExempt(unittest.TestCase):
    def test_a_merge_commit_has_nobody_to_attest(self):
        self.assertEqual(gate.unsigned(record(parents="1111111 2222222", body="Merge")), [])

    def test_a_name_ending_in_bot(self):
        self.assertEqual(gate.unsigned(record(name="dependabot[bot]", body="bump")), [])

    def test_an_address_carrying_the_bot_marker(self):
        self.assertEqual(
            gate.unsigned(record(email="49699333+dependabot[bot]@users.noreply.github.com", body="bump")),
            [],
        )

    def test_the_one_address_the_forge_authors_as(self):
        self.assertEqual(gate.unsigned(record(email="noreply@github.com", body="update")), [])

    def test_a_person_is_not_exempt_for_looking_like_one(self):
        # The three exemptions are holes by design, and this is the side of each
        # that keeps them holes rather than doors.
        for name, email in (
            ("A Person", "bot@example.com"),
            ("Robot", "robot@example.com"),
            ("A Person", "noreply@example.com"),
        ):
            with self.subTest(name=name, email=email):
                self.assertEqual(len(gate.unsigned(record(name=name, email=email, body="no"))), 1)


class WhatItReads(unittest.TestCase):
    def test_nothing_between_the_two_refs_is_nothing_to_refuse(self):
        self.assertEqual(gate.unsigned(""), [])

    def test_a_record_git_cut_short_is_skipped_rather_than_guessed_at(self):
        self.assertEqual(gate.unsigned("abcdef\x00A Person\x01\n"), [])

    def test_several_commits_are_read_apart_however_long_their_bodies(self):
        # The record separator is what makes that true: a body holding blank lines
        # and its own `\x00` would otherwise run into the next commit.
        body = "A long message.\n\nWith blank lines.\n\n" + SIGNED
        out = record(sha="1111111111", body=body) + record(sha="2222222222", body="no")
        found = gate.unsigned(out)
        self.assertEqual(len(found), 1)
        self.assertIn("22222222", found[0])


class WhatItSays(unittest.TestCase):
    def setUp(self):
        self.real = gate._read
        self.addCleanup(setattr, gate, "_read", self.real)

    def test_a_clean_range_says_so_and_exits_zero(self):
        gate._read = lambda base, head: record()
        self.assertEqual(gate.main(["dco_check.py", "a", "b"]), 0)

    def test_an_unsigned_commit_exits_one(self):
        gate._read = lambda base, head: record(body="no")
        self.assertEqual(gate.main(["dco_check.py", "a", "b"]), 1)

    def test_a_ref_that_is_not_one_is_refused_before_git_is_asked(self):
        def refuse(base, head):
            raise AssertionError("git was asked about a ref that should have been refused")

        gate._read = refuse
        self.assertEqual(gate.main(["dco_check.py", "a; rm -rf /", "b"]), 1)
        self.assertEqual(gate.main(["dco_check.py", "a", "b$(whoami)"]), 1)


class WhatGitIsAsked(unittest.TestCase):
    """The half the tests above stand in for, asked once against a real repository.

    Everything above hands `unsigned` a string, which is the only way to reach the
    decisions without making commits. That leaves the question nothing else asks:
    does the format string still produce records of the shape those tests assume.
    A field added or reordered in `git log --format` would pass every test above
    and report every commit as unsigned.

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
        for n in ("one", "two"):
            (where / f"{n}.txt").write_text(n, encoding="utf-8")
            subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                [*git, "commit", "-q", "-m", f"feat: {n}\n\n{SIGNED}"],
                check=True, capture_output=True,
            )
            shas.append(
                subprocess.run([*git, "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.strip()
            )

        os.chdir(where)
        out = gate._read(*shas)

        self.assertTrue(out.endswith("\x01\n"), "a record no longer ends where one is read to end")
        parts = out.strip("\x01\n").split("\x00")
        self.assertEqual(len(parts), 5, f"a record now carries {len(parts)} fields, not five")
        self.assertEqual(parts[0], shas[1], "the first field is no longer the sha")
        self.assertEqual(parts[1], "A Person", "the second field is no longer the author's name")
        self.assertEqual(parts[2], "a@example.com", "the third field is no longer the address")
        self.assertIn("Signed-off-by", parts[4], "the fifth field is no longer the body")

        self.assertEqual(gate.unsigned(out), [], "a signed-off commit was read as unsigned")


if __name__ == "__main__":
    unittest.main(verbosity=2)
