#!/usr/bin/env python3
"""Coverage tests for metafm.py — Q-R61, Q-R66.

`metafm` is the frontmatter parser every feature document is read through:
`catalogue.py` builds the board from it and `check_frontmatter.py` validates
against it, so a shape it misreads is a shape two gates then agree about.

It was carried as an unmeasured debt on the grounds that it was "exercised at
100%" through `catalogue.py`. It was not — four of its branches had never run.
Three of them decide what a value *is*, and the fourth decides that a document
has no frontmatter at all, which is the answer a caller acts on by skipping the
file.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_metafm.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import metafm

ROOT = pathlib.Path(__file__).resolve().parent.parent


def block(*lines: str) -> str:
    """A document whose frontmatter is the given lines."""
    return "---\n" + "\n".join(lines) + "\n---\n\n# A heading\n"


class WhatCountsAsABlock(unittest.TestCase):
    def test_a_document_with_frontmatter(self):
        self.assertEqual(metafm.parse(block("id: F1")), {"id": "F1"})

    def test_a_document_with_none(self):
        self.assertIsNone(metafm.parse("# Just a heading\n"))

    def test_a_block_that_is_never_closed(self):
        # The one worth naming. An unterminated block is answered with `None`,
        # which is the same answer a document with no frontmatter gets — so a
        # caller acting on it skips the file rather than complaining, and a
        # missing `---` reads as a document that was never meant to have one.
        self.assertIsNone(metafm.parse("---\nid: F1\ntitle: A feature\n"))

    def test_an_opening_marker_that_is_not_the_first_line(self):
        # A leading blank line is enough. `catalogue` reads whatever a writer
        # saved, and an editor that adds one would otherwise drop the document
        # out of the board with nothing said.
        self.assertIsNone(metafm.parse("\n---\nid: F1\n---\n"))

    def test_an_empty_block(self):
        self.assertEqual(metafm.parse("---\n\n---\n"), {})


class WhatAScalarMeans(unittest.TestCase):
    def test_a_bare_value(self):
        self.assertEqual(metafm.parse(block("status: accepted"))["status"], "accepted")

    def test_a_single_quoted_value(self):
        # This is not hypothetical: one title in this repository is single-quoted
        # precisely because it contains double quotes.
        said = metafm.parse(block("""title: '"Where is my show?" trace'"""))
        self.assertEqual(said["title"], '"Where is my show?" trace')

    def test_a_doubled_single_quote_is_one(self):
        self.assertEqual(metafm.parse(block("title: 'it''s here'"))["title"], "it's here")

    def test_a_double_quoted_value(self):
        self.assertEqual(metafm.parse(block('title: "A feature"'))["title"], "A feature")

    def test_an_escaped_double_quote_inside_one(self):
        said = metafm.parse(block(r'title: "say \"yes\""'))
        self.assertEqual(said["title"], 'say "yes"')

    def test_an_escaped_backslash_inside_one(self):
        self.assertEqual(metafm.parse(block(r'title: "a\\b"'))["title"], r"a\b")

    def test_a_quote_on_one_end_only_is_not_a_quoted_value(self):
        # Left as written rather than half-unwrapped, so a typo reaches the
        # schema check as the wrong value rather than as a plausible one.
        self.assertEqual(metafm.parse(block("title: 'unclosed"))["title"], "'unclosed")

    def test_the_value_is_everything_after_the_first_colon(self):
        said = metafm.parse(block("title: RFC: the second colon"))
        self.assertEqual(said["title"], "RFC: the second colon")

    def test_surrounding_space_is_not_part_of_the_value(self):
        self.assertEqual(metafm.parse(block("  id :   F1  "))["id"], "F1")


class WhatAListMeans(unittest.TestCase):
    def test_a_flow_list(self):
        said = metafm.parse(block("labels: [stats, verification, wiring]"))
        self.assertEqual(said["labels"], ["stats", "verification", "wiring"])

    def test_an_empty_flow_list_is_a_list_and_not_a_string(self):
        # `[]` and `''` are both falsy, and a gate asking "are there labels?"
        # cannot tell them apart — but one of them is a list it can iterate.
        self.assertEqual(metafm.parse(block("labels: []"))["labels"], [])

    def test_a_list_of_one(self):
        self.assertEqual(metafm.parse(block("relates: [D6]"))["relates"], ["D6"])

    def test_quoted_entries_are_unwrapped_like_any_other_scalar(self):
        said = metafm.parse(block("""labels: ['a b', "c d"]"""))
        self.assertEqual(said["labels"], ["a b", "c d"])


class WhatIsSkipped(unittest.TestCase):
    def test_a_blank_line(self):
        self.assertEqual(metafm.parse(block("id: F1", "", "area: F")), {"id": "F1", "area": "F"})

    def test_a_comment(self):
        self.assertEqual(metafm.parse(block("# a note", "id: F1")), {"id": "F1"})

    def test_a_line_with_no_colon(self):
        self.assertEqual(metafm.parse(block("id: F1", "nonsense")), {"id": "F1"})


class WhatItReadsFromDisk(unittest.TestCase):
    def test_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "f1-thing.md"
            path.write_text(block("id: F1", "labels: [a, b]"), encoding="utf-8")
            self.assertEqual(metafm.load(path), {"id": "F1", "labels": ["a", "b"]})

    def test_a_real_feature_document_in_this_repository(self):
        # The parser against the thing it parses. Every case above is written
        # from the parser's own shapes, and a suite written that way agrees with
        # the code whatever the documents actually look like.
        path = ROOT / "10-functional" / "features" / "h-glue" / "h8-stats.md"
        front = metafm.load(path)
        self.assertEqual(front["id"], "H8")
        self.assertEqual(front["kind"], "feature")
        self.assertIsInstance(front["labels"], list)
        self.assertIn("stats", front["labels"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
