#!/usr/bin/env python3
"""What the generated-file check refuses, and what it says while refusing.

The thing being pinned here is the message. A bare `git diff --exit-code` is
already correct about whether a file moved; what it cannot say is which of four
generators owns it, what command rewrites it, or that hand-editing it was the
mistake. So the tests that matter are the ones that read the refusal.

Beside them, the three silences. A registry with nothing in it, a registry
naming a file that is not there, and a git that could not answer all produce the
same clean-looking run as a repository where nothing moved, and each has to
refuse instead.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_generated.py
"""

from __future__ import annotations

import io
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import generated

ONE = generated.Generated(
    generator="scripts/gen_thing.py",
    recipe="python3 scripts/gen_thing.py",
    paths=("thing.md",),
    owns="the table",
)


class TheRegistry(unittest.TestCase):
    def test_every_entry_names_a_script_and_a_file_that_exist(self):
        for entry in generated.GENERATED:
            with self.subTest(entry.generator):
                self.assertTrue((generated.ROOT / entry.generator).exists())
                for path in entry.paths:
                    self.assertTrue((generated.ROOT / path).exists())

    def test_a_path_is_written_by_one_generator_only(self):
        seen: dict[str, str] = {}
        for entry in generated.GENERATED:
            for path in entry.paths:
                self.assertNotIn(path, seen, f"{path} is claimed twice")
                seen[path] = entry.generator

    def test_the_owner_of_a_path_is_the_entry_that_writes_it(self):
        self.assertEqual(
            generated.owner_of("10-functional/features/BOARD.md").generator,
            "scripts/gen_board.py",
        )

    def test_nothing_owns_a_path_no_generator_writes(self):
        self.assertIsNone(generated.owner_of("README.md"))

    def test_the_listing_pairs_each_file_with_its_generator(self):
        out = io.StringIO()
        self.assertEqual(generated.listing(out), 0)
        rows = [line.split("\t") for line in out.getvalue().splitlines()]
        self.assertEqual(
            len(rows), sum(len(e.paths) for e in generated.GENERATED)
        )
        self.assertIn(
            ["30-repos/README.md", "scripts/gen_repos.py", "python3 scripts/gen_repos.py"],
            rows,
        )


class TheRefusal(unittest.TestCase):
    def test_it_names_the_file_the_generator_and_the_command(self):
        said = generated.refusal(ONE, "thing.md")
        self.assertIn("thing.md", said)
        self.assertIn("scripts/gen_thing.py", said)
        self.assertIn("python3 scripts/gen_thing.py", said)

    def test_it_says_the_file_is_generated_and_what_to_edit_instead(self):
        said = generated.refusal(ONE, "thing.md")
        self.assertIn("edit the source, not the file", said)
        self.assertIn("the table", said)

    def test_it_says_why_the_rule_exists(self):
        self.assertIn("drifts", generated.refusal(ONE, "thing.md"))


class TheSilences(unittest.TestCase):
    def test_an_empty_registry_refuses_rather_than_reporting_a_clean_tree(self):
        out = io.StringIO()
        with mock.patch.object(generated, "GENERATED", ()):
            self.assertEqual(generated.check(out), 1)
        self.assertIn("nothing was compared", out.getvalue())

    def test_a_registered_file_that_is_not_there_refuses(self):
        out = io.StringIO()
        with mock.patch.object(generated, "GENERATED", (ONE,)):
            self.assertEqual(generated.check(out), 1)
        self.assertIn("scripts/gen_thing.py", out.getvalue())
        self.assertIn("silently stops", out.getvalue())

    def test_a_git_that_cannot_answer_refuses(self):
        out = io.StringIO()
        with mock.patch.object(generated, "run", return_value=None), mock.patch.object(
            generated, "moved", return_value=None
        ):
            self.assertEqual(generated.check(out), 1)
        self.assertIn("compared nothing", out.getvalue())


class TheRun(unittest.TestCase):
    def test_a_generator_that_refuses_stops_the_check_and_is_quoted(self):
        out = io.StringIO()
        with mock.patch.object(generated, "run", return_value="no repository table found"):
            self.assertEqual(generated.check(out), 1)
        self.assertIn("no repository table found", out.getvalue())

    def test_a_tree_that_matches_passes(self):
        out = io.StringIO()
        with mock.patch.object(generated, "run", return_value=None), mock.patch.object(
            generated, "moved", return_value=[]
        ):
            self.assertEqual(generated.check(out), 0)

    def test_a_file_that_moved_is_refused_with_its_owner_named(self):
        out = io.StringIO()
        with mock.patch.object(generated, "run", return_value=None), mock.patch.object(
            generated, "moved", return_value=["30-repos/README.md"]
        ):
            self.assertEqual(generated.check(out), 1)
        self.assertIn("scripts/gen_repos.py", out.getvalue())

    def test_run_reports_what_a_refusing_generator_said(self):
        done = mock.Mock(returncode=1, stderr="no counting sentence found", stdout="")
        with mock.patch.object(generated.subprocess, "run", return_value=done):
            self.assertEqual(generated.run(ONE), "no counting sentence found")

    def test_run_falls_back_to_stdout_then_to_the_status(self):
        done = mock.Mock(returncode=2, stderr="", stdout="said on stdout")
        with mock.patch.object(generated.subprocess, "run", return_value=done):
            self.assertEqual(generated.run(ONE), "said on stdout")
        silent = mock.Mock(returncode=3, stderr="", stdout="")
        with mock.patch.object(generated.subprocess, "run", return_value=silent):
            self.assertEqual(generated.run(ONE), "exit 3")

    def test_run_says_nothing_where_the_generator_succeeded(self):
        done = mock.Mock(returncode=0, stderr="", stdout="")
        with mock.patch.object(generated.subprocess, "run", return_value=done):
            self.assertIsNone(generated.run(ONE))

    def test_moved_names_the_files_git_reports(self):
        done = mock.Mock(returncode=0, stdout="a.md\n\nb.md\n")
        with mock.patch.object(generated, "_git", return_value=done):
            self.assertEqual(generated.moved(["a.md", "b.md"]), ["a.md", "b.md"])

    def test_moved_says_nothing_rather_than_nothing_found_when_git_fails(self):
        done = mock.Mock(returncode=128, stdout="")
        with mock.patch.object(generated, "_git", return_value=done):
            self.assertIsNone(generated.moved(["a.md"]))

    def test_git_is_addressed_at_the_repository_root(self):
        with mock.patch.object(generated.subprocess, "run") as ran:
            generated._git("diff")
        self.assertEqual(ran.call_args[0][0][:3], ["git", "-C", str(generated.ROOT)])


class TheCommandLine(unittest.TestCase):
    def test_list_prints_the_table(self):
        with mock.patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(generated.main(["--list"]), 0)
        self.assertIn("scripts/gen_board.py", out.getvalue())

    def test_no_flag_checks(self):
        with mock.patch.object(generated, "check", return_value=0) as checked:
            self.assertEqual(generated.main([]), 0)
        checked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
