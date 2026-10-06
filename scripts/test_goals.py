#!/usr/bin/env python3
"""The report of where every goal stands says what the sources say — OPS-R76, OPS-R77.

Each verdict is driven from the state that earns it: a goal cited and recorded
done is met, cited and recorded nowhere is unmarked, recorded and cited nowhere
is uncited, cited by an open pull request is claimed — a draft one included —
and touched by nothing is open. Then the reading that makes the report safe to
run against sibling checkouts: it reads a revision, never a working tree, so a
tracker edited and not committed changes nothing. And the refusals: a shallow
clone, a repository a version is satisfied in with no checkout given, a manifest
asked for that is not there.

Stdlib unittest. Real git repositories in a temporary directory, because what is
read — a commit message, a file at a revision — is what a patched reader would
stop testing.
Run:  python3 scripts/test_goals.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import goals  # noqa: E402

LEGACY_HEADER = "| Deliverable | Spec | Status | Landing |\n|---|---|---|---|\n"


def run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["goals.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = goals.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Train(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path("70-operations/versions").mkdir(parents=True)
        self.manifest("0.2.0", "planned", ["A1-R1", "A1-R2", "A1-R3", "A1-R4", "A1-R5"],
                      ["core", "app"])
        self.manifest("0.1.0", "released", ["A1-R9"], ["core"])
        (pathlib.Path("70-operations/versions") / "TEMPLATE.toml").write_text(
            'version = "X"\ngoals = []\n', encoding="utf-8")
        self.repo("core", "Spec: A1-R1, A1-R2")
        self.repo("app", "Spec: A1-R4")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manifest(self, version, status, goal_ids, searched):
        listed = ", ".join(f'"{g}"' for g in goal_ids)
        where = ", ".join(f'"{r}"' for r in searched)
        pathlib.Path(f"70-operations/versions/{version}.toml").write_text(
            f'version = "{version}"\nstatus = "{status}"\nrepos = ["core"]\n'
            f"satisfied_in = [{where}]\ngoals = [{listed}]\n", encoding="utf-8")

    def git(self, path, *args):
        return subprocess.run(["git", "-C", path, *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def repo(self, path, trailer):
        subprocess.run(["git", "init", "-q", path], check=True, capture_output=True)
        self.git(path, "config", "commit.gpgsign", "false")
        self.git(path, "config", "user.email", "t@t")
        self.git(path, "config", "user.name", "t")
        self.commit(path, "README", "x", trailer)

    def commit(self, path, name, text, trailer="Spec: GOV-R12"):
        (pathlib.Path(path) / name).write_text(text, encoding="utf-8")
        self.git(path, "add", name)
        self.git(path, "commit", "-q", "-m", f"feat: {name}", "-m", trailer)
        return self.git(path, "rev-parse", "HEAD")

    def checkouts(self):
        return ["--checkout", "core=core", "--checkout", "app=app"]

    def report(self, *extra):
        code, said = run_main([*self.checkouts(), "--json", "state.json", *extra])
        self.assertEqual(code, 0, said)
        data = json.loads(pathlib.Path("state.json").read_text(encoding="utf-8"))
        return {g["id"]: g for v in data["versions"] for g in v["goals"]}, data


class EachVerdictFromTheStateThatEarnsIt(Train):
    def test_the_five_verdicts(self):
        self.commit("core", "status.toml",
                    '[[requirement]]\nid = "A1-R1"\nstate = "done"\nevidence = ["README"]\n'
                    '[[requirement]]\nid = "A1-R3"\nstate = "done"\nevidence = ["README"]\n'
                    '[[requirement]]\nid = "A1-R5"\nstate = "partial"\n'
                    '[[requirement]]\nid = "Z9-R9"\nstate = "done"\nevidence = ["README"]\n')
        prs = {"app": [{"number": 7, "url": "https://x/7", "isDraft": True, "body": "",
                        "commits": [{"message": "feat: x\n\nSpec: A1-R5"}]},
                       {"number": 8, "url": "https://x/8", "isDraft": False,
                        "body": "Spec: A1-R1", "commits": None}]}
        pathlib.Path("prs.json").write_text(json.dumps(prs), encoding="utf-8")
        found, data = self.report("--prs", "prs.json")
        verdicts = {ident: g["verdict"] for ident, g in found.items()}
        self.assertEqual(verdicts, {"A1-R1": "met", "A1-R2": "unmarked", "A1-R3": "uncited",
                                    "A1-R4": "unmarked", "A1-R5": "claimed"})
        self.assertEqual(found["A1-R5"]["partial_in"], ["core"])
        self.assertEqual(found["A1-R5"]["claims"][0]["draft"], True)
        self.assertEqual([v["version"] for v in data["versions"]], ["0.2.0"],
                         "a released version is not on the report")

    def test_a_row_naming_where_it_landed_stands_for_a_citation(self):
        sha = self.git("core", "rev-parse", "HEAD")
        self.commit("core", "status.toml",
                    f'[[requirement]]\nid = "A1-R3"\nstate = "done"\nevidence = ["README"]\nlanded = "{sha}"\n'
                    '[[requirement]]\nid = "A1-R2"\nstate = "done"\nevidence = ["README"]\nlanded = "deadbeef"\n')
        found, _ = self.report()
        self.assertEqual(found["A1-R3"]["verdict"], "met")
        self.assertEqual(found["A1-R2"]["landed_in"], [], "a commit the history lacks is nothing")

    def test_the_binary_markdown_tracker_is_read_while_it_is_kept(self):
        self.commit("core", "IMPLEMENTATION-STATUS.md",
                    LEGACY_HEADER + "| x | `A1-R2` | ✅ | landed in `abc1234` |\n| x | `A1-R4` | ☐ | y |\n")
        self.commit("core", "status.toml", '[[milestone]]\nname = "M1"\n')
        found, _ = self.report()
        self.assertEqual(found["A1-R2"]["verdict"], "met")
        self.assertEqual(found["A1-R4"]["verdict"], "unmarked")

    def test_a_working_tree_edit_changes_nothing(self):
        (pathlib.Path("core") / "status.toml").write_text(
            '[[requirement]]\nid = "A1-R2"\nstate = "done"\nevidence = ["README"]\n', encoding="utf-8")
        found, _ = self.report("--ref", "HEAD")
        self.assertEqual(found["A1-R2"]["verdict"], "unmarked")


class ThePage(Train):
    def test_markdown_groups_by_verdict_and_folds_what_is_met(self):
        self.commit("core", "status.toml",
                    '[[requirement]]\nid = "A1-R1"\nstate = "done"\nevidence = ["README"]\n')
        for n in range(5):
            self.commit("app", f"f{n}", "x", "Spec: A1-R4")
        code, page = run_main([*self.checkouts(), "--version", "0.2.0"])
        self.assertEqual(code, 0)
        self.assertIn("## 0.2.0 — planned", page)
        self.assertIn("5 goals: 2 unmarked, 2 open, 1 met.", page)
        self.assertIn("<details><summary>Met</summary>", page)
        self.assertIn("and 3 more", page)

    def test_both_files_are_written_when_asked(self):
        code, said = run_main([*self.checkouts(), "--markdown", "STATE.md", "--json", "s.json"])
        self.assertEqual((code, said), (0, ""))
        self.assertTrue(pathlib.Path("STATE.md").read_text(encoding="utf-8").startswith("# Where"))


class Refusals(Train):
    def assert_refused(self, argv, words):
        code, said = run_main(argv)
        self.assertEqual(code, 2)
        self.assertIn(words, said)

    def test_a_checkout_that_is_not_name_equals_path(self):
        self.assert_refused(["--checkout", "core"], "name=path")

    def test_a_repository_searched_with_no_checkout(self):
        self.assert_refused(["--checkout", "core=core"], "no checkout of it was given")

    def test_a_version_with_no_manifest(self):
        self.assert_refused([*self.checkouts(), "--version", "9.9.9"], "no manifest for 9.9.9")

    def test_a_shallow_clone(self):
        shutil.move("app", "app-origin")
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        f"file://{pathlib.Path('app-origin').resolve()}", "app"],
                       check=True, capture_output=True)
        self.commit("app-origin", "later", "x")
        self.assert_refused(self.checkouts(), "shallow clone")

    def test_a_ref_git_would_read_as_an_option(self):
        self.assert_refused([*self.checkouts(), "--ref=--output=x"], "is not a revision")

    def test_a_ref_that_is_not_there(self):
        self.assert_refused([*self.checkouts(), "--ref", "nowhere"], "no history at nowhere")

    def test_an_unreadable_tracker(self):
        self.commit("core", "status.toml", "[[requirement]\n")
        self.assert_refused(self.checkouts(), "status.toml")

    def test_a_pull_request_file_that_is_not_json(self):
        pathlib.Path("prs.json").write_text("{", encoding="utf-8")
        self.assert_refused([*self.checkouts(), "--prs", "prs.json"], "::error::")


if __name__ == "__main__":
    unittest.main()
