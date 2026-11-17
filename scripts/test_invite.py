#!/usr/bin/env python3
"""The invite-code check, against real git trees (OPS-R56).

Each case builds a repository in a temporary directory, commits what it needs and
runs the check over it, so what is searched is what git tracks.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_invite.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import check_invite as invite

#: An invite link, assembled so this file does not carry one.
CODE = "discord" + ".gg/abc123"
LONG = "discordapp" + ".com/invite/abc123"


def git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
    )


class ATree(unittest.TestCase):
    """A repository, and what the check says about it."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q")

    def track(self, path: str, text: str) -> None:
        (self.root / path).write_text(text, encoding="utf-8")
        git(self.root, "add", path)

    def run_check(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = invite.main(["--root", str(self.root)])
        return code, out.getvalue()

    def test_a_tree_addressing_the_community_by_name_passes(self):
        self.track("README.md", f"Join us at {invite.COMMUNITY}.\n")
        self.assertEqual(self.run_check(), (0, "no invite codes in tracked files\n"))

    def test_each_form_of_invite_link_is_refused_naming_where_it_is(self):
        for link in (CODE, LONG, "discord" + ".com/invite/abc123"):
            with self.subTest(link):
                self.track("README.md", f"Join us at https://{link}\n")
                code, said = self.run_check()
                self.assertEqual(code, 1)
                self.assertIn(f"README.md:1:Join us at https://{link}", said)
                self.assertIn(f"::error::Address the community as {invite.COMMUNITY} (OPS-R56).", said)

    def test_an_untracked_file_is_not_searched(self):
        self.track("README.md", "nothing here\n")
        (self.root / "notes.md").write_text(f"https://{CODE}\n", encoding="utf-8")
        self.assertEqual(self.run_check()[0], 0)

    def test_a_tree_git_cannot_search_is_refused_rather_than_passed(self):
        shutil.rmtree(self.root / ".git")
        code, said = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("::error::git grep could not search the tracked files", said)

    def test_this_check_does_not_match_its_own_text(self):
        spec = pathlib.Path(__file__).resolve().parent.parent
        self.assertEqual(invite.found(spec), [])


if __name__ == "__main__":
    unittest.main()
