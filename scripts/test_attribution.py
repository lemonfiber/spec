#!/usr/bin/env python3
"""Nothing credits the tool, and naming the rule is not breaking it (GOV-R46).

`attribution_check.py` reads two things a contributor wrote — the commit bodies
and the pull request body — and refuses the shapes an assistant adds by default.
The subtlety is not in finding them; it is in the three things it must let
through, and each of them is a way a check like this gets switched off:

- **A human co-author.** A co-author trailer is a legitimate thing between two
  people, and a rule that refused every one of them would refuse pair
  programming in order to enforce a rule about robots.
- **Prose naming what is forbidden.** The requirement, the guide, the script's
  own docstring and every commit message explaining any of them have to be able
  to say the word. A rule that fires on its own documentation is a rule somebody
  disables, and the disabling takes the real coverage with it.
- **A quoted trailer.** The same thing one indent in, which is how a message
  shows somebody the line they should remove.

Driven through the module rather than through git: `attributed` is handed text
and decides, which is the half worth holding — building real commits to reach it
would test git as much as this.

Stdlib unittest.
Run:  python3 scripts/test_attribution.py
"""

from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import attribution_check as CHECK


class Refuses(unittest.TestCase):
    """The shapes that actually arrive."""

    def test_a_co_author_trailer_naming_an_assistant(self) -> None:
        said = CHECK.attributed(
            "feat: a thing\n\nSigned-off-by: A Person <a@example.com>\n"
            "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n"
        )
        self.assertEqual(len(said), 1, said)
        self.assertIn("Claude", said[0])

    def test_the_trailer_whatever_its_casing(self) -> None:
        # Git treats the trailer name case-insensitively and so do the tools
        # that write it, so a check matching one spelling catches one tool.
        for spelling in ("Co-authored-by", "Co-Authored-By", "co-authored-by"):
            with self.subTest(spelling=spelling):
                self.assertTrue(
                    CHECK.attributed(f"{spelling}: Copilot <copilot@github.com>\n")
                )

    def test_the_badge_line_a_body_ends_with(self) -> None:
        said = CHECK.attributed(
            "A body.\n\n\N{ROBOT FACE} Generated with [Claude Code](https://claude.com/claude-code)\n"
        )
        self.assertEqual(len(said), 1, said)

    def test_a_badge_without_the_emoji(self) -> None:
        self.assertTrue(CHECK.attributed("Written by Gemini.\n"))

    def test_it_reads_the_pull_request_body_as_well_as_the_commits(self) -> None:
        # A squash merge writes the body into the commit that lands on the
        # default branch, so a clean history and a dirty body are the same thing
        # one merge later.
        said = CHECK.problems("", "The body.\n\nCo-authored-by: Devin <devin@example.com>\n")
        self.assertEqual(len(said), 1, said)
        self.assertIn("the pull request body", said[0])


class Allows(unittest.TestCase):
    """The three ways a rule like this gets switched off."""

    def test_a_human_co_author(self) -> None:
        self.assertEqual(
            CHECK.attributed("Co-authored-by: Wessel Verheij <info@nightworks.io>\n"), []
        )

    def test_prose_naming_what_is_forbidden(self) -> None:
        self.assertEqual(
            CHECK.attributed(
                "This removes the Claude trailer from every commit on the branch.\n"
            ),
            [],
        )

    def test_a_trailer_quoted_one_indent_in(self) -> None:
        # How a message shows somebody the line to remove. A trailer git will
        # read starts the line; a quoted one does not.
        self.assertEqual(
            CHECK.attributed("  Co-authored-by: Claude <noreply@anthropic.com>\n"), []
        )

    def test_an_ordinary_message(self) -> None:
        self.assertEqual(
            CHECK.problems(
                "abc123\x00feat: a thing\x00feat: a thing\n\nWhy.\n\nSpec: GOV-R46\n\x01\n",
                "An ordinary pull request body.\n",
            ),
            [],
        )


class ReadsWhatGitSaid(unittest.TestCase):
    """The record format, which is `dco_check.py`'s and for its reason."""

    def test_it_names_the_commit_and_the_line(self) -> None:
        said = CHECK.problems(
            "abcdef1234\x00feat: a thing\x00feat: a thing\n\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n\x01\n",
            "",
        )
        self.assertEqual(len(said), 1, said)
        self.assertIn("abcdef12", said[0])
        self.assertIn("feat: a thing", said[0])

    def test_a_body_with_blank_lines_is_still_one_commit(self) -> None:
        # The record separator is \x01 rather than a newline precisely because
        # every body has newlines in it.
        said = CHECK.problems(
            "aaaaaaaa\x00fix: one\x00fix: one\n\nA paragraph.\n\nAnother.\n\x01\n"
            "bbbbbbbb\x00fix: two\x00fix: two\n\nCo-authored-by: Aider <a@example.com>\n\x01\n",
            "",
        )
        self.assertEqual(len(said), 1, said)
        self.assertIn("bbbbbbbb", said[0])

    def test_a_record_git_cut_short_is_skipped_rather_than_guessed_at(self) -> None:
        # Two fields where three are read. Guessing which one is missing would
        # mean reporting a subject as a message or a message as a subject.
        self.assertEqual(CHECK.problems("abcdef12\x00feat: a thing\x01\n", ""), [])


