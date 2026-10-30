#!/usr/bin/env python3
"""`paths.py`: a path from a command line stays inside the working directory, and a job
holding a guarded reads and writes files there without ever following a link.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_paths.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import paths

GUARDED_BODY = "only the runner may read this"


class Scratch(unittest.TestCase):
    """A working directory of its own, and a secret-looking file outside it nobody may read."""

    def setUp(self):
        self.outside = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.outside, True)
        self.addCleanup(shutil.rmtree, self.root, True)
        self.guarded = self.outside / "guarded-file"
        self.guarded.write_text(GUARDED_BODY)
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)

    def file(self, relative: str, body: str = "x") -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path


class Within(Scratch):
    """Where a command-line path may point."""

    def test_a_path_inside_is_resolved_and_one_outside_is_refused(self):
        self.assertEqual(paths.within_cwd("a/../b"), self.root / "b")
        outside = str(self.guarded)
        with contextlib.redirect_stdout(io.StringIO()) as said, self.assertRaises(SystemExit):
            paths.within_cwd(outside)
        self.assertIn("escapes the working directory", said.getvalue())

    def test_a_plain_relative_path_is_the_path_it_names(self):
        self.file("dir/plugin.toml")
        self.assertEqual(paths.plain_relative("./dir/plugin.toml"), "dir/plugin.toml")
        self.assertEqual(paths.plain_relative(str(self.root / "dir/plugin.toml")), "dir/plugin.toml")
        self.assertEqual(paths.plain_relative("."), ".")

    def test_a_link_on_the_way_or_at_the_end_is_refused(self):
        self.file("real/plugin.toml")
        os.symlink(self.root / "real", self.root / "linked")
        os.symlink(self.root / "real/plugin.toml", self.root / "plugin.toml")
        with self.assertRaisesRegex(paths.NotPlain, "passes through a link"):
            paths.plain_relative("linked/plugin.toml")
        with self.assertRaisesRegex(paths.NotPlain, "is a link"):
            paths.plain_relative("plugin.toml")

    def test_a_directory_is_real_all_the_way_down_and_made_where_asked(self):
        self.assertEqual(paths.plain_directory("."), self.root)
        self.assertEqual(paths.plain_directory("new/deeper", make=True), self.root / "new/deeper")
        with self.assertRaises(FileNotFoundError):
            paths.plain_directory("missing")
        self.file("afile")
        with self.assertRaisesRegex(paths.NotPlain, "not a plain directory"):
            paths.plain_directory("afile")


class Plain(Scratch):
    """Reading, writing and listing, none of it through a link."""

    def test_a_plain_file_is_read_within_its_bound(self):
        self.file("a/b.json", "{}")
        self.assertEqual(paths.plain_read(self.root, "a/b.json", 10), b"{}")
        with self.assertRaisesRegex(paths.NotPlain, "larger than 1 bytes"):
            paths.plain_read(self.root, "a/b.json", 1)

    def test_a_link_to_a_secret_is_refused_and_nothing_is_read(self):
        os.symlink(self.guarded, self.root / "plugin.toml")
        (self.root / "recordings").mkdir()
        os.symlink(self.outside, self.root / "recordings/sonarr")
        self.guarded.chmod(0)
        self.addCleanup(self.guarded.chmod, 0o600)
        with self.assertRaisesRegex(paths.NotPlain, "plugin.toml is a link"):
            paths.plain_read(self.root, "plugin.toml", 100)
        with self.assertRaisesRegex(paths.NotPlain, "recordings/sonarr is not a plain directory"):
            paths.plain_read(self.root, "recordings/sonarr/guarded-file", 100)

    def test_a_hard_link_a_directory_or_a_name_that_leaves_is_refused(self):
        self.file("one")
        os.link(self.root / "one", self.root / "two")
        (self.root / "dir").mkdir()
        for relative, why in (
            ("two", "not a plain file"),
            ("dir", "not a plain file"),
            ("../credentials", "not a plain relative path"),
            (".", "working directory itself"),
            ("a//b", "not a plain relative path"),
        ):
            with self.subTest(relative=relative), self.assertRaisesRegex(paths.NotPlain, why):
                paths.plain_read(self.root, relative, 100)

    def test_a_file_that_cannot_be_opened_says_so(self):
        with self.assertRaises(FileNotFoundError):
            paths.plain_read(self.root, "missing", 100)

    def test_a_write_replaces_a_plain_file_makes_its_directories_and_refuses_a_link(self):
        self.file("a/b", "old")
        paths.plain_write(self.root, "a/b", b"new")
        paths.plain_write(self.root, "c/d/e", b"made")
        self.assertEqual(
            ((self.root / "a/b").read_text(), (self.root / "c/d/e").read_text()), ("new", "made")
        )
        os.symlink(self.guarded, self.root / "f")
        with self.assertRaisesRegex(paths.NotPlain, "not a plain file to replace"):
            paths.plain_write(self.root, "f", b"overwritten")
        self.assertEqual(self.guarded.read_text(), GUARDED_BODY)

    def test_a_listing_names_plain_files_apart_from_everything_else(self):
        self.file("a/b")
        self.file("c")
        os.link(self.root / "c", self.root / "hard")
        os.symlink(self.guarded, self.root / "link")
        os.symlink(self.outside, self.root / "dirlink")
        self.assertEqual(paths.plain_files(self.root), (["a/b"], ["c", "dirlink", "hard", "link"]))


if __name__ == "__main__":
    unittest.main()
