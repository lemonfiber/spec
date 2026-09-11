#!/usr/bin/env python3
"""Coverage tests for next_id.py — allocating an identifier that is actually free.

Grepping one file for its highest number is wrong here: a prefix spans several
files with interleaved ranges, and identifiers are permanent (`GOV-R8`) so a
withdrawn one leaves a hole that counting would hand back.

`next_id.ROOT` is fixed at import from the script's own location, so each test
points it at a tree built in a temporary directory.

Run:  python3 scripts/test_next_id.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import next_id  # noqa: E402


def run(*argv):
    """Call next_id.main() with argv; return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    previous = sys.argv
    sys.argv = ["next_id.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = next_id.main()
    finally:
        sys.argv = previous
    return code, out.getvalue(), err.getvalue()


class Allocating(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.previous, next_id.ROOT = next_id.ROOT, self.tmp
        self.addCleanup(setattr, next_id, "ROOT", self.previous)

    def define(self, name, *identifiers):
        rows = "".join(f"| **{i}** | a requirement |\n" for i in identifiers)
        (self.tmp / name).parent.mkdir(parents=True, exist_ok=True)
        (self.tmp / name).write_text(rows, encoding="utf-8")

    def test_a_prefix_spanning_files_is_read_whole(self):
        # The DES shape: one file's ceiling is not the family's.
        self.define("a.md", "DES-R1", "DES-R21")
        self.define("b.md", "DES-R15", "DES-R27")
        code, out, err = run("DES")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "DES-R28")
        self.assertIn("a.md", err)
        self.assertIn("b.md", err)

    def test_a_hole_is_never_handed_back(self):
        # Four defined, ceiling R9: counting would return R5, which once meant
        # something else. GOV has exactly this shape at R36..R39.
        self.define("a.md", "GOV-R1", "GOV-R2", "GOV-R3", "GOV-R9")
        code, out, _ = run("GOV")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "GOV-R10")

    def test_a_run_of_identifiers_is_contiguous(self):
        self.define("a.md", "N1-R4")
        code, out, _ = run("N1", "-n", "3")
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["N1-R5", "N1-R6", "N1-R7"])

    def test_a_prefix_is_accepted_however_it_is_typed(self):
        self.define("a.md", "DES-R3")
        for typed in ("des", "DES-R", "DeS"):
            code, out, _ = run(typed)
            self.assertEqual((code, out.strip()), (0, "DES-R4"), typed)

    def test_an_unknown_prefix_is_refused_with_its_neighbours(self):
        self.define("a.md", "DES-R1")
        code, _, err = run("DX")
        self.assertEqual(code, 2)
        self.assertIn("no requirement is defined under DX", err)
        self.assertIn("DES", err)

    def test_an_unknown_prefix_with_no_neighbours_still_refuses(self):
        self.define("a.md", "DES-R1")
        code, _, err = run("ZZ")
        self.assertEqual(code, 2)
        self.assertNotIn("Prefixes starting", err)

    def test_a_citation_does_not_reserve_a_number(self):
        # Only a definition occupies one; a typo in prose must not hold R99.
        (self.tmp / "a.md").write_text(
            "| **DES-R1** | a requirement |\nSee DES-R99 for more.\n", encoding="utf-8"
        )
        code, out, _ = run("DES")
        self.assertEqual((code, out.strip()), (0, "DES-R2"))

    def test_vendored_and_git_trees_are_not_read(self):
        self.define("a.md", "DES-R1")
        self.define("vendor/other/b.md", "DES-R80")
        code, out, _ = run("DES")
        self.assertEqual(out.strip(), "DES-R2", "a vendored copy is not ours to allocate from")
        self.assertEqual(code, 0)

    def test_the_prefix_listing_reports_ceilings_and_gaps(self):
        self.define("a.md", "GOV-R1", "GOV-R4")
        code, out, _ = run("--prefixes")
        self.assertEqual(code, 0)
        self.assertIn("highest R4", out)
        self.assertIn("gaps: R2, R3", out)

    def test_the_prefix_listing_says_nothing_of_gaps_where_there_are_none(self):
        self.define("a.md", "GOV-R1", "GOV-R2")
        _, out, _ = run("--prefixes")
        self.assertNotIn("gaps", out)

    def test_naming_no_prefix_at_all_is_refused(self):
        self.define("a.md", "DES-R1")
        with self.assertRaises(SystemExit):
            run()


