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


if __name__ == "__main__":
    unittest.main(verbosity=2)