class WhatItSays(unittest.TestCase):
    """`main`, with git stubbed — the exit codes the workflow actually reads."""

    def setUp(self) -> None:
        self.addCleanup(setattr, CHECK, "_read", CHECK._read)
        self.addCleanup(setattr, sys, "stdin", sys.stdin)

    def test_a_clean_range_says_so_and_exits_zero(self) -> None:
        CHECK._read = lambda base, head: "abcdef12\x00feat: a thing\x00feat: a thing\n\x01\n"
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b"]), 0)

    def test_a_commit_crediting_one_exits_one(self) -> None:
        CHECK._read = lambda base, head: (
            "abcdef12\x00feat: a thing\x00feat: a thing\n\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n\x01\n"
        )
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b"]), 1)

    def test_a_range_holding_no_commit_is_refused_rather_than_called_clean(self) -> None:
        """Both refs resolve, git is happy, and nothing was read.

        A pull request always carries a commit, so an empty range means the refs
        are not the ones the run was about — and a clean answer over it is a pass
        nobody earned.
        """
        CHECK._read = lambda base, head: "\n"
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b"]), 1)

    def test_the_body_counts_only_where_the_caller_piped_one_in(self) -> None:
        # The flag is what makes stdin part of the answer. Without it a check run
        # by hand would sit waiting on a pipe nobody is filling, and the whole
        # reason the body is read at all — the squash merge — is a CI concern.
        CHECK._read = lambda base, head: "abcdef12\x00feat: a thing\x00feat: a thing\n\x01\n"
        credited = "A body.\n\nCo-authored-by: Codex <codex@example.com>\n"

        sys.stdin = io.StringIO(credited)
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b"]), 0)

        sys.stdin = io.StringIO(credited)
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b", "--body-on-stdin"]), 1)

    def test_a_ref_that_is_not_one_is_refused_before_git_is_asked(self) -> None:
        def refuse(base: str, head: str) -> str:
            raise AssertionError("git was asked about a ref that should have been refused")

        CHECK._read = refuse
        self.assertEqual(CHECK.main(["attribution_check.py", "a; rm -rf /", "b"]), 1)
        self.assertEqual(CHECK.main(["attribution_check.py", "a", "b$(whoami)"]), 1)


class WhatGitIsAsked(unittest.TestCase):
    """The format string, asked once against a real repository.

    Everything above hands `problems` a string, which is the only way to reach
    the decisions without making commits. That leaves the one question nothing
    else asks: does `--format` still produce records of the shape those tests
    assume. A field added or reordered would pass every test above and report
    every commit as clean — a gate that refuses nothing, which is the direction
    of error nobody goes looking for.

    Against a repository built here rather than against this one. CI clones
    shallow, so `HEAD~1` is not a commit there — and a test that only runs where
    the history is deep is a test that does not run where the gate does.
    """

    def test_the_format_produces_the_shape_the_records_above_assume(self) -> None:
        self.addCleanup(os.chdir, os.getcwd())
        where = pathlib.Path(tempfile.mkdtemp())
        git = ["git", "-C", str(where), "-c", "user.name=A Person",
               "-c", "user.email=a@example.com", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q", "-b", "main"], check=True, capture_output=True)
        shas = []
        for name, message in (
            ("one", "feat: one\n\nWhy this happened.\n"),
            ("two", "feat: two\n\nCo-authored-by: Claude <noreply@anthropic.com>\n"),
        ):
            (where / f"{name}.txt").write_text(name, encoding="utf-8")
            subprocess.run([*git, "add", f"{name}.txt"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-q", "-m", message], check=True, capture_output=True)
            shas.append(
                subprocess.run([*git, "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.strip()
            )

        os.chdir(where)
        out = CHECK._read(*shas)

        self.assertTrue(out.endswith("\x01\n"), "a record no longer ends where one is read to end")
        parts = out.strip("\x01\n").split("\x00")
        self.assertEqual(len(parts), 3, f"a record now carries {len(parts)} fields, not three")
        self.assertEqual(parts[0], shas[1], "the first field is no longer the sha")
        self.assertEqual(parts[1], "feat: two", "the second field is no longer the subject")

        said = CHECK.problems(out, "")
        self.assertEqual(len(said), 1, said)
        self.assertIn("feat: two", said[0])


if __name__ == "__main__":
    unittest.main()