class Branches(unittest.TestCase):
    """An identifier taken on an unmerged branch is taken.

    `F9` was allocated on a pull request that had not merged, and this script —
    reading only the working tree — still reported the `F` ceiling as `F8`. The
    next author to ask would have been handed a number already spoken for, which
    is the double allocation the script exists to prevent, one level up.
    """

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.tmp, capture_output=True, text=True, check=True,
        )

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.previous, next_id.ROOT = next_id.ROOT, self.tmp
        self.addCleanup(setattr, next_id, "ROOT", self.previous)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@e.st")
        self.git("config", "user.name", "T")

    def commit(self, name, *identifiers):
        rows = "".join(f"| **{i}** | a requirement |\n" for i in identifiers)
        (self.tmp / name).write_text(rows, encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-qm", f"add {name}")

    def on_a_branch(self, branch, name, *identifiers):
        """Commit on a branch and leave it only under refs/remotes, as a fetch would."""
        self.git("checkout", "-q", "-b", branch)
        self.commit(name, *identifiers)
        head = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("checkout", "-q", "main")
        self.git("branch", "-qD", branch)
        self.git("update-ref", f"refs/remotes/origin/{branch}", head)

    def test_a_number_taken_on_a_branch_is_not_handed_out_again(self):
        self.commit("main.md", "F-R1", "F-R2")
        self.on_a_branch("in-flight", "flight.md", "F-R3")
        code, out, err = run("F")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "F-R4")
        self.assertIn("branch(es) read", err)

    def test_the_branch_is_named_so_the_reader_knows_where_it_went(self):
        self.commit("main.md", "F-R1")
        self.on_a_branch("in-flight", "flight.md", "F-R7")
        _, _, err = run("F")
        self.assertIn("origin/in-flight", err)

    def test_here_reads_the_tree_only_and_says_what_that_costs(self):
        self.commit("main.md", "F-R1")
        self.on_a_branch("in-flight", "flight.md", "F-R3")
        _, out, err = run("F", "--here")
        self.assertEqual(out.strip(), "F-R2")
        self.assertIn("handed out again", err)

    def test_a_number_in_both_keeps_the_path_the_tree_has(self):
        # The branch is only ever news about a number the tree does not know.
        # The branch edits the same file so the row is on both sides of it.
        self.commit("main.md", "F-R1")
        self.git("checkout", "-q", "-b", "in-flight")
        (self.tmp / "main.md").write_text(
            "| **F-R1** | reworded on the branch |\n", encoding="utf-8")
        self.git("add", "main.md")
        self.git("commit", "-qm", "reword")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("checkout", "-q", "main")
        self.git("branch", "-qD", "in-flight")
        self.git("update-ref", "refs/remotes/origin/in-flight", head)
        _, _, err = run("F")
        self.assertIn("main.md", err)
        self.assertNotIn("(origin/in-flight)", err)

    def test_a_ref_this_clone_cannot_read_yields_nothing_rather_than_guessing(self):
        # A ref listed but unreadable — a shallow clone, or a fetch that failed
        # partway. Returning an empty set is right; inventing one is not.
        self.commit("main.md", "F-R1")
        self.git("update-ref", "refs/remotes/origin/broken", "0" * 40)
        self.assertEqual(next_id.defined_on("refs/remotes/origin/broken"), set())

    def test_a_tree_that_is_not_a_repository_says_it_searched_only_itself(self):
        # No git, no refs. It must say so rather than imply it looked.
        plain = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, plain, ignore_errors=True)
        next_id.ROOT = plain
        (plain / "a.md").write_text("| **F-R1** | x |\n", encoding="utf-8")
        _, out, err = run("F")
        self.assertEqual(out.strip(), "F-R2")
        self.assertIn("no branches could be read", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
