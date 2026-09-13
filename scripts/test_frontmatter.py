#!/usr/bin/env python3
"""Coverage tests for check_frontmatter.py — GOV-R12, Q-R66.

Every check is driven against a feature doc written to a temporary file, and
against the real schema — which is the point. The rules here are the schema's,
read out of it at import rather than written again, so a suite that supplied its
own enums would be testing a copy of the thing under test.

`main` is checked for the failure it had: `FEATURE_DOCS` is a relative glob, so a
run from the wrong directory matched nothing and printed *frontmatter: 0 feature
docs valid*, which is the sentence a tree of valid features gets.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_frontmatter.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import catalogue
import check_frontmatter as gate

# Built from the schema rather than written out, for the same reason the gate
# compiles its id pattern from it: a fixture carrying its own idea of a valid
# feature goes stale the moment the schema moves, and passes while it does.
GOOD = {key: min(gate.PROPS[key]["enum"]) for key in gate.ENUM_KEYS}


def doc(stem: str = "f1-thing", **overrides) -> str:
    """A feature doc written to a temporary file, and its path."""
    front = dict(GOOD)
    front["id"] = "F1"
    front["area"] = "F"
    front["title"] = "A feature"
    front.update(overrides)
    lines = []
    for key, value in front.items():
        if value is None:
            continue
        rendered = "[" + ", ".join(value) + "]" if isinstance(value, list) else value
        lines.append(f"{key}: {rendered}")
    where = pathlib.Path(tempfile.mkdtemp()) / f"{stem}.md"
    where.write_text("---\n" + "\n".join(lines) + "\n---\n\n# A feature\n", encoding="utf-8")
    return str(where)


class TheFixtureIsValid(unittest.TestCase):
    def test_a_doc_built_from_the_schema_has_nothing_wrong_with_it(self):
        # Asserted before anything below it. Every other test here says a broken
        # doc is refused, and every one of them would pass against a fixture that
        # was broken to begin with.
        self.assertEqual(gate.problems_for(doc()), [])


class TheKeys(unittest.TestCase):
    def test_a_missing_required_key(self):
        found = gate.problems_for(doc(title=None))
        self.assertTrue(any("missing required key 'title'" in said for said in found))

    def test_a_key_the_schema_does_not_define(self):
        path = doc()
        pathlib.Path(path).write_text(
            pathlib.Path(path).read_text().replace("---\n\n#", "invented: yes\n---\n\n#"),
            encoding="utf-8",
        )
        self.assertTrue(any("unknown key 'invented'" in said for said in gate.problems_for(path)))

    def test_a_file_with_no_frontmatter_at_all(self):
        where = pathlib.Path(tempfile.mkdtemp()) / "f1-thing.md"
        where.write_text("# Just a heading\n", encoding="utf-8")
        self.assertEqual(gate.problems_for(str(where)), [f"{where}: no frontmatter block"])


class TheEnums(unittest.TestCase):
    def test_a_value_outside_the_enum(self):
        for key in gate.ENUM_KEYS:
            with self.subTest(key=key):
                found = gate.problems_for(doc(**{key: "nonsense"}))
                self.assertTrue(any(f"{key} = 'nonsense'" in said for said in found))


class TheIdentity(unittest.TestCase):
    def test_an_id_the_schema_pattern_refuses(self):
        found = gate.problems_for(doc(id="not-an-id"))
        self.assertTrue(any("is malformed" in said for said in found))

    def test_an_id_whose_letter_is_not_its_area(self):
        found = gate.problems_for(doc(id="F1", area="C"))
        self.assertTrue(any("does not match area" in said for said in found))

    def test_an_id_the_filename_does_not_start_with(self):
        found = gate.problems_for(doc(stem="something-else"))
        self.assertTrue(any("does not match filename" in said for said in found))

    def test_the_filename_is_matched_whatever_its_case(self):
        self.assertEqual(gate.problems_for(doc(stem="F1-Thing")), [])


class TheLists(unittest.TestCase):
    def test_a_label_the_registry_does_not_carry(self):
        found = gate.problems_for(doc(labels=["invented"]))
        self.assertTrue(any("is not in the registry" in said for said in found))

    def test_a_label_it_does(self):
        self.assertEqual(gate.problems_for(doc(labels=[min(gate.LABELS)])), [])

    def test_a_malformed_entry_in_requires_or_relates(self):
        for key in ("requires", "relates"):
            with self.subTest(key=key):
                found = gate.problems_for(doc(**{key: ["not-an-id"]}))
                self.assertTrue(any(f"{key} entry" in said for said in found))

    def test_depends_is_retired_and_says_so(self):
        # The field that conflated "cannot be built without" with "worth reading",
        # which is how features came to be scheduled before the things they need.
        found = gate.problems_for(doc(depends=["F2"]))
        self.assertTrue(any("`depends` is retired" in said for said in found))


class TheShippedVersion(unittest.TestCase):
    def test_a_version_on_a_feature_nobody_has_built(self):
        found = gate.problems_for(doc(shipped="0.1.0", maturity="planned"))
        self.assertTrue(any("whose maturity is 'planned'" in said for said in found))

    def test_something_that_is_not_a_version(self):
        found = gate.problems_for(doc(shipped="soon", maturity="shipped"))
        self.assertTrue(any("is not a version" in said for said in found))

    def test_a_version_on_a_shipped_feature(self):
        self.assertEqual(gate.problems_for(doc(shipped="0.1.0", maturity="shipped")), [])

    def test_no_version_is_not_a_problem_whatever_the_maturity(self):
        # Deliberately not the other direction: `status` describes the
        # specification, and a feature can be accepted and unbuilt.
        self.assertEqual(gate.problems_for(doc(maturity="shipped")), [])


class WhatMainSays(unittest.TestCase):
    def setUp(self):
        self.was = catalogue.FEATURE_DOCS
        self.addCleanup(setattr, catalogue, "FEATURE_DOCS", self.was)

    def run_main(self) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = gate.main()
        return code, said.getvalue()

    def test_a_glob_that_matched_nothing_is_refused_rather_than_passed(self):
        catalogue.FEATURE_DOCS = str(pathlib.Path(tempfile.mkdtemp()) / "*.md")
        code, said = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("nothing was read", said)

    def test_a_tree_of_valid_docs_says_how_many_it_read(self):
        where = pathlib.Path(doc()).parent
        catalogue.FEATURE_DOCS = str(where / "*.md")
        code, said = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("1 feature docs valid", said)

    def test_a_tree_with_a_broken_doc_names_it(self):
        path = pathlib.Path(doc(id="not-an-id"))
        catalogue.FEATURE_DOCS = str(path.parent / "*.md")
        code, said = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("is malformed", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
