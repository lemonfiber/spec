#!/usr/bin/env python3
"""The shared markdown check refuses a tree that would hand markdownlint code.

markdownlint-cli2 imports a configuration written as a module, and every module
a configuration names under `customRules`, `markdownItPlugins` or
`outputFormatters`, from the tree it lints. In `gates` that tree is a pull
request's, on the one runner every later verdict runs on, so hygiene's markdown
job refuses such a tree in the step before the linter, and the linter never
starts on it.

The step's script is read out of the committed `hygiene.yml` and run over trees
built for each case.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_markdown_runs_no_code.py
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
HYGIENE = HERE.parent / ".github" / "workflows" / "hygiene.yml"


def steps() -> list[dict]:
    return yaml.safe_load(HYGIENE.read_text(encoding="utf-8"))["jobs"]["markdown"]["steps"]


class Guard(unittest.TestCase):
    def setUp(self):
        self.tree = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)

    def write(self, path: str, text: str = "{}\n") -> None:
        target = self.tree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def guard(self) -> subprocess.CompletedProcess:
        script = next(one for one in steps() if one.get("id") == "inert")["run"]
        return subprocess.run(["bash", "-c", script], cwd=self.tree, capture_output=True, text=True)

    def test_the_guard_comes_before_the_linter(self):
        names = [str(one.get("uses", "")).split("@")[0] or one.get("id") for one in steps()]
        self.assertLess(names.index("inert"), names.index("DavidAnson/markdownlint-cli2-action"))

    def test_a_tree_of_data_passes(self):
        self.write("README.md", "# Hello\n")
        self.write(".markdownlint.jsonc", '{ "MD013": false }\n')
        self.write("docs/.markdownlint-cli2.yaml", "config:\n  MD041: false\n")
        self.write(".git/.markdownlint.cjs", "ignored: it is the repository's own store")
        done = self.guard()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_configuration_written_as_a_module_is_refused(self):
        for name in (".markdownlint-cli2.cjs", ".markdownlint-cli2.mjs", ".markdownlint.cjs", ".markdownlint.mjs"):
            with self.subTest(name):
                self.setUp()
                self.write(f"deep/down/{name}", "module.exports = {};\n")
                done = self.guard()
                self.assertEqual(done.returncode, 1)
                self.assertIn(f"::error file=deep/down/{name}::", done.stdout)
                self.assertIn("would import and run", done.stdout)

    def test_a_module_by_any_other_name_is_still_one(self):
        # A directory, or a link, under the name is refused as well: the linter
        # goes by the name.
        (self.tree / ".markdownlint.cjs").mkdir()
        self.assertEqual(self.guard().returncode, 1)
        self.setUp()
        self.write("elsewhere.js", "module.exports = {};\n")
        (self.tree / ".markdownlint-cli2.mjs").symlink_to("elsewhere.js")
        self.assertEqual(self.guard().returncode, 1)

    def test_a_configuration_naming_a_module_is_refused(self):
        for key in ("customRules", "markdownItPlugins", "outputFormatters"):
            with self.subTest(key):
                self.setUp()
                self.write("sub/.markdownlint-cli2.jsonc", f'{{ "{key}": ["./rule.js"] }}\n')
                done = self.guard()
                self.assertEqual(done.returncode, 1)
                self.assertIn("names a module", done.stdout)

    def test_a_data_name_that_is_not_a_file_is_left_to_the_linter(self):
        (self.tree / ".markdownlint.jsonc").mkdir()
        self.assertEqual(self.guard().returncode, 0)

    def test_a_file_name_cannot_write_a_workflow_command(self):
        self.write("a\n::warning::x,y:z/.markdownlint.cjs", "module.exports = {};\n")
        done = self.guard()
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("\n::warning::", done.stdout)
        self.assertIn("file=a%0A%3A%3Awarning%3A%3Ax%2Cy%3Az/.markdownlint.cjs::", done.stdout)


if __name__ == "__main__":
    unittest.main()
