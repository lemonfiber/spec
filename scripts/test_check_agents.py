#!/usr/bin/env python3
"""An AGENTS.md opens with the pointer to the board and the shared rules, and
fits the cap — GOV-R26, GOV-R50.

Stdlib unittest.
Run:  python3 scripts/test_check_agents.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_agents  # noqa: E402

GOOD = """# AGENTS.md — example

> **Start at the roadmap and board on [lemonfiber.app](https://lemonfiber.app),
> rendered from the report. Then the rules** every repository shares:
> [working in the repositories](https://github.com/lemonfiber/spec/blob/main/50-governance/working-in-the-repositories.md).

## What this repo is

An example.
"""


def run_main(root):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["check_agents.py", "--root", str(root)]
    try:
        with contextlib.redirect_stdout(out):
            code = check_agents.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Faults(unittest.TestCase):
    def test_the_pointer_first_and_within_the_cap(self):
        self.assertEqual(check_agents.faults(GOOD), [])

    def test_a_file_that_is_not_there(self):
        self.assertIn("no AGENTS.md", check_agents.faults(None)[0])

    def test_a_pointer_that_is_missing_late_or_out_of_order(self):
        cases = {
            "no block": "# AGENTS.md\n\n## What this repo is\n",
            "after a paragraph": GOOD.replace("\n\n> **Start", "\n\nIntro.\n\n> **Start"),
            "the rules only": GOOD.replace("https://lemonfiber.app", "https://example.org"),
            "the board only": GOOD.replace("working-in-the-repositories", "contributing"),
            "the rules first": (
                "# AGENTS.md\n\n> [rules](50-governance/working-in-the-repositories.md)"
                " then [board](https://lemonfiber.app)\n"
            ),
        }
        for why, text in cases.items():
            with self.subTest(why):
                said = check_agents.faults(text)
                self.assertEqual(len(said), 1)
                self.assertIn("does not open with the pointer", said[0])

    def test_a_file_with_no_title_is_read_from_its_first_line(self):
        self.assertEqual(check_agents.faults(GOOD.split("\n", 2)[2]), [])

    def test_over_the_cap(self):
        said = check_agents.faults(GOOD + "line\n" * check_agents.CAP)
        self.assertEqual(len(said), 1)
        self.assertIn(f"the cap is {check_agents.CAP}", said[0])


class Main(unittest.TestCase):
    def test_what_it_says_and_its_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            code, out = run_main(root)
            self.assertEqual(code, 1)
            self.assertIn("::error file=AGENTS.md::there is no AGENTS.md", out)
            (root / "AGENTS.md").write_text(GOOD, encoding="utf-8")
            code, out = run_main(root)
            self.assertEqual(code, 0)
            self.assertIn("opens with the pointer", out)


if __name__ == "__main__":
    unittest.main()
