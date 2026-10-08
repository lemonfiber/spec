#!/usr/bin/env python3
"""A repository's tracker is checked against the spec and the tree — OPS-R74, OPS-R75.

What is worth proving is that each claim a row can make is refused when nothing
backs it: an identifier the spec does not define, a done row naming no evidence,
evidence naming a path that is not there or a test a file does not hold, a done
row no version carries, and a commit the history does not have. Then the reverse
for each: the ordinary row passes. And the reading the gates share, a file in the
old milestone shape read as no tracker and a malformed one refused rather than
read as empty.

Stdlib unittest, no dependencies. The fixtures are a real spec tree and a real
git repository, because what is checked — a requirement row, a file on disk, a
commit in a history — is exactly what a patched reader would stop testing.
Run:  python3 scripts/test_status_check.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import status_check  # noqa: E402


def run_main(argv):
    """Call main() with argv patched; return (exit code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["status_check.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = status_check.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Tree(unittest.TestCase):
    """A spec under `spec/` and a repository under `repo/`."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        self.spec = pathlib.Path("spec")
        (self.spec / "70-operations" / "versions").mkdir(parents=True)
        self.feature("B1", "building", 3)
        self.manifest("0.1.0", ["B1-R1", "B1-R2"], satisfied=["repo", "web"])
        self.root = pathlib.Path("repo")
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (self.root / "src").mkdir()
        (self.root / "src" / "thing.rs").write_text("fn a_thing_is_held() {}\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "feat: a thing")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        return subprocess.run(["git", "-C", "repo", *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def feature(self, fid, maturity, count, retired=()):
        directory = self.spec / "10-functional" / "features" / "b-running"
        directory.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f"| **{fid}-R{n}** | *Withdrawn — carried elsewhere.* |" if n in retired
            else f"| **{fid}-R{n}** | Something MUST happen. |"
            for n in range(1, count + 1)
        )
        (directory / f"{fid.lower()}-thing.md").write_text(
            f"---\nid: {fid}\nmaturity: {maturity}\n---\n\n| ID | Requirement |\n"
            f"|----|----|\n{rows}\n", encoding="utf-8")

    def manifest(self, version, goals, satisfied=None, repos=("repo",)):
        listed = ", ".join(f'"{g}"' for g in goals)
        cut = ", ".join(f'"{r}"' for r in repos)
        extra = ""
        if satisfied is not None:
            extra = "satisfied_in = [" + ", ".join(f'"{r}"' for r in satisfied) + "]\n"
        (self.spec / "70-operations" / "versions" / f"{version}.toml").write_text(
            f'version = "{version}"\nrepos = [{cut}]\n{extra}goals = [{listed}]\n',
            encoding="utf-8")

    def tracker(self, body, path="repo/status.toml"):
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        return p

    def faults(self, body, siblings=None):
        rows = status_check.read(self.tracker(body), "repo")
        return status_check.check(rows, "status.toml", self.spec, self.root, siblings or {})


ROW = '[[requirement]]\nid = "B1-R1"\nstate = "done"\nevidence = ["src/thing.rs::a_thing_is_held"]\n'


class TheOrdinaryRowPasses(Tree):
    def test_a_done_row_with_evidence_that_is_there(self):
        self.assertEqual(self.faults(ROW), [])

    def test_a_partial_row_needs_no_evidence(self):
        self.assertEqual(self.faults('[[requirement]]\nid = "B1-R3"\nstate = "partial"\n'), [])

    def test_a_directory_is_evidence(self):
        self.assertEqual(self.faults(
            '[[requirement]]\nid = "B1-R1"\nstate = "done"\nevidence = ["src"]\n'), [])

    def test_a_commit_in_the_history_is_where_it_landed(self):
        sha = self.git("rev-parse", "HEAD")
        self.assertEqual(self.faults(ROW + f'landed = "{sha}"\n'), [])

    def test_evidence_in_another_repository_is_checked_where_it_is_given(self):
        web = pathlib.Path("web")
        (web / "src").mkdir(parents=True)
        (web / "src" / "App.svelte").write_text("<p>x</p>")
        body = '[[requirement]]\nid = "B1-R1"\nstate = "done"\nevidence = ["web:src/App.svelte"]\n'
        self.assertEqual(self.faults(body, {"web": web}), [])
        self.assertEqual(self.faults(body), [], "not given, so not judged here")
        missing = body.replace("App.svelte", "Gone.svelte")
        self.assertEqual(len(self.faults(missing, {"web": web})), 1)


class EachClaimIsBacked(Tree):
    def test_an_identifier_the_spec_does_not_define(self):
        faults = self.faults(ROW.replace("B1-R1", "Z9-R9"))
        self.assertEqual(len(faults), 1)
        self.assertIn("defined nowhere", faults[0])

    def test_a_copy_of_another_repository_defines_nothing(self):
        vendored = self.spec / "vendor" / "other"
        vendored.mkdir(parents=True)
        (vendored / "z9.md").write_text("| **Z9-R9** | Something MUST happen. |\n")
        self.assertIn("defined nowhere", self.faults(ROW.replace("B1-R1", "Z9-R9"))[0])

    def test_a_retired_requirement_no_version_locked(self):
        self.feature("B1", "building", 3, retired=(3,))
        faults = self.faults(ROW.replace("B1-R1", "B1-R3").replace('"done"', '"partial"'))
        self.assertEqual(len(faults), 1)
        self.assertIn("withdrawn or superseded and no version locked it", faults[0])

    def test_a_retired_requirement_a_version_shipped_stays_recorded(self):
        self.feature("B1", "building", 3, retired=(1,))
        self.assertEqual(self.faults(ROW), [])

    def test_a_done_row_no_version_carries_yet_is_recorded(self):
        self.assertEqual(self.faults(ROW.replace("B1-R1", "B1-R3")), [])

    def test_evidence_naming_no_such_path(self):
        faults = self.faults(ROW.replace("src/thing.rs", "src/gone.rs"))
        self.assertEqual(len(faults), 1)
        self.assertIn("no such path", faults[0])

    def test_evidence_naming_a_test_the_file_does_not_hold(self):
        faults = self.faults(ROW.replace("a_thing_is_held", "a_thing_nobody_wrote"))
        self.assertEqual(len(faults), 1)
        self.assertIn("does not contain `a_thing_nobody_wrote`", faults[0])

    def test_text_cannot_be_promised_of_a_directory(self):
        faults = self.faults(ROW.replace("src/thing.rs", "src"))
        self.assertIn("does not contain", faults[0])

    def test_a_commit_the_history_does_not_have(self):
        faults = self.faults(ROW + 'landed = "deadbeefdeadbeef"\n')
        self.assertEqual(len(faults), 1)
        self.assertIn("no such commit", faults[0])


class TheShapeIsRefusedBeforeItIsRead(Tree):
    def refused(self, body):
        path = self.tracker(body)
        with self.assertRaises(status_check.Unreadable) as caught:
            status_check.read(path, "repo")
        return str(caught.exception)

    def test_an_absent_file_is_no_tracker(self):
        self.assertIsNone(status_check.read(pathlib.Path("repo/none.toml"), "repo"))

    def test_the_milestone_shape_is_no_tracker(self):
        self.assertIsNone(status_check.read(self.tracker('[[milestone]]\nname = "M1"\n'), "repo"))

    def test_bytes_that_are_not_text(self):
        path = pathlib.Path("repo/status.toml")
        path.write_bytes(b"\xff\xfe")
        with self.assertRaises(status_check.Unreadable):
            status_check.read(path, "repo")

    def test_toml_that_does_not_parse(self):
        self.assertIn("status.toml", self.refused("[[requirement]\n"))

    def test_a_key_a_tracker_does_not_hold(self):
        self.assertIn("`preamble` is not something", self.refused('preamble = "x"\n'))

    def test_requirement_that_is_not_an_array_of_tables(self):
        self.assertIn("array of tables", self.refused('requirement = "x"\n'))

    def test_an_entry_that_is_not_a_table(self):
        self.assertIn("is not a table", self.refused('requirement = ["x"]\n'))

    def test_an_unknown_key_and_a_missing_one(self):
        said = self.refused('[[requirement]]\nid = "B1-R1"\nwhy = "x"\n')
        self.assertIn("carries `why`", said)
        self.assertIn("has no `state`", said)

    def test_an_identifier_that_is_not_one(self):
        self.assertIn("not a requirement identifier",
                      self.refused('[[requirement]]\nid = "B1"\nstate = "open"\n'))

    def test_a_requirement_recorded_twice(self):
        row = '[[requirement]]\nid = "B1-R2"\nstate = "open"\n'
        self.assertIn("recorded twice", self.refused(row + row))

    def test_a_state_that_is_not_one(self):
        self.assertIn("`finished` is not one of",
                      self.refused('[[requirement]]\nid = "B1-R2"\nstate = "finished"\n'))

    def test_evidence_that_is_not_a_list_of_paths(self):
        self.assertIn("list of paths",
                      self.refused('[[requirement]]\nid = "B1-R2"\nstate = "open"\nevidence = "x"\n'))

    def test_a_done_row_naming_no_evidence(self):
        self.assertIn("names no evidence",
                      self.refused('[[requirement]]\nid = "B1-R2"\nstate = "done"\n'))

    def test_landed_that_is_not_a_commit(self):
        self.assertIn("hexadecimal",
                      self.refused(ROW + 'landed = "HEAD"\n'))


class ARepositoryPastAThousandLinesSplitsByFeature(Tree):
    def split(self, files):
        directory = self.root / "status"
        directory.mkdir()
        for name, body in files.items():
            (directory / name).write_text(body, encoding="utf-8")

    def test_each_feature_file_is_read(self):
        self.split({"B1.toml": 'requirement = [\n  { id = "B1-R1", state = "done", evidence = ["src"] },\n]\n'})
        rows = status_check.load(self.root, "repo")
        self.assertEqual([row.id for row in rows], ["B1-R1"])

    def test_a_row_in_another_features_file(self):
        self.split({"C1.toml": 'requirement = [{ id = "B1-R1", state = "open" }]\n'})
        with self.assertRaises(status_check.Unreadable) as caught:
            status_check.load(self.root, "repo")
        self.assertIn("belongs in status/B1.toml", str(caught.exception))

    def test_a_requirement_in_two_files(self):
        row = 'requirement = [{ id = "B1-R1", state = "open" }]\n'
        self.split({"B1.toml": row, "B1.more.toml": row})
        with self.assertRaises(status_check.Unreadable) as caught:
            status_check.load(self.root, "repo")
        self.assertIn("is also recorded in", str(caught.exception))

    def test_both_shapes_at_once(self):
        self.tracker(ROW)
        self.split({"B1.toml": ""})
        with self.assertRaises(status_check.Unreadable) as caught:
            status_check.load(self.root, "repo")
        self.assertIn("keeps both", str(caught.exception))

    def test_bytes_that_are_not_text_in_a_feature_file(self):
        (self.root / "status").mkdir()
        (self.root / "status" / "B1.toml").write_bytes(b"\xff\xfe")
        with self.assertRaises(status_check.Unreadable):
            status_check.load(self.root, "repo")

    def test_the_short_row_form_reads_as_the_table_form(self):
        self.tracker('requirement = [\n  { id = "B1-R1", state = "done", evidence = ["src/thing.rs::a_thing_is_held"] },\n]\n')
        self.assertEqual(status_check.load(self.root, "repo"),
                         status_check.read(pathlib.Path("repo/status.toml"), "repo"))


class TheCommandLine(Tree):
    def test_check_passes_and_refuses(self):
        self.tracker(ROW)
        code, said = run_main(["check", "--spec", "spec", "--repo-root", "repo"])
        self.assertEqual(code, 0, said)
        self.tracker(ROW.replace("B1-R1", "Z9-R9"))
        code, said = run_main(["check", "--spec", "spec", "--repo-root", "repo", "--sibling", "web=web"])
        self.assertEqual(code, 1)
        self.assertIn("Z9-R9 is defined nowhere", said)

    def test_no_tracker_is_nothing_to_check(self):
        code, said = run_main(["check", "--spec", "spec", "--repo-root", "repo"])
        self.assertEqual(code, 0)
        self.assertIn("nothing to check", said)

    def test_an_unreadable_tracker_is_a_question_not_answered(self):
        self.tracker("[[requirement]\n")
        code, said = run_main(["check", "--spec", "spec", "--repo-root", "repo"])
        self.assertEqual(code, 2)
        self.assertIn("::error::", said)

    def test_a_sibling_that_is_not_name_equals_path(self):
        self.tracker(ROW)
        code, said = run_main(["check", "--spec", "spec", "--repo-root", "repo",
                               "--sibling", "web"])
        self.assertEqual(code, 2)
        self.assertIn("name=path", said)

    def test_a_spec_with_no_manifests_cannot_be_asked(self):
        code, said = run_main(["repos", "--spec", "nowhere"])
        self.assertEqual(code, 2)
        self.assertIn("no version manifests", said)

    def test_repos_names_every_repository_some_version_is_satisfied_in(self):
        self.manifest("0.2.0", ["B1-R3"])
        (self.spec / "70-operations" / "versions" / "TEMPLATE.toml").write_text(
            'repos = ["template-only"]\n', encoding="utf-8")
        code, said = run_main(["repos", "--spec", "spec"])
        self.assertEqual(code, 0)
        self.assertEqual(said.split(), ["repo", "web"])


if __name__ == "__main__":
    unittest.main()
