#!/usr/bin/env python3
"""A feature's maturity is derived from the trackers and the manifests — OPS-R73, OPS-R78.

Each of the four derived states is driven from the trackers that earn it, the
refusal is checked for naming the feature, what it says and what it should say,
and `--write` is checked for rewriting the one line and nothing else. A withdrawn
feature is a decision and is left alone; a retired requirement is asked of no one.

Stdlib unittest, a real spec tree in a temporary directory.
Run:  python3 scripts/test_maturity.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import maturity  # noqa: E402

LEGACY_HEADER = "| Deliverable | Spec | Status | Landing |\n|---|---|---|---|\n"


def run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["maturity.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = maturity.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Catalogue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path("spec/70-operations/versions").mkdir(parents=True)
        self.manifest("0.1.0", "released", ["B1-R1", "B1-R2"])
        self.manifest("0.2.0", "planned", ["B1-R3"])
        (pathlib.Path("spec/70-operations/versions") / "TEMPLATE.toml").write_text(
            'version = "X"\nstatus = "released"\ngoals = ["B1-R3"]\n', encoding="utf-8")
        pathlib.Path("repo").mkdir()
        (pathlib.Path("repo") / "f").write_text("x")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manifest(self, version, status, goals):
        listed = ", ".join(f'"{g}"' for g in goals)
        pathlib.Path(f"spec/70-operations/versions/{version}.toml").write_text(
            f'version = "{version}"\nstatus = "{status}"\nrepos = ["repo"]\ngoals = [{listed}]\n',
            encoding="utf-8")

    def feature(self, fid, says, count, retired=(), shipped=None):
        directory = pathlib.Path("spec/10-functional/features/b-running")
        directory.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f"| **{fid}-R{n}** | *Withdrawn — carried elsewhere.* |" if n in retired
            else f"| **{fid}-R{n}** | Something MUST happen. |"
            for n in range(1, count + 1))
        path = directory / f"{fid.lower()}.md"
        version = f"shipped: {shipped}\n" if shipped else ""
        path.write_text(f"---\nid: {fid}\nmaturity: {says}\n{version}labels: [x]\n---\n\n{rows}\n",
                        encoding="utf-8")
        return path

    def done(self, *ids):
        body = "".join(f'[[requirement]]\nid = "{i}"\nstate = "done"\nevidence = ["f"]\n' for i in ids)
        pathlib.Path("repo/status.toml").write_text(body, encoding="utf-8")
        return ["--tracker", "repo=repo"]

    def act(self, *args):
        return run_main(["--spec", "spec", *args])


class TheFourStates(Catalogue):
    def test_derive_names_each_state(self):
        shipped = {"B1-R1", "B1-R2"}
        reqs = {"B1-R1", "B1-R2"}
        self.assertEqual(maturity.derive(reqs, set(), shipped), "planned")
        self.assertEqual(maturity.derive(reqs, {"B1-R1"}, shipped), "building")
        self.assertEqual(maturity.derive(reqs, reqs, shipped), "shipped")
        self.assertEqual(maturity.derive(reqs | {"B1-R3"}, reqs | {"B1-R3"}, shipped), "built")

    def test_a_catalogue_that_agrees_passes(self):
        self.feature("B1", "building", 3)
        code, said = self.act(*self.done("B1-R1"), "--check")
        self.assertEqual(code, 0, said)

    def test_a_planned_feature_with_a_requirement_done_is_refused_by_name(self):
        self.feature("B1", "planned", 3)
        code, said = self.act(*self.done("B1-R1"), "--check")
        self.assertEqual(code, 1)
        self.assertIn("B1 is `planned` in the catalogue, and the trackers and manifests make it `building`", said)
        self.assertIn("1 of its 3", said)

    def test_a_finished_feature_missing_a_requirement_is_refused(self):
        """OPS-R73: a requirement added to a finished feature reopens it."""
        self.feature("B1", "shipped", 3, shipped="0.1.0")
        code, said = self.act(*self.done("B1-R1", "B1-R2"), "--check")
        self.assertEqual(code, 1)
        self.assertIn("is `shipped 0.1.0` in the catalogue", said)
        self.assertIn("make it `building`", said)

    def test_a_retired_requirement_is_asked_of_no_one(self):
        self.feature("B1", "shipped", 3, retired=(3,), shipped="0.1.0")
        code, said = self.act(*self.done("B1-R1", "B1-R2"), "--check")
        self.assertEqual(code, 0, said)

    def test_a_withdrawn_feature_is_left_as_decided(self):
        self.feature("B1", "withdrawn", 3)
        code, said = self.act(*self.done("B1-R1"), "--check")
        self.assertEqual(code, 0, said)

    def test_a_tracker_still_kept_as_markdown_is_read_beside_them(self):
        self.feature("B1", "building", 3)
        pathlib.Path("repo/status.toml").write_text('[[milestone]]\nname = "M1"\n', encoding="utf-8")
        pathlib.Path("t.md").write_text(LEGACY_HEADER + "| x | `B1-R1` | ✅ | y |\n", encoding="utf-8")
        code, said = self.act("--tracker", "repo=repo", "--legacy", "t.md", "--check")
        self.assertEqual(code, 0, said)


class Writing(Catalogue):
    def test_write_rewrites_the_line_and_nothing_else(self):
        path = self.feature("B1", "planned", 3)
        code, said = self.act(*self.done("B1-R1", "B1-R2", "B1-R3"), "--write")
        self.assertEqual(code, 0)
        self.assertIn("B1: planned → built", said)
        self.assertIn("maturity: built\nlabels: [x]", path.read_text(encoding="utf-8"))
        self.assertEqual(self.act("--tracker", "repo=repo", "--check")[0], 0)


    def test_shipped_names_the_latest_released_version_and_leaves_with_it(self):
        self.manifest("0.3.0", "released", ["B1-R2"])
        path = self.feature("B1", "built", 2)
        _, said = self.act(*self.done("B1-R1", "B1-R2"), "--write")
        self.assertIn("B1: built → shipped 0.3.0", said)
        self.assertIn("maturity: shipped\nshipped: 0.3.0\nlabels", path.read_text(encoding="utf-8"))
        _, said = self.act(*self.done("B1-R1"), "--write")
        self.assertIn("B1: shipped 0.3.0 → building", said)
        self.assertIn("maturity: building\nlabels", path.read_text(encoding="utf-8"))

    def test_a_wrong_shipped_version_alone_is_refused(self):
        self.feature("B1", "shipped", 2, shipped="0.0.9")
        code, said = self.act(*self.done("B1-R1", "B1-R2"), "--check")
        self.assertEqual(code, 1)
        self.assertIn("make it `shipped 0.1.0`", said)


class Refusals(Catalogue):
    def test_a_spec_with_no_manifests(self):
        code, said = run_main(["--spec", "repo", "--check"])
        self.assertEqual(code, 2)
        self.assertIn("no version manifests", said)

    def assert_unread(self, args, words):
        """An input not read stops both modes, so `--write` lowers nothing either."""
        path = self.feature("B1", "shipped", 2, shipped="0.1.0")
        before = path.read_text(encoding="utf-8")
        for mode in ("--check", "--write"):
            code, said = self.act(*args, mode)
            self.assertEqual(code, 2, said)
            self.assertIn(words, said)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_an_unreadable_tracker(self):
        pathlib.Path("repo/status.toml").write_text("[[requirement]\n", encoding="utf-8")
        self.assert_unread(["--tracker", "repo=repo"], "::error::")

    def test_a_repository_with_no_tracker_given(self):
        self.manifest("0.3.0", "planned", ["B1-R3"])
        pathlib.Path("spec/70-operations/versions/0.3.0.toml").write_text(
            'version = "0.3.0"\nstatus = "planned"\nrepos = ["repo"]\n'
            'satisfied_in = ["repo", "web"]\ngoals = ["B1-R3"]\n', encoding="utf-8")
        self.assert_unread(self.done("B1-R1", "B1-R2"), "no tracker given for web")

    def test_a_tracker_path_that_is_not_there(self):
        pathlib.Path("elsewhere").mkdir()
        self.assert_unread(["--tracker", "repo=elsewhere"], "no tracker under")

    def test_the_old_shape_with_no_page_to_read_it_through(self):
        pathlib.Path("repo/status.toml").write_text('[[milestone]]\nname = "M1"\n', encoding="utf-8")
        self.assert_unread(["--tracker", "repo=repo"], "no --legacy page")

    def test_a_page_that_is_not_there_or_records_nothing(self):
        args = self.done("B1-R1", "B1-R2")
        self.assert_unread([*args, "--legacy", "gone.md"], "no Markdown tracker at")
        pathlib.Path("t.md").write_text(LEGACY_HEADER, encoding="utf-8")
        self.assert_unread([*args, "--legacy", "t.md"], "records nothing done")

    def test_a_feature_doc_with_no_identifier_is_not_a_feature(self):
        directory = pathlib.Path("spec/10-functional/features/b-running")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "README.md").write_text("# The running area\n", encoding="utf-8")
        self.assertEqual(self.act(*self.done(), "--check")[0], 0)


if __name__ == "__main__":
    unittest.main()
