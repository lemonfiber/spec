#!/usr/bin/env python3
"""What the contrast generator must get right, including the arithmetic.

The ratios are checked against WCAG 2.1's own published examples rather than
against what this implementation happens to produce. A generator tested only
against itself would keep agreeing with a formula nobody had checked, which is
the failure the page it writes exists to prevent.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_gen_contrast.py
"""

from __future__ import annotations

import importlib
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

gen_contrast = importlib.import_module("gen_contrast")


PALETTE = {
    "color": {
        "ink": "#000000",
        "paper": "#FFFFFF",
        "canvas": "#767676",
        "mid": "#767676",
    }
}

PAGE = """# Brand accessibility

Prose above the table, which must survive.

| Token | Hex | On `paper` | On `canvas` | On `ink` |
|-------|-----|---|---|---|
| `stale` | #BADBAD | 1.00 · fails | 1.00 · fails | 1.00 · fails |

Prose below the table, which must survive too.
"""


class Arithmetic(unittest.TestCase):
    """The formula, against values WCAG states the answer for."""

    def test_black_on_white_is_the_maximum(self):
        self.assertAlmostEqual(gen_contrast.ratio("#000000", "#FFFFFF"), 21.0, places=2)

    def test_a_colour_against_itself_is_one(self):
        self.assertAlmostEqual(gen_contrast.ratio("#5B6B2A", "#5B6B2A"), 1.0, places=6)

    def test_the_order_of_the_pair_does_not_matter(self):
        self.assertAlmostEqual(
            gen_contrast.ratio("#17160F", "#FBF7EA"),
            gen_contrast.ratio("#FBF7EA", "#17160F"),
            places=9,
        )

    def test_the_web_safe_grey_wcag_names_as_the_aa_boundary(self):
        # #767676 on white is the canonical 4.54 — the lightest grey that
        # clears AA for body text.
        self.assertAlmostEqual(gen_contrast.ratio("#767676", "#FFFFFF"), 4.54, places=2)

    def test_a_hex_is_read_with_or_without_its_hash(self):
        self.assertAlmostEqual(
            gen_contrast.luminance("#FFFFFF"), gen_contrast.luminance("FFFFFF"), places=9
        )

    def test_the_low_channel_branch_is_linear(self):
        # Below 0.03928 sRGB is linear rather than gamma-encoded, and a colour
        # that dark is what exercises the other side of the branch.
        self.assertGreater(gen_contrast.luminance("#050505"), 0.0)
        self.assertLess(gen_contrast.luminance("#050505"), gen_contrast.luminance("#0A0A0A"))


class Verdicts(unittest.TestCase):
    """The words the table puts beside a number, at each boundary."""

    def test_seven_is_aaa_and_just_under_is_not(self):
        self.assertEqual(gen_contrast.verdict(7.0), "AAA")
        self.assertEqual(gen_contrast.verdict(6.99), "AA")

    def test_four_and_a_half_is_aa_and_just_under_is_large_only(self):
        self.assertEqual(gen_contrast.verdict(4.5), "AA")
        self.assertEqual(gen_contrast.verdict(4.49), "AA large")

    def test_three_is_large_and_just_under_is_a_failure(self):
        self.assertEqual(gen_contrast.verdict(3.0), "AA large")
        self.assertEqual(gen_contrast.verdict(2.99), "fails")


class Writing(unittest.TestCase):
    """The generator against a page and a palette of its own."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.tokens = self.tmp / "tokens.json"
        self.page = self.tmp / "accessibility.md"
        self.write(PALETTE)
        self.page.write_text(PAGE, encoding="utf-8")
        self.restore = (gen_contrast.TOKENS, gen_contrast.PAGE)
        gen_contrast.TOKENS = self.tokens
        gen_contrast.PAGE = self.page
        self.addCleanup(self.put_back)

    def put_back(self):
        gen_contrast.TOKENS, gen_contrast.PAGE = self.restore
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, palette):
        self.tokens.write_text(json.dumps(palette), encoding="utf-8")

    def test_the_table_is_replaced_and_the_prose_around_it_is_not(self):
        gen_contrast.main()
        written = self.page.read_text(encoding="utf-8")
        self.assertIn("Prose above the table, which must survive.", written)
        self.assertIn("Prose below the table, which must survive too.", written)
        self.assertNotIn("#BADBAD", written)

    def test_every_token_gets_a_row(self):
        gen_contrast.main()
        written = self.page.read_text(encoding="utf-8")
        for token in PALETTE["color"]:
            self.assertIn(f"| `{token}` |", written)

    def test_a_token_against_its_own_surface_is_a_dash(self):
        gen_contrast.main()
        row = self.row("ink")
        self.assertEqual(row[-1].strip(), "—")

    def test_the_numbers_are_the_measured_ones(self):
        gen_contrast.main()
        self.assertIn("21.00 · AAA", self.page.read_text(encoding="utf-8"))

    def test_running_twice_changes_nothing(self):
        gen_contrast.main()
        once = self.page.read_text(encoding="utf-8")
        gen_contrast.main()
        self.assertEqual(once, self.page.read_text(encoding="utf-8"))

    def test_a_page_with_no_table_is_refused_rather_than_appended_to(self):
        self.page.write_text("# Nothing to replace\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            gen_contrast.main()
        self.assertIn("no measured table found", str(raised.exception))

    def test_a_palette_with_no_colours_is_refused(self):
        self.write({"font": {"body": "Golos Text"}})
        with self.assertRaises(SystemExit) as raised:
            gen_contrast.main()
        self.assertIn("carries no colours", str(raised.exception))

    def test_a_palette_missing_a_surface_says_which(self):
        self.write({"color": {"ink": "#000000", "paper": "#FFFFFF"}})
        with self.assertRaises(SystemExit) as raised:
            gen_contrast.main()
        self.assertIn("canvas", str(raised.exception))

    def row(self, token):
        for line in self.page.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"| `{token}` |"):
                return line.split("|")[1:-1]
        raise AssertionError(f"no row for {token}")


class Live(unittest.TestCase):
    """The real page and the real tokens, which is what CI diffs."""

    def test_the_page_on_disk_is_what_the_tokens_produce(self):
        # The integrity job runs the generator and diffs. This says the same
        # thing here, so a palette change that nobody regenerated is a failing
        # test rather than only a failing job.
        rows = gen_contrast.table()
        page = gen_contrast.PAGE.read_text(encoding="utf-8")
        for row in rows:
            self.assertIn(row, page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
