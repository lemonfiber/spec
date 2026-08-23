#!/usr/bin/env python3
"""Coverage tests for gen_redirects.py — the pages that stand where the book
stood. Stdlib unittest, no dependencies. Run: python3 scripts/test_redirects.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_redirects  # noqa: E402


def run_main(argv):
    """Call main() with argv patched; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv
    sys.argv = ["gen_redirects", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen_redirects.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class RouteOf(unittest.TestCase):
    def test_a_document_keeps_its_path_in_lower_case(self):
        self.assertEqual(
            gen_redirects.route_of(pathlib.PurePosixPath("00-overview/vision.md")),
            "00-overview/vision",
        )
        self.assertEqual(
            gen_redirects.route_of(
                pathlib.PurePosixPath("10-functional/features/BOARD.md")
            ),
            "10-functional/features/board",
        )

    def test_a_readme_is_the_directory_holding_it(self):
        self.assertEqual(
            gen_redirects.route_of(pathlib.PurePosixPath("30-repos/README.md")),
            "30-repos",
        )


class Pages(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)
        (self.root / "30-repos").mkdir()
        (self.root / "30-repos" / "README.md").write_text("# Repos\n")
        (self.root / "30-repos" / "brand.md").write_text("# Brand\n")
        self.addCleanup(self.dir.cleanup)

    def test_it_names_every_url_the_book_published(self):
        found = gen_redirects.pages(self.root)
        self.assertEqual(found["index.html"], "")
        self.assertEqual(found["print.html"], "")
        self.assertEqual(found["30-repos/index.html"], "30-repos")
        self.assertEqual(found["30-repos/brand.html"], "30-repos/brand")

    def test_a_section_the_repository_does_not_have_contributes_nothing(self):
        self.assertNotIn("60-brand/index.html", gen_redirects.pages(self.root))


class Within(unittest.TestCase):
    def test_a_name_inside_the_directory_resolves(self):
        with tempfile.TemporaryDirectory() as work:
            out = pathlib.Path(work)
            self.assertEqual(
                gen_redirects.within(out, "a/b.html"), (out / "a" / "b.html").resolve()
            )

    def test_a_name_that_leaves_the_directory_does_not(self):
        with tempfile.TemporaryDirectory() as work:
            self.assertIsNone(gen_redirects.within(pathlib.Path(work), "../out.html"))


class Main(unittest.TestCase):
    def test_it_stops_rather_than_writing_outside_the_output(self):
        saved = gen_redirects.pages
        gen_redirects.pages = lambda root: {"../escaped.html": ""}
        try:
            with tempfile.TemporaryDirectory() as work:
                code, _, complaint = run_main([str(pathlib.Path(work) / "redirect")])
        finally:
            gen_redirects.pages = saved
        self.assertEqual(code, 1)
        self.assertIn("outside", complaint)

    def test_it_writes_a_page_that_names_where_the_document_went(self):
        with tempfile.TemporaryDirectory() as work:
            root = pathlib.Path(work) / "spec"
            (root / "40-quality").mkdir(parents=True)
            (root / "40-quality" / "tooling.md").write_text("# Tooling\n")
            out = pathlib.Path(work) / "redirect"
            saved = os.getcwd()
            os.chdir(root)
            try:
                code, printed, _ = run_main([str(out)])
            finally:
                os.chdir(saved)
            self.assertEqual(code, 0)
            self.assertIn("redirect pages", printed)
            page = (out / "40-quality" / "tooling.html").read_text()
            self.assertIn(
                'rel="canonical" href="https://docs.lemonfiber.app/spec/40-quality/tooling/"',
                page,
            )
            self.assertIn("0; url=https://docs.lemonfiber.app/spec/40-quality/tooling/", page)
            self.assertIn(
                'href="https://docs.lemonfiber.app/spec/"', (out / "index.html").read_text()
            )

    def test_it_refuses_to_run_without_somewhere_to_write(self):
        code, _, complaint = run_main([])
        self.assertEqual(code, 2)
        self.assertIn("usage", complaint)


if __name__ == "__main__":
    unittest.main(verbosity=2)
