#!/usr/bin/env python3
"""Coverage tests for spec_refs.py — GOV-R32, Q-R66.

This one does not refuse anything, which is why it is easy to leave untested and
worth testing anyway. It writes the comment a contributor reads to find out
whether their citation landed, and every way it can be wrong is a way of telling
somebody something untrue about their own pull request: a link to the wrong file,
a warning about an identifier that exists, or silence where a citation was made.

The path guard gets its own tests. `--text-file` is a path this script is handed
by a workflow, and reading one outside the workspace would be reading a file
nobody asked it to read. It is refused with the marker still printed, so the
sticky comment updates rather than the step going quiet.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_spec_refs.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import spec_refs as refs

URL = "https://example.invalid/blob/main"


def spec(rows: str = "| **X1-R1** | The first thing. |\n", adrs: dict[str, str] | None = None) -> pathlib.Path:
    """A spec checkout defining these requirements and these decisions."""
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "10-functional").mkdir(parents=True)
    (root / "10-functional" / "x1.md").write_text(
        f"# X1 — a feature\n\n| ID | Requirement |\n|----|----|\n{rows}", encoding="utf-8"
    )
    if adrs:
        where = root / "00-overview" / "decisions"
        where.mkdir(parents=True)
        for name, heading in adrs.items():
            (where / name).write_text(f"{heading}\n", encoding="utf-8")
    return root


class WhatItReadsAsACitation(unittest.TestCase):
    def test_an_identifier_on_a_spec_trailer(self):
        self.assertEqual(refs.cited("Spec: X1-R1"), ["X1-R1"])

    def test_several_on_one_trailer_in_the_order_written(self):
        self.assertEqual(refs.cited("Spec: X1-R2, X1-R1"), ["X1-R2", "X1-R1"])

    def test_the_same_one_twice_is_listed_once(self):
        self.assertEqual(refs.cited("Spec: X1-R1\n\nSpec: X1-R1"), ["X1-R1"])

    def test_an_identifier_not_on_a_trailer_is_prose(self):
        # A sentence mentioning a requirement is not a claim to serve it, and
        # treating it as one would fill the comment with whatever the body says.
        self.assertEqual(refs.cited("This is about X1-R1 and nothing else."), [])

    def test_a_body_citing_nothing(self):
        self.assertEqual(refs.cited("No trailers here.\n"), [])


class WhatItFinds(unittest.TestCase):
    def test_a_requirement_against_the_file_defining_it(self):
        found = refs.index(spec())
        self.assertEqual(found["X1-R1"], ("10-functional/x1.md", "The first thing."))

    def test_the_first_definition_wins_so_a_later_copy_cannot_move_the_link(self):
        root = spec()
        (root / "10-functional" / "x2.md").write_text(
            "| **X1-R1** | Said again elsewhere. |\n", encoding="utf-8"
        )
        self.assertEqual(refs.index(root)["X1-R1"][0], "10-functional/x1.md")

    def test_a_decision_record_by_its_padded_number(self):
        found = refs.index(spec(adrs={"0018-pinning.md": "# Pin the certificate"}))
        self.assertIn("ADR-0018", found)
        self.assertEqual(found["ADR-0018"][1], "Pin the certificate")

    def test_a_three_digit_number_is_padded_to_four(self):
        found = refs.index(spec(adrs={"007-early.md": "# An early one"}))
        self.assertIn("ADR-0007", found)

    def test_a_file_that_merely_starts_with_a_number_is_not_a_decision(self):
        # The name is the identifier here, so a loose match would mint an ADR out
        # of any numbered file somebody dropped in that directory.
        found = refs.index(spec(adrs={"7-early.md": "# Too short", "notes.md": "# Not one"}))
        self.assertEqual([key for key in found if key.startswith("ADR-")], [])

    def test_a_tree_with_no_decisions_is_not_an_error(self):
        self.assertNotIn("ADR-0001", refs.index(spec()))

    def test_a_decision_with_no_heading_is_listed_with_nothing_said_about_it(self):
        # Listed rather than skipped: the citation is valid and the link works, and
        # a decision nobody gave a title is a thing to see in the comment.
        found = refs.index(spec(adrs={"0042-untitled.md": "No heading here.\n"}))
        self.assertEqual(found["ADR-0042"][1], "")

    def test_markdown_inside_a_git_directory_is_not_the_spec(self):
        # A checkout carries `.md` under `.git`, and a requirement row in one of
        # them would be indexed as though the spec defined it.
        root = spec()
        hidden = root / ".git" / "notes"
        hidden.mkdir(parents=True)
        (hidden / "stray.md").write_text("| **X9-R9** | From inside .git. |\n", encoding="utf-8")
        self.assertNotIn("X9-R9", refs.index(root))


class WhatItWrites(unittest.TestCase):
    def test_the_marker_comes_first_so_the_comment_can_be_found_again(self):
        self.assertTrue(refs.build([], {}, URL).startswith(refs.MARKER))

    def test_a_citation_becomes_a_link_to_its_file(self):
        said = refs.build(["X1-R1"], refs.index(spec()), URL)
        self.assertIn(f"[`X1-R1`]({URL}/10-functional/x1.md) — The first thing.", said)

    def test_an_identifier_nothing_defines_is_flagged_rather_than_linked(self):
        said = refs.build(["X9-R9"], {}, URL)
        self.assertIn("not found on spec@main", said)
        self.assertNotIn(URL, said)

    def test_citing_nothing_says_how_to_cite_something(self):
        said = refs.build([], {}, URL)
        self.assertIn("No `Spec:` citation found yet", said)

    def test_a_long_requirement_is_cut_with_an_ellipsis(self):
        long = "x" * 200
        said = refs.build(["X1-R1"], {"X1-R1": ("a.md", long)}, URL)
        self.assertIn("…", said)
        self.assertNotIn("x" * 141, said)

    def test_a_requirement_just_under_the_cut_is_left_whole(self):
        edge = "y" * 140
        said = refs.build(["X1-R1"], {"X1-R1": ("a.md", edge)}, URL)
        self.assertIn(edge, said)
        self.assertNotIn("…", said)

    def test_a_definition_with_no_text_still_makes_a_row(self):
        said = refs.build(["X1-R1"], {"X1-R1": ("a.md", "")}, URL)
        self.assertIn("— —", said)


class WhatItRefusesToRead(unittest.TestCase):
    def setUp(self):
        self.was = pathlib.Path.cwd()
        self.addCleanup(os.chdir, self.was)

    def run_main(self, spec_dir: pathlib.Path, text_file: pathlib.Path) -> str:
        said = io.StringIO()
        argv = sys.argv
        sys.argv = [
            "spec_refs.py",
            "--spec-dir", str(spec_dir),
            "--text-file", str(text_file),
            "--spec-url", URL + "/",
        ]
        try:
            with contextlib.redirect_stdout(said):
                refs.main()
        finally:
            sys.argv = argv
        return said.getvalue()

    def test_a_text_file_inside_the_workspace_is_read(self):
        root = spec()
        work = pathlib.Path(tempfile.mkdtemp())
        body = work / "body.txt"
        body.write_text("Spec: X1-R1\n", encoding="utf-8")
        os.chdir(work)
        said = self.run_main(root, body)
        self.assertIn("X1-R1", said)
        self.assertIn("10-functional/x1.md", said)

    def test_a_text_file_outside_it_is_refused_with_the_marker_still_printed(self):
        root = spec()
        outside = pathlib.Path(tempfile.mkdtemp()) / "body.txt"
        outside.write_text("Spec: X1-R1\n", encoding="utf-8")
        os.chdir(tempfile.mkdtemp())
        said = self.run_main(root, outside)
        self.assertIn(refs.MARKER, said)
        self.assertIn("outside the workspace", said)
        self.assertNotIn("X1-R1", said)

    def test_the_trailing_slash_on_the_url_is_not_doubled(self):
        root = spec()
        work = pathlib.Path(tempfile.mkdtemp())
        body = work / "body.txt"
        body.write_text("Spec: X1-R1\n", encoding="utf-8")
        os.chdir(work)
        said = self.run_main(root, body)
        self.assertNotIn("//10-functional", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
