#!/usr/bin/env python3
"""The CodeQL alert gate, put in front of every case that would break it.

The gate carries its own `--self-test`, and every workflow that calls it runs
that first — which answers "does this still work" on the machine that is about to
trust it. What it cannot answer is "would it notice if it stopped": a self-test
whose assertions have all quietly become tautologies passes just as loudly. So
the tests below do both. They drive the judgement directly, and they break each
function the self-test depends on and assert the self-test *says so*.

This file lives in `spec` because `shared/gates/` is where the gate is
maintained; every other repository carries a byte-identical copy that
`check_shared_files.py` refuses to let drift.

Stdlib unittest plus PyYAML, which the gate itself needs.
Run:  python3 scripts/test_no_open_codeql_alert.py
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE.parent / "shared" / "gates" / "no_open_codeql_alert.py"

_spec = importlib.util.spec_from_file_location("no_open_codeql_alert", GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

RUST = gate.RUST
ACTIONS = gate.ACTIONS
PYTHON = gate.PYTHON
GENERATED = f".github/workflows/codeql.yml:analyze{PYTHON}"

MATRIX = """
jobs:
  analyze:
    strategy:
      matrix:
        language: [rust, actions]
"""
SINGLE = """
jobs:
  analyze:
    steps:
      - uses: github/codeql-action/init@v3
        with:
          languages: actions
