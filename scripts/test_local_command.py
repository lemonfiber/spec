#!/usr/bin/env python3
"""Coverage tests for check_local_command.py — the command run before a push says
what it does not run (Q-R57, OPS-R51).

Each case is checked by the message a maintainer would read as well as by the
exit code. The message is the whole of the fix here: the defect is a sentence,
and a refusal that does not quote the sentence leaves somebody guessing which of
five lines in a comment block it meant.

Two things are worth driving beyond the happy path. The **floor** — a repository
with no local command, and one whose command nobody described — because without
it the check reads an empty description, finds no claim in it, and reports that
every claim in the repository is honest. And the **near-misses**, because a check
that refuses an honest sentence is one people delete: a comment that mentions CI
without claiming to be it, and a sentence saying what the command is *not*, both
have to pass.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_local_command.py
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_local_command  # noqa: E402


def run_main(root: pathlib.Path) -> tuple[int, str]:
    """Call check_local_command.main() with argv patched; return (code, output)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["check_local_command", "--root", str(root)]
    try:
        with contextlib.redirect_stdout(out):
            code = check_local_command.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Repo(unittest.TestCase):
    """A repository with one local command, described."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def justfile(self, said: str, recipe: str = "ci: lint test\n") -> None:
        block = "".join(f"# {line}\n" for line in said.splitlines())
        (self.tmp / "justfile").write_text(
            f"default:\n    @just --list\n\n{block}{recipe}", encoding="utf-8")

    def composer(self, said: str | None) -> None:
        document: dict = {"scripts": {"ci": ["@lint", "@test"]}}
        if said is not None:
            document["scripts-descriptions"] = {"ci": said}
        (self.tmp / "composer.json").write_text(
            json.dumps(document, indent=2), encoding="utf-8")

    def package(self, scripts: dict) -> None:
        (self.tmp / "package.json").write_text(
            json.dumps({"scripts": scripts}, indent=2), encoding="utf-8")

    def verdict(self):
        """This repository's exit status, and what the check said about it."""
        return run_main(self.tmp)


class TheFloor(Repo):
    """What the check has to refuse before it can be trusted to pass anything."""

    def test_a_repository_with_no_local_command(self):
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("no local command", said)
        self.assertIn("nothing a contributor can run before a push", said)

    def test_a_justfile_with_no_ci_recipe(self):
        (self.tmp / "justfile").write_text("default:\n    @just --list\n", encoding="utf-8")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("no local command", said)

    def test_a_recipe_nobody_described(self):
        # The state this check would otherwise read as an honest repository: no
        # sentence to find, so no claim to refuse, so a clean report.
        self.justfile("")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("nothing says what it covers", said)

    def test_a_composer_script_with_no_description(self):
        self.composer(None)
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("nothing says what it covers", said)

    def test_an_npm_script_with_no_justfile_beside_it(self):
        self.package({"ci": "npm run lint && npm run test"})
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("npm run ci", said)
        self.assertIn("nothing says what it covers", said)

    def test_a_composer_json_with_no_ci_script_at_all(self):
        # A repository with a composer.json for its dependencies and its gate
        # somewhere else. There is no local command here to describe.
        (self.tmp / "composer.json").write_text(
            json.dumps({"scripts": {"lint": "@php vendor/bin/pint"}}), encoding="utf-8")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("no local command", said)

    def test_a_task_runner_that_will_not_parse(self):
        (self.tmp / "composer.json").write_text("{ not json", encoding="utf-8")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("unreadable composer.json", said)


class TheClaim(Repo):
    """A sentence saying the local command is CI has to say what it leaves out."""

    def test_an_unqualified_claim(self):
        self.justfile("Everything CI runs, in CI's order.")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("says the local command is CI, and it is not", said)
        self.assertIn("Everything CI runs, in CI's order.", said)

    def test_the_refusal_quotes_the_sentence_rather_than_the_block(self):
        # Five lines of comment and one of them is the problem. A refusal naming
        # the file leaves somebody reading all five.
        self.justfile(
            "The gates, in order.\n"
            "\n"
            "Run every check CI runs before pushing.\n"
            "\n"
            "It is quick.")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("Run every check CI runs before pushing.", said)
        self.assertNotIn("The gates, in order.", said)

    def test_a_claim_qualified_in_the_sentence(self):
        self.justfile("Everything CI runs bar the image check, which needs the network.")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)
        self.assertIn("1 sentence(s) claiming to be CI", said)

    def test_a_claim_qualified_the_other_way(self):
        self.composer(
            "Every gate CI runs but backward compatibility, in order; "
            "run `composer bc` for that one.")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)

    def test_a_claim_whose_block_lists_what_is_missing(self):
        # Better than a clause where there are six of them, and the shape the
        # plugin repositories use.
        self.justfile(
            "Every gate CI runs, in the order CI runs them.\n"
            "\n"
            "Four jobs are not here: commitlint, dco, attribution and spec-check,\n"
            "each of which the commit-msg hook answers before the push.")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)

    def test_a_claim_in_a_composer_description(self):
        self.composer("Every check CI runs, in order.")
        code, said = self.verdict()
        self.assertEqual(code, 1, said)
        self.assertIn("Every check CI runs, in order.", said)


class WhatItMustLetThrough(Repo):
    """A check that refuses an honest sentence is a check people delete."""

    def test_a_description_that_makes_no_claim(self):
        self.justfile("The gates this repository's own scripts decide, in order.")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)
        self.assertIn("0 sentence(s)", said)

    def test_a_sentence_saying_what_the_command_is_not(self):
        # `lemonfiber`'s block says the recipe is *not* the thing to run before a
        # push, and explains why. That is not a claim to be CI.
        self.justfile(
            "The whole set locally, for a toolchain bump or a failure to reproduce.\n"
            "\n"
            "Not the command to run before a push: CI runs all of this the moment\n"
            "you push, so running it here first learns nothing sooner.")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)

    def test_two_runners_where_only_one_describes_the_command(self):
        # The two sites drive npm from a justfile. The description is in the
        # justfile and there is nothing wrong with that.
        self.package({"ci": "npm run lint"})
        self.justfile("Everything CI runs bar the browser install, which CI does first.",
                      recipe="ci:\n    npm run ci\n")
        code, said = self.verdict()
        self.assertEqual(code, 0, said)
        self.assertIn("just ci", said)
        self.assertIn("npm run ci", said)


class ItsOwnRepository(unittest.TestCase):
    """The repository this script lives in passes its own check.

    A gate whose own repository fails it is one that gets excluded rather than
    obeyed, and `just ci` runs this here.
    """

    def test_this_repository(self):
        code, said = run_main(HERE.parent)
        self.assertEqual(code, 0, said)


if __name__ == "__main__":
    unittest.main()
