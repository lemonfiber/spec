#!/usr/bin/env python3
"""Coverage tests for integrity.py — every citation resolves, no identifier is
minted twice, every internal link points at a file that exists (GOV-R8, GOV-R11).

It is the gate that decides whether the spec itself may merge, and the spec is
what every other repository cites. A citation that resolves to nothing is a
requirement two repos are each sure the other wrote.

`integrity.ROOT` is fixed at import from the script's own location, so each test
points it at a spec built in a temporary directory instead. Each refusal is
checked by the message a maintainer would read as well as by the exit code.

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_integrity.py
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
import integrity  # noqa: E402


def run_main():
    """Call integrity.main() against whatever ROOT points at; return (code, stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = integrity.main()
    return code, out.getvalue()


class Spec(unittest.TestCase):
    """A spec tree in a temporary directory, read in place of the real one."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.saved = integrity.ROOT
        integrity.ROOT = self.root

    def tearDown(self):
        integrity.ROOT = self.saved
        shutil.rmtree(self.root, ignore_errors=True)

    def doc(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def define(self, *ids):
        """Requirements as the spec defines them: a bolded id opening a table row."""
        return "".join(f"| **{i}** | what it asks for |\n" for i in ids)

    def adr(self, filename):
        self.doc(f"00-overview/decisions/{filename}", "# a decision\n")


class Clean(Spec):
    """Everything the check must let through."""

    def test_a_spec_whose_citations_all_resolve(self):
        self.doc("10-functional/f.md", self.define("A1-R1", "A1-R2"))
        self.doc("00-overview/vision.md", "We will do A1-R1 and then A1-R2.\n")
        code, out = run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("spec integrity: clean", out)

    def test_an_empty_spec_is_clean(self):
        self.assertEqual(run_main(), (0, "spec integrity: clean\n"))

    def test_a_link_to_a_file_that_exists(self):
        self.doc("00-overview/vision.md", "see [the features](../10-functional/f.md)\n")
        self.doc("10-functional/f.md", "# features\n")
        self.assertEqual(run_main()[0], 0)

    def test_a_link_carrying_an_anchor_is_read_without_it(self):
        self.doc("00-overview/vision.md", "see [a heading](../10-functional/f.md#goals)\n")
        self.doc("10-functional/f.md", "# features\n")
        self.assertEqual(run_main()[0], 0)

    def test_an_anchor_on_its_own_names_no_file(self):
        self.doc("00-overview/vision.md", "see [above](#goals)\n")
        self.assertEqual(run_main()[0], 0)

    def test_a_link_that_leaves_the_repository_is_not_ours_to_resolve(self):
        self.doc("00-overview/vision.md",
                 "[docs](https://docs.lemonfiber.app/) and [mail](mailto:a@b.c)\n")
        self.assertEqual(run_main()[0], 0)

    def test_a_link_with_nothing_in_it_is_passed_over(self):
        self.doc("00-overview/vision.md", "[empty]( )\n")
        self.assertEqual(run_main()[0], 0)

    def test_a_docs_path_belongs_to_the_repo_that_has_one(self):
        # `.docs/` is a repo-local convention in cli, not a path in this tree.
        self.doc("00-overview/vision.md",
                 "[a](.docs/plan.md) and [b](../cli/.docs/plan.md)\n")
        self.assertEqual(run_main()[0], 0)

    def test_an_adr_citation_that_resolves(self):
        self.adr("0007-one-thing.md")
        self.doc("00-overview/vision.md", "as ADR-0007 settled\n")
        self.assertEqual(run_main()[0], 0)

    def test_an_adr_is_the_same_decision_however_it_is_padded(self):
        # The filename may carry three digits or four; the citation may too.
        self.adr("007-one-thing.md")
        self.doc("00-overview/vision.md", "ADR-007 and ADR-0007 are one decision\n")
        self.assertEqual(run_main()[0], 0)

    def test_a_file_in_the_decisions_directory_that_is_not_an_adr(self):
        self.adr("0007-one-thing.md")
        self.doc("00-overview/decisions/README.md", "# the decisions\n")
        self.doc("00-overview/vision.md", "ADR-0007\n")
        self.assertEqual(run_main()[0], 0)

    def test_what_git_keeps_is_not_the_spec(self):
        # A checkout's own .git directory can hold Markdown; it defines nothing.
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc(".git/COMMIT_EDITMSG.md", self.define("A1-R1") + "cites B9-R9 too\n")
        code, out = run_main()
        self.assertEqual(code, 0, out)


class Refusals(Spec):
    """Every refusal, by its message as well as its code."""

    def test_a_citation_resolving_to_nothing(self):
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc("00-overview/vision.md", "we will do A1-R9\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("00-overview/vision.md: cites undefined A1-R9", out)
        self.assertIn("1 integrity problem(s).", out)

    def test_an_identifier_defined_twice(self):
        # Identifiers are permanent and unique (GOV-R8); a second definition
        # makes every citation of it ambiguous.
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc("20-architecture/a.md", self.define("A1-R1"))
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("duplicate requirement id defined 2x: A1-R1", out)

    def test_an_identifier_defined_three_times_is_counted(self):
        for name in ("a.md", "b.md", "c.md"):
            self.doc(f"10-functional/{name}", self.define("A1-R1"))
        self.assertIn("defined 3x: A1-R1", run_main()[1])

    def test_only_the_first_stray_citation_in_a_file_is_named(self):
        # The rest is noise: one broken file is one thing to go and fix.
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc("00-overview/vision.md", "A1-R7 then A1-R8 then A1-R9\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("cites undefined A1-R7", out)
        self.assertNotIn("A1-R8", out)
        self.assertNotIn("A1-R9", out)

    def test_a_stray_citation_is_named_in_each_file_that_makes_it(self):
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc("00-overview/vision.md", "A1-R9\n")
        self.doc("20-architecture/a.md", "A1-R9\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("00-overview/vision.md: cites undefined A1-R9", out)
        self.assertIn("20-architecture/a.md: cites undefined A1-R9", out)
        self.assertIn("2 integrity problem(s).", out)

    def test_an_adr_citation_resolving_to_nothing(self):
        self.adr("0007-one-thing.md")
        self.doc("00-overview/vision.md", "as ADR-0008 settled\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("cites undefined ADR-0008", out)

    def test_an_adr_citation_where_no_decision_has_been_recorded(self):
        self.doc("00-overview/vision.md", "as ADR-0001 settled\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("cites undefined ADR-0001", out)

    def test_only_the_first_stray_adr_in_a_file_is_named(self):
        self.doc("00-overview/vision.md", "ADR-0004 and ADR-0005\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("cites undefined ADR-0004", out)
        self.assertNotIn("ADR-0005", out)

    def test_a_link_to_a_file_that_is_not_there(self):
        self.doc("00-overview/vision.md", "see [the plan](./plan.md)\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("00-overview/vision.md: broken link -> ./plan.md", out)

    def test_the_same_broken_link_twice_in_a_file_is_said_once(self):
        self.doc("00-overview/vision.md", "[a](./plan.md) and again [b](./plan.md)\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertEqual(out.count("broken link -> ./plan.md"), 1)
        self.assertIn("1 integrity problem(s).", out)

    def test_a_broken_link_and_a_stray_citation_are_both_reported(self):
        self.doc("10-functional/f.md", self.define("A1-R1"))
        self.doc("00-overview/vision.md", "A1-R9, see [the plan](./plan.md)\n")
        code, out = run_main()
        self.assertEqual(code, 1)
        self.assertIn("cites undefined A1-R9", out)
        self.assertIn("broken link -> ./plan.md", out)
        self.assertIn("2 integrity problem(s).", out)


class Reading(Spec):
    """What counts as a definition, since everything else is measured against it."""

    def test_a_definition_is_a_bolded_id_opening_a_table_row(self):
        self.doc("10-functional/f.md", self.define("A1-R1", "B2-R30"))
        self.assertEqual(sorted(integrity.defined_reqs()), ["A1-R1", "B2-R30"])

    def test_prose_naming_an_id_does_not_define_it(self):
        self.doc("10-functional/f.md", "A1-R1 is **A1-R1** but not a row.\n")
        self.assertEqual(list(integrity.defined_reqs()), [])

    def test_a_decisions_directory_that_is_not_there_defines_no_adrs(self):
        self.assertEqual(integrity.defined_adrs(), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
