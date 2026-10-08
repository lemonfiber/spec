#!/usr/bin/env python3
"""The shared markdown check hands markdownlint nothing of the pull request's but Markdown.

markdownlint-cli2 reads a configuration from every directory it lints, in
formats that import code, and resolves the modules a configuration names from
the tree beside it. In `gates` that tree is a pull request's, on the one runner
every later verdict runs on. So hygiene's markdown job checks the pull request
out aside, and replaces the linter's workspace with the tracked Markdown files,
read out of git, and the canonical configuration. Nothing of the pull request's
is read as configuration, so no way of writing one (a module, a key spelt with
an escape, a YAML merge, a byte-order mark, an `extends`, a package's own key,
a name in another case) has anything to reach.

The step's script is read out of the committed `hygiene.yml` and run over a
repository built with every such shape in it; each case is judged by what the
linter's workspace holds afterwards.

Stdlib unittest plus PyYAML, and git.
Run:  python3 scripts/test_markdown_runs_no_code.py
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
HYGIENE = HERE.parent / ".github" / "workflows" / "hygiene.yml"
CANONICAL = HERE.parent / "shared" / "markdownlint.jsonc"
LINTER = "DavidAnson/markdownlint-cli2-action"

#: Every shape a pull request could write a configuration in, by path.
SHAPES = {
    ".markdownlint-cli2.cjs": "module.exports = { customRules: ['./rule.js'] };\n",
    ".markdownlint-cli2.mjs": "export default { customRules: ['./rule.js'] };\n",
    ".markdownlint.cjs": "module.exports = {};\n",
    "docs/deep/.markdownlint.mjs": "export default {};\n",
    "docs/.markdownlint-cli2.jsonc": '{ "custom\\u0052ules": ["./rule.js"] }\n',
    "docs/bom/.markdownlint-cli2.jsonc": '﻿{ /* c */ "markdownItPlugins": [["evil-rule"]] }\n',
    "docs/.markdownlint-cli2.yaml": "base: &b\n  customRules: [evil-rule]\n<<: *b\n",
    "docs/dup/.markdownlint-cli2.jsonc": '{ "outputFormatters": [], "outputFormatters": [["./rule.js"]] }\n',
    ".markdownlint.jsonc": '{ "extends": "./evil.markdownlint.cjs", "default": false }\n',
    "evil.markdownlint.cjs": "module.exports = {};\n",
    ".Markdownlint-CLI2.cjs": "module.exports = {};\n",
    "package.json": '{ "markdownlint-cli2": { "customRules": ["evil-rule"] } }\n',
    "node_modules/evil-rule/index.js": "require('fs').writeFileSync('/tmp/pwned', '');\n",
    "node_modules/evil-rule/README.md": "# A package's own page\n",
    "rule.js": "module.exports = {};\n",
}

#: The Markdown a pull request holds, which is all the linter is to see of it.
MARKDOWN = {
    "README.md": "# Hello\n",
    "docs/guide.md": "# Guide\n",
    "docs/deep/with space.md": "# Spaced\n",
    "node_modules/evil-rule/README.md": SHAPES["node_modules/evil-rule/README.md"],
}


def steps() -> list[dict]:
    return yaml.safe_load(HYGIENE.read_text(encoding="utf-8"))["jobs"]["markdown"]["steps"]


def git(cwd: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                    *args], cwd=cwd, check=True, capture_output=True)


class Stage(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.work = self.root / "work"
        self.pr = self.work / ".pr"
        self.pr.mkdir(parents=True)
        (self.root / "temp").mkdir()
        canonical = self.work / ".spec-canonical" / "shared"
        canonical.mkdir(parents=True)
        shutil.copy(CANONICAL, canonical / "markdownlint.jsonc")
        git(self.pr, "init", "-q")

    def commit(self, files: dict[str, str]) -> None:
        for path, text in files.items():
            target = self.pr / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        git(self.pr, "add", "-A")
        git(self.pr, "commit", "-q", "-m", "tree")

    def stage(self, repo: str = "lemonfiber/core") -> subprocess.CompletedProcess:
        script = next(one for one in steps() if one.get("id") == "markdown-only")["run"]
        env = {**os.environ, "REPO": repo, "RUNNER_TEMP": str(self.root / "temp"),
               "GITHUB_WORKSPACE": str(self.work)}
        return subprocess.run(["bash", "-c", script], cwd=self.work, env=env, capture_output=True, text=True)

    def held(self) -> dict[str, bytes]:
        return {str(path.relative_to(self.work)): path.read_bytes()
                for path in sorted(self.work.rglob("*")) if not path.is_dir() or path.is_symlink()}

    def test_the_linter_comes_after_the_tree_is_replaced(self):
        names = [str(one.get("uses", "")).split("@")[0] or one.get("id") for one in steps()]
        self.assertLess(names.index("markdown-only"), names.index(LINTER))
        lint = next(one for one in steps() if str(one.get("uses", "")).startswith(LINTER))
        self.assertNotIn("config", lint.get("with", {}), "the canonical file is the workspace's own")

    def test_every_shape_of_configuration_is_left_behind(self):
        self.commit({**SHAPES, **MARKDOWN})
        (self.pr / "link.md").symlink_to("rule.js")
        git(self.pr, "add", "link.md")
        git(self.pr, "commit", "-q", "-m", "a link")
        (self.pr / "untracked.md").write_text("# Not in git\n", encoding="utf-8")
        done = self.stage()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        held = self.held()
        expected = {".markdownlint.jsonc": CANONICAL.read_bytes(),
                    **{path: text.encode() for path, text in MARKDOWN.items()}}
        self.assertEqual(held, expected)
        self.assertIn("4 Markdown file(s)", done.stdout)
        self.assertFalse((self.root / "temp" / "markdown").exists(), "the stage is cleared")

    def test_what_git_holds_is_read_not_the_working_tree(self):
        self.commit({"README.md": "# Committed\n"})
        (self.pr / "README.md").write_text("# Changed after\n", encoding="utf-8")
        self.assertEqual(self.stage().returncode, 0)
        self.assertEqual(self.held()["README.md"], b"# Committed\n")

    def test_a_directory_named_as_a_configuration_is_refused(self):
        for name in (".markdownlint-cli2.cjs", ".MARKDOWNLINT.mjs", ".markdownlint.jsonc"):
            with self.subTest(name):
                self.setUp()
                self.commit({f"docs/{name}/README.md": "# x\n", "README.md": "# y\n"})
                done = self.stage()
                self.assertEqual(done.returncode, 1)
                self.assertIn(f"::error::docs/{name}/README.md sits in a directory named", done.stdout)
                self.assertNotIn("README.md", self.held(), "the linter was handed nothing")

    def test_spec_takes_its_own_canonical_copy(self):
        shutil.rmtree(self.work / ".spec-canonical")
        self.commit({"shared/markdownlint.jsonc": '{ "MD013": false }\n', "README.md": "# z\n"})
        self.assertEqual(self.stage(repo="lemonfiber/spec").returncode, 0)
        self.assertEqual(self.held()[".markdownlint.jsonc"], b'{ "MD013": false }\n')

    def test_a_name_cannot_write_a_workflow_command(self):
        self.commit({"a\n::warning::x/.markdownlint.cjs/b.md": "# b\n"})
        done = self.stage()
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("\n::warning::", done.stdout)
        self.assertIn("::error::a%0A::warning::x/.markdownlint.cjs/b.md", done.stdout)


if __name__ == "__main__":
    unittest.main()
