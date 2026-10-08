#!/usr/bin/env python3
"""The advice explain adds: the citation, the mirrored page, the tracker — and
the silence where none is owed (GOV-R33).

Stdlib unittest.
Run:  python3 scripts/test_assist.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assist  # noqa: E402

FIRST = "FIRST_TIME_CONTRIBUTOR"
MIRRORS = [
    {"route": "commands/every-command.md", "remote": "https://github.com/o/core",
     "branch": "main", "path": "reference/commands.md"},
    {"route": "architecture", "remote": "https://github.com/o/core",
     "branch": "main", "path": ".docs/architecture"},
]
MANIFEST = 'version = "0.1.0"\nstatus = "staged"\nrepos = ["core"]\ngoals = ["A1-R1", "A1-R2"]\n'
TRACKER = '[[requirement]]\nid = "A1-R1"\nstate = "partial"\n'


class Citation(unittest.TestCase):
    def test_a_proposal_cites_the_rfc_process(self):
        said = assist.citation(["10-functional/proposals/scans.md"], "body", FIRST)
        self.assertIn("`Spec: GOV-R40`", said)

    def test_prose_only_cites_routine_maintenance(self):
        said = assist.citation(["README.md", "docs/a.mdx"], "", "FIRST_TIMER")
        self.assertIn("`Spec: GOV-R12`", said)

    def test_nothing_where_none_is_owed(self):
        cases = {
            "a returning contributor": (["README.md"], "", "CONTRIBUTOR"),
            "already cited": (["README.md"], "fix\n\nSpec: GOV-R12\n", FIRST),
            "no paths": ([], "", FIRST),
            "code, which no rule names": (["src/a.rs", "README.md"], "", FIRST),
        }
        for why, (paths, text, association) in cases.items():
            with self.subTest(why):
                self.assertEqual(assist.citation(paths, text, association), "")


class Mirrors(unittest.TestCase):
    def test_a_file_route_and_a_page_under_a_directory_route(self):
        paths = ["src/content/docs/commands/every-command.md",
                 "src/content/docs/architecture/00-index.md", "src/pages/index.astro"]
        said = assist.mirrored(paths, MIRRORS, FIRST)
        self.assertIn("- `src/content/docs/commands/every-command.md` is rendered from "
                      "https://github.com/o/core/blob/main/reference/commands.md", said)
        self.assertIn("https://github.com/o/core/blob/main/.docs/architecture/00-index.md", said)
        self.assertNotIn("index.astro", said)

    def test_a_route_is_not_a_prefix_of_a_longer_name(self):
        self.assertIsNone(assist.upstream("src/content/docs/architecture-notes.md", MIRRORS))

    def test_nothing_where_none_is_owed(self):
        self.assertEqual(assist.mirrored(["src/content/docs/architecture"], MIRRORS, "MEMBER"), "")
        self.assertEqual(assist.mirrored(["src/a.ts"], MIRRORS, FIRST), "")


class Tree(unittest.TestCase):
    """A spec with one staged version satisfied in `core`, and core's checkout."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = pathlib.Path(tmp.name)
        self.spec = self.base / "spec"
        (self.spec / "70-operations" / "versions").mkdir(parents=True)
        (self.spec / "70-operations" / "versions" / "0.1.0.toml").write_text(MANIFEST, encoding="utf-8")
        self.core = self.base / "core"
        self.core.mkdir()
        (self.core / "status.toml").write_text(TRACKER, encoding="utf-8")

    def reminder(self, paths=("src/a.rs",), text="feat: a\n\nSpec: A1-R1, A1-R2, GOV-R12\n", repo="core"):
        return assist.reminder(list(paths), text, self.spec, self.core, repo)


class Reminder(Tree):
    def test_each_cited_goal_and_its_state(self):
        said = self.reminder()
        self.assertIn("| `A1-R1` | partial |\n| `A1-R2` | not recorded |", said)
        self.assertNotIn("GOV-R12", said)

    def test_a_repository_without_a_tracker_records_nothing(self):
        (self.core / "status.toml").unlink()
        self.assertIn("| `A1-R1` | not recorded |", self.reminder())

    def test_nothing_where_none_is_owed(self):
        cases = {
            "the tracker is touched": {"paths": ["status.toml", "src/a.rs"]},
            "a split tracker is touched": {"paths": ["status/A1.toml"]},
            "no goal is cited": {"text": "Spec: GOV-R12\n"},
            "a repository no version is satisfied in": {"repo": "web"},
        }
        for why, given in cases.items():
            with self.subTest(why):
                self.assertEqual(self.reminder(**given), "")


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    saved = sys.argv
    sys.argv = ["assist.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = assist.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class Main(Tree):
    def setUp(self):
        super().setUp()
        self.was = os.getcwd()
        os.chdir(self.base)
        self.addCleanup(os.chdir, self.was)
        pathlib.Path("paths.txt").write_text("README.md\n\n", encoding="utf-8")
        pathlib.Path("text.txt").write_text("docs: a typo\n", encoding="utf-8")
        pathlib.Path("mirrors.json").write_text(json.dumps({"mirrors": MIRRORS}), encoding="utf-8")

    def test_citation(self):
        code, out, _ = run_main(["citation", "--paths", "paths.txt", "--text", "text.txt",
                                 "--association", FIRST])
        self.assertEqual(code, 0)
        self.assertIn("GOV-R12", out)

    def test_mirrors_and_silence(self):
        code, out, _ = run_main(["mirrors", "--paths", "paths.txt", "--mirrors", "mirrors.json",
                                 "--association", FIRST])
        self.assertEqual((code, out), (0, ""))

    def test_status(self):
        pathlib.Path("text.txt").write_text("Spec: A1-R1\n", encoding="utf-8")
        code, out, _ = run_main(["status", "--paths", "paths.txt", "--text", "text.txt",
                                 "--spec", "spec", "--repo-root", "core", "--repo", "core"])
        self.assertEqual(code, 0)
        self.assertIn("| `A1-R1` | partial |", out)

    def test_an_input_that_cannot_be_read(self):
        pathlib.Path("mirrors.json").write_text("{}", encoding="utf-8")
        cases = {
            "missing": ["citation", "--paths", "nowhere.txt", "--text", "text.txt", "--association", FIRST],
            "not a mirror table": ["mirrors", "--paths", "paths.txt", "--mirrors", "mirrors.json",
                                   "--association", FIRST],
        }
        for why, argv in cases.items():
            with self.subTest(why):
                code, out, err = run_main(argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("::error::", err)


if __name__ == "__main__":
    unittest.main()
