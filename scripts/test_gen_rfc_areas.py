#!/usr/bin/env python3
"""The RFC form's area options are the catalogue's areas, and nothing else.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_gen_rfc_areas.py
"""

from __future__ import annotations

import contextlib
import importlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

catalogue = importlib.import_module("catalogue")
gen = importlib.import_module("gen_rfc_areas")

PAGE = (
    "# Features\n\n## How to read a feature doc\n\n"
    "## B — Running it\n\n## The ecosystem\n\n## A — Getting started\n\n"
    "## J — Runtime & platform · *Draft*\n"
)
FORM = (
    "name: RFC\nbody:\n"
    "  - type: dropdown\n    id: area\n    attributes:\n      label: Area\n      options:\n"
    '        - "A — Old"\n        - "Z — Gone"\n'
    "    validations:\n      required: true\n"
    "  - type: input\n    id: proposal-title\n"
)


class Areas(unittest.TestCase):
    def test_a_section_headed_by_a_letter_is_an_area(self):
        self.assertEqual(
            catalogue.areas(PAGE),
            {"B": "Running it", "A": "Getting started", "J": "Runtime & platform"},
        )


class Written(unittest.TestCase):
    def test_the_options_are_every_area_in_letter_order(self):
        after = gen.written(FORM, catalogue.areas(PAGE))
        self.assertIn(
            '      options:\n        - "A — Getting started"\n        - "B — Running it"\n'
            '        - "J — Runtime & platform"\n    validations:\n',
            after,
        )
        self.assertTrue(after.startswith("name: RFC\nbody:\n"))
        self.assertTrue(after.endswith("  - type: input\n    id: proposal-title\n"))

    def test_writing_twice_changes_nothing(self):
        once = gen.written(FORM, catalogue.areas(PAGE))
        self.assertEqual(gen.written(once, catalogue.areas(PAGE)), once)

    def test_a_form_without_the_dropdown_is_refused(self):
        form, names = FORM.replace("id: area", "id: place"), catalogue.areas(PAGE)
        with self.assertRaisesRegex(gen.Refused, "no `area` dropdown"):
            gen.written(form, names)

    def test_a_page_with_no_area_is_refused(self):
        with self.assertRaisesRegex(gen.Refused, "heads no area"):
            gen.written(FORM, {})


class Main(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        page = self.root / catalogue.FEATURES_README
        page.parent.mkdir(parents=True)
        page.write_text(PAGE, encoding="utf-8")
        self.form = self.root / "rfc.yml"
        self.form.write_text(FORM, encoding="utf-8")
        for name, value in (("ROOT", self.root), ("FORM", self.form)):
            patch = mock.patch.object(gen, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_it_rewrites_the_form(self):
        self.assertEqual(gen.main(), 0)
        self.assertIn('"J — Runtime & platform"', self.form.read_text(encoding="utf-8"))

    def test_a_refusal_is_said_and_leaves_the_form(self):
        self.form.write_text("name: RFC\n", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(gen.main(), 1)
        self.assertIn("gen_rfc_areas: rfc.yml has no `area` dropdown", err.getvalue())
        self.assertEqual(self.form.read_text(encoding="utf-8"), "name: RFC\n")


class TheCommittedForm(unittest.TestCase):
    def test_it_lists_the_catalogues_areas(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        names = catalogue.areas((root / catalogue.FEATURES_README).read_text(encoding="utf-8"))
        form = (root / ".github" / "ISSUE_TEMPLATE" / "rfc.yml").read_text(encoding="utf-8")
        self.assertEqual(gen.written(form, names), form)


if __name__ == "__main__":
    unittest.main()