"""

ALERT = {
    "rule": {"id": "rust/path-injection", "security_severity_level": "high"},
    "most_recent_instance": {"location": {"path": "a.rs", "start_line": 7}},
}


@contextlib.contextmanager
def swapped(name, value):
    """One module attribute replaced, and put back however the test ends."""
    was = getattr(gate, name)
    setattr(gate, name, value)
    try:
        yield
    finally:
        setattr(gate, name, was)


@contextlib.contextmanager
def working_in(path):
    """`inside()` judges against the working directory, so tests move into one."""
    was = os.getcwd()
    os.chdir(path)
    try:
        yield pathlib.Path(path)
    finally:
        os.chdir(was)


class Flattening(unittest.TestCase):
    """`--paginate --slurp` wraps pages; one page arrives unwrapped."""

    def test_pages_are_read_as_one_list(self):
        self.assertEqual(gate.flatten([[ALERT], []]), [ALERT])

    def test_a_single_page_is_read_as_it_came(self):
        self.assertEqual(gate.flatten([ALERT]), [ALERT])

    def test_nothing_stays_nothing(self):
        self.assertEqual(gate.flatten([]), [])


class Naming(unittest.TestCase):
    """Four of six repositories let GitHub build the category, so both shapes
    have to name the same language."""

    def test_a_category_github_generated(self):
        self.assertEqual(gate.named(GENERATED), "language:python")

    def test_a_category_the_workflow_wrote(self):
        self.assertEqual(gate.named(RUST), "language:rust")

    def test_a_language_is_not_satisfied_by_one_it_prefixes(self):
        self.assertEqual(gate.missing(["/language:rustacean"], [RUST]), [RUST])

    def test_a_generated_category_satisfies_the_language_it_names(self):
        self.assertEqual(gate.missing([GENERATED], [PYTHON]), [])

    def test_both_styles_at_once(self):
        self.assertEqual(gate.missing([GENERATED, RUST], [PYTHON, RUST]), [])

    def test_the_language_that_never_landed_is_the_one_named(self):
        self.assertEqual(gate.missing([ACTIONS], [RUST, ACTIONS]), [RUST])


class Analyses(unittest.TestCase):
    """An analysis of the ref is not an analysis of this commit."""

    def setUp(self):
        self.here = gate._analysis("aaa", RUST)
        self.stale = gate._analysis("bbb", RUST)

    def test_no_analysis_at_all(self):
        self.assertEqual(gate.at([], "aaa"), [])
        self.assertEqual(gate.at([[]], "aaa"), [])

    def test_an_analysis_of_a_commit_since_replaced(self):
        self.assertEqual(gate.at([self.stale], "aaa"), [])

    def test_another_tools_analysis(self):
        other = gate._analysis("aaa", RUST, tool="Other")
        self.assertEqual(gate.at([other], "aaa"), [])

    def test_an_analysis_of_this_commit(self):
        self.assertEqual(gate.at([self.here], "aaa"), [RUST])

    def test_paged_analyses(self):
        self.assertEqual(gate.at([[self.here], [self.stale]], "aaa"), [RUST])


class ReadingTheWorkflow(unittest.TestCase):
    """The languages come off the caller's own workflow, in either shape the
    organisation writes them."""

    def test_a_matrix(self):
        self.assertEqual(gate.expected(MATRIX), [RUST, ACTIONS])

    def test_one_language_on_the_init_step(self):
        self.assertEqual(gate.expected(SINGLE), [ACTIONS])

    def test_a_comma_separated_languages(self):
        text = SINGLE.replace("languages: actions", "languages: actions, python")
        self.assertEqual(gate.expected(text), [ACTIONS, PYTHON])

    def test_a_workflow_naming_no_language_is_refused(self):
        for empty in ("jobs: {}\n", "jobs:\n  analyze:\n    steps: []\n", ""):
            with self.subTest(workflow=empty), self.assertRaises(ValueError):
                gate.expected(empty)

    def test_a_step_that_is_not_the_init_step_is_passed_over(self):
        text = SINGLE.replace("codeql-action/init@v3", "actions/checkout@v5")
        with self.assertRaises(ValueError):
            gate.expected(text)


class Judging(unittest.TestCase):
    """Nought where nothing is open, one where anything is — and one where
    nothing was looked at, which is the sentence this gate exists for."""

    def test_an_open_alert_refuses_the_branch(self):
        out = io.StringIO()
        self.assertEqual(gate.judge([ALERT], out), 1)
        self.assertIn("rust/path-injection", out.getvalue())
        self.assertIn("a.rs:7", out.getvalue())
        self.assertIn("1 open alert(s)", out.getvalue())

    def test_an_alert_missing_every_detail_still_reports(self):
        out = io.StringIO()
        self.assertEqual(gate.judge([{}], out), 1)
        self.assertIn("?", out.getvalue())

    def test_an_alert_with_no_security_severity_falls_back(self):
        out = io.StringIO()
        gate.judge([{"rule": {"id": "x", "severity": "warning"}}], out)
        self.assertIn("warning", out.getvalue())

    def test_no_open_alert_allows_the_branch(self):
        out = io.StringIO()
        self.assertEqual(gate.judge([], out), 0)
        self.assertIn("No open CodeQL alert", out.getvalue())

    def test_an_empty_list_about_a_commit_nobody_analysed(self):
        out = io.StringIO()
        self.assertEqual(gate.judge([], out, seen=False), 1)
        self.assertIn("has read nothing", out.getvalue())


class ReadingAPath(unittest.TestCase):
    """Both files are named by the caller and interpolated straight into a read."""

    def test_a_path_inside_the_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp, working_in(tmp) as here:
            self.assertEqual(gate.inside("scripts/x.py"), (here / "scripts/x.py").resolve())

    def test_the_working_directory_itself(self):
        with tempfile.TemporaryDirectory() as tmp, working_in(tmp) as here:
            self.assertEqual(gate.inside("."), here.resolve())

    def test_a_path_that_walks_out(self):
        with tempfile.TemporaryDirectory() as tmp, working_in(tmp):
            for outside in ("../../etc/passwd", "/etc/passwd", "a/../../../etc/passwd"):
                with self.subTest(path=outside), self.assertRaises(ValueError):
                    gate.inside(outside)


class TheSelfTestPasses(unittest.TestCase):
    def test_every_claim_holds(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gate.self_test(), 0)
        self.assertIn("every claim holds", out.getvalue())


class TheSelfTestNotices(unittest.TestCase):
    """A self-test nobody has watched fail is a self-test nobody knows works.

    Each function the self-test leans on is replaced with a broken one, and the
    complaint it is supposed to raise is asserted by name. Without this, the
    self-test could decay into a run of tautologies and still print that every
    claim holds — which is the same failure as a gate passing on an empty list.
    """

    def complaints(self, name, broken, reading):
        with swapped(name, broken), contextlib.redirect_stderr(io.StringIO()):
            return getattr(gate, reading)()

    def test_an_alert_list_nothing_reads(self):
        said = self.complaints("flatten", lambda read: [], "_reading_alerts")
        self.assertIn("pages of alerts were not read as one list", said)
        self.assertIn("a single page of alerts was not read as it came", said)

    def test_a_judgement_that_always_allows(self):
        said = self.complaints("judge", lambda *a, **k: 0, "_reading_alerts")
        self.assertIn("an open alert did not refuse the branch", said)
        self.assertIn(
            "a commit with no analysis was allowed on an empty alert list", said
        )

    def test_a_judgement_that_always_refuses(self):
        said = self.complaints("judge", lambda *a, **k: 1, "_reading_alerts")
        self.assertIn("no open alert did not allow the branch", said)

    def test_an_analysis_reader_that_says_yes_to_everything(self):
        said = self.complaints(
            "at", lambda analyses, sha: [RUST], "_reading_analyses"
        )
        self.assertIn("no analysis was read as an analysis", said)
        self.assertIn("an analysis of another commit was read as this one's", said)
        self.assertIn("another tool's analysis was read as CodeQL's", said)

    def test_an_analysis_reader_that_finds_nothing(self):
        said = self.complaints("at", lambda analyses, sha: [], "_reading_analyses")
        self.assertIn("an analysis of this commit was not seen", said)
        self.assertIn("paged analyses were not read as one list", said)

    def test_a_category_reader_that_answers_the_same_thing_every_time(self):
        said = self.complaints("named", lambda category: "x", "_reading_a_category")
        self.assertIn("a category GitHub generated was not read down to its language", said)
        self.assertIn("a category this repository writes was not read", said)
        self.assertIn("language:rust was satisfied by language:rustacean", said)

    def test_a_missing_check_that_calls_everything_absent(self):
        said = self.complaints(
            "missing", lambda analysed, wanted: list(wanted), "_reading_a_category"
        )
        self.assertIn("a generated category did not satisfy the language it names", said)
        self.assertIn("a mix of both category styles was not read", said)

    def test_a_workflow_reader_that_invents_a_language(self):
        said = self.complaints(
            "expected", lambda workflow: [PYTHON], "_reading_the_workflow"
        )
        self.assertIn("the matrix's languages were not read off the workflow", said)
        self.assertIn("a complete set of analyses was called incomplete", said)
        self.assertIn("a language whose analysis never landed was not named", said)
        self.assertIn("a job with one language and no matrix was not read", said)
        self.assertIn("a comma-separated languages: was not read as a list", said)
        self.assertIn("a workflow naming no language was accepted", said)

    def test_a_path_check_that_refuses_everything(self):
        def refuse(named):
            raise ValueError(named)

        said = self.complaints("inside", refuse, "_reading_a_path")
        self.assertIn("a path inside the working directory was refused", said)

    def test_a_path_check_that_refuses_nothing(self):
        said = self.complaints("inside", lambda named: named, "_reading_a_path")
        self.assertIn("/etc/passwd was read rather than refused", said)

    def test_the_self_test_fails_out_loud(self):
        out, err = io.StringIO(), io.StringIO()
        with swapped("judge", lambda *a, **k: 0), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            self.assertEqual(gate.self_test(), 1)
        self.assertIn("FAILED", out.getvalue())
        self.assertIn("self-test:", err.getvalue())


class Invoked(unittest.TestCase):
    """The command line, which is the only part a workflow touches."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, True))
        (self.tmp / ".github" / "workflows").mkdir(parents=True)
        self.workflow = ".github/workflows/codeql.yml"
        (self.tmp / self.workflow).write_text(MATRIX, encoding="utf-8")

    def analyses(self, *rows, name="analyses.json"):
        (self.tmp / name).write_text(json.dumps(list(rows)), encoding="utf-8")
        return name

    def run_main(self, argv, stdin="[]"):
        out = io.StringIO()
        was_in, was_argv = sys.stdin, sys.argv
        sys.stdin = io.StringIO(stdin)
        sys.argv = ["no_open_codeql_alert.py", *argv]
        try:
            with working_in(self.tmp), contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = gate.main()
        finally:
            sys.stdin, sys.argv = was_in, was_argv
        return code, out.getvalue()

    def test_the_self_test_through_the_command_line(self):
        code, said = self.run_main(["--self-test"])
        self.assertEqual(code, 0, said)

    def test_the_three_arguments_are_all_required(self):
        for argv in ([], ["--sha", "aaa"], ["--analyses", "a.json", "--sha", "aaa"]):
            with self.subTest(argv=argv):
                code, said = self.run_main(argv)
                self.assertEqual(code, 1)
                self.assertIn("will not guess which", said)

    def test_a_workflow_path_that_leaves_the_working_directory(self):
        code, said = self.run_main(
            ["--analyses", self.analyses(), "--sha", "aaa", "--workflow", "../x.yml"]
        )
        self.assertEqual(code, 1)
        self.assertIn("refusing to read", said)

    def test_a_workflow_that_is_not_there(self):
        code, said = self.run_main(
            ["--analyses", self.analyses(), "--sha", "aaa",
             "--workflow", ".github/workflows/absent.yml"]
        )
        self.assertEqual(code, 1)
        self.assertIn("::error::", said)

    def test_waiting_while_a_language_has_not_landed(self):
        rows = self.analyses(gate._analysis("aaa", RUST))
        code, said = self.run_main(
            ["--analyses", rows, "--sha", "aaa", "--workflow", self.workflow,
             "--complete-only"]
        )
        self.assertEqual(code, 1)
        self.assertIn("waiting on", said)
        self.assertIn(ACTIONS, said)

    def test_waiting_ends_when_every_language_has_landed(self):
        rows = self.analyses(
            gate._analysis("aaa", RUST), gate._analysis("aaa", ACTIONS)
        )
        code, said = self.run_main(
            ["--analyses", rows, "--sha", "aaa", "--workflow", self.workflow,
             "--complete-only"]
        )
        self.assertEqual(code, 0, said)
        self.assertIn("analysed", said)

    def test_a_commit_with_nothing_analysed_at_all(self):
        code, said = self.run_main(
            ["--analyses", self.analyses(), "--sha", "aaa", "--workflow",
             self.workflow, "--complete-only"]
        )
        self.assertEqual(code, 1)
        self.assertIn("nothing analysed", said)

    def test_an_alert_list_one_analysis_short_is_refused(self):
        rows = self.analyses(gate._analysis("aaa", RUST))
        code, said = self.run_main(
            ["--analyses", rows, "--sha", "aaa", "--workflow", self.workflow]
        )
        self.assertEqual(code, 1)
        self.assertIn("cannot carry a finding from an analysis that did not land", said)

    def test_a_complete_analysis_and_no_open_alert(self):
        rows = self.analyses(
            gate._analysis("aaa", RUST), gate._analysis("aaa", ACTIONS)
        )
        code, said = self.run_main(
            ["--analyses", rows, "--sha", "aaa", "--workflow", self.workflow]
        )
        self.assertEqual(code, 0, said)
        self.assertIn("No open CodeQL alert stands against this ref.", said)

    def test_a_complete_analysis_and_an_open_alert(self):
        rows = self.analyses(
            gate._analysis("aaa", RUST), gate._analysis("aaa", ACTIONS)
        )
        code, said = self.run_main(
            ["--analyses", rows, "--sha", "aaa", "--workflow", self.workflow],
            stdin=json.dumps([ALERT]),
        )
        self.assertEqual(code, 1)
        self.assertIn("rust/path-injection", said)


if __name__ == "__main__":
    unittest.main()
