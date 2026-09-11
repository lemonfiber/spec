#!/usr/bin/env python3
"""What the repository table, diagram and count are generated from.

The table and the sentence counting it drifted once already: `lemonfiber-companion`
had a page under `30-repos/` and a row in nothing, while the sentence went on
saying "Those eleven" through the day a twelfth repository was created. These
pin the properties that stop it happening again — above all that generating
twice changes nothing, because a generator that is not idempotent makes the
`git diff --exit-code` in CI fail on a tree nobody edited.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_gen_repos.py
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

REGISTRY = """
[[repo]]
name = "spec"
spec = ["../README.md"]
lang = "Markdown"
note = "This repository"
node = "spec"
group = "root"
label = "spec<br/>canonical"

[[repo]]
name = "sdk-php"
spec = ["sdk-php.md"]
lang = "PHP"
note = "The same contract, as a peer"
node = "sdkphp"
group = "impl"
label = "sdk-php<br/>the PHP client"

[[repo]]
name = ".github"
spec = []
lang = "Markdown"
note = "Org-wide community health files; no spec of its own"
node = "gh"
group = "root"
label = ".github<br/>community health files"

[[edge]]
from = "sdk-php"
to = "spec"
label = "cites"

[[edge]]
from = "spec"
to = "impl"
label = "governs all"
dotted = true
"""

README = """# Repos

```mermaid
flowchart TD
    OLD["this gets replaced"]
```

Prose above the table that must survive.

| Repo | Spec | Language | What's specific about it |
|------|------|----------|--------------------------|
| `stale` | [gone.md](gone.md) | COBOL | A row from before |

Those nine are every repository in the org. And prose after it.
"""


class Tree:
    """A throwaway spec tree the generator is pointed at.

    Deliberately not a `TestCase`. Subclassing one here would make this a test
    class in its own right — collected and run, holding no tests, and reporting
    a pass that measured nothing — and `run_gen` would read as a test that
    forgot its prefix rather than as the helper it is.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        (self.tmp / "30-repos").mkdir()
        self.registry = self.tmp / "30-repos" / "repos.toml"
        self.readme = self.tmp / "30-repos" / "README.md"
        self.registry.write_text(REGISTRY, encoding="utf-8")
        self.readme.write_text(README, encoding="utf-8")
        here = pathlib.Path.cwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.tmp)
        self.gen = importlib.reload(importlib.import_module("gen_repos"))

    def run_gen(self):
        self.gen.main()
        return self.readme.read_text(encoding="utf-8")


class Generating(Tree, unittest.TestCase):
    def test_generating_twice_changes_nothing(self):
        # The property CI rests on: `gen && git diff --exit-code` must not fail
        # on a tree nobody touched.
        once = self.run_gen()
        twice = self.run_gen()
        self.assertEqual(once, twice)

    def test_the_count_is_a_word_and_matches_the_registry(self):
        self.assertIn("Those three are every repository in the org", self.run_gen())

    def test_a_row_the_registry_does_not_name_is_gone(self):
        out = self.run_gen()
        self.assertNotIn("stale", out)
        self.assertNotIn("COBOL", out)

    def test_every_registry_entry_gets_exactly_one_row(self):
        out = self.run_gen()
        self.assertEqual(out.count("| `spec` |"), 1)
        self.assertEqual(out.count("| `sdk-php` |"), 1)

    def test_prose_around_the_generated_parts_survives(self):
        out = self.run_gen()
        self.assertIn("Prose above the table that must survive.", out)
        self.assertIn("And prose after it.", out)

    def test_a_repo_with_no_page_of_its_own_points_at_this_one(self):
        # `.github` is described by the table and nowhere else. A blank cell
        # would read as an omission rather than as the fact it is.
        self.assertIn("| `.github` | this page | Markdown |", self.run_gen())

    def test_the_spec_link_keeps_the_path_as_written(self):
        # `../README.md` says it leaves this directory; `README.md` would not.
        self.assertIn("[../README.md](../README.md)", self.run_gen())


class Diagramming(Tree, unittest.TestCase):
    def test_the_old_diagram_is_replaced_not_appended(self):
        out = self.run_gen()
        self.assertNotIn("this gets replaced", out)
        self.assertEqual(out.count("```mermaid"), 1)

    def test_every_label_is_quoted(self):
        # Mermaid needs it wherever a label holds a dot, and quoting only those
        # is a rule someone has to remember.
        out = self.run_gen()
        self.assertIn('spec["spec<br/>canonical"]', out)
        self.assertIn('sdkphp["sdk-php<br/>the PHP client"]', out)

    def test_an_edge_naming_the_subgraph_resolves_to_it(self):
        # `impl` is the one edge target with no registry entry, deliberately:
        # governance applies to all of them at once.
        self.assertIn("spec -.->|governs all| impl", self.run_gen())

    def test_a_dotted_edge_is_dotted_and_a_plain_one_is_not(self):
        out = self.run_gen()
        self.assertIn("sdkphp -->|cites| spec", out)
        self.assertIn("-.->|governs all|", out)


class Refusing(Tree, unittest.TestCase):
    def test_a_count_past_the_words_refuses_rather_than_writing_a_digit(self):
        with self.assertRaises(SystemExit) as raised:
            self.gen.word(21)
        self.assertIn("counting words", str(raised.exception))

    def test_a_readme_with_no_table_refuses(self):
        self.readme.write_text("```mermaid\nflowchart TD\n```\nThose three are every repository in the org\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.gen.main()
        self.assertIn("no repository table", str(raised.exception))

    def test_a_readme_with_no_diagram_refuses(self):
        self.readme.write_text(README.replace("```mermaid\nflowchart TD\n    OLD[\"this gets replaced\"]\n```", ""), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.gen.main()
        self.assertIn("no repository diagram", str(raised.exception))

    def test_a_readme_with_no_counting_sentence_refuses(self):
        self.readme.write_text(README.replace("Those nine are every repository in the org.", ""), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.gen.main()
        self.assertIn("no counting sentence", str(raised.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
