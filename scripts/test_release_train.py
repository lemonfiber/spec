#!/usr/bin/env python3
"""Coverage tests for the release-train scripts — gate, set_status,
check_stageable, tracker_body, pr_goals, submodule_pins, manifest_repos,
check_image_pins.

status_lint has its own suite in test_status_lint.py: it gates every
repository through the spec-check workflow, not only a release.

Stdlib unittest, no dependencies (the repo has none). The scripts are imported
and their functions called in-process so coverage sees every branch; git and
manifest fixtures are built in a temporary working directory that mirrors the CI
layout. Run:  python3 scripts/test_release_train.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

#: The header every tracker table carries, and without which no row in it has a
#: status to read. Spelled once here so a fixture is a row rather than a table.
HEADER = "| Deliverable | Spec | Status | Landing / notes |\n|---|---|---|---|\n"

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_image_pins  # noqa: E402
import check_stageable  # noqa: E402
import gate  # noqa: E402
import manifest_repos  # noqa: E402
import pr_goals  # noqa: E402
import set_status  # noqa: E402
import submodule_pins  # noqa: E402
import tracker_body  # noqa: E402
import train_step  # noqa: E402


def run_main(mod, argv, stdin=""):
    """Call a module's main() with argv/stdin patched; return (exit_code, what it said).

    `sys.exit("::error::…")` is how these gates refuse, and the interpreter prints
    that string only when nothing catches the SystemExit. Caught here it would be
    dropped, leaving a test able to see *that* a gate refused and never *which*
    thing it refused — so the message joins the captured stdout.
    """
    out = io.StringIO()
    saved_argv, saved_stdin = sys.argv, sys.stdin
    sys.argv = [mod.__name__, *argv]
    sys.stdin = io.StringIO(stdin)
    code, said = 0, ""
    try:
        with contextlib.redirect_stdout(out):
            result = mod.main()
        code = result if isinstance(result, int) else 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        said = "" if exc.code is None or isinstance(exc.code, int) else f"{exc.code}\n"
    finally:
        sys.argv, sys.stdin = saved_argv, saved_stdin
    return code, out.getvalue() + said


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path("70-operations/versions").mkdir(parents=True)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manifest(self, name, status="staged", goals=("B1-R4",), repos=("lf",)):
        g = ", ".join(f'"{x}"' for x in goals)
        r = ", ".join(f'"{x}"' for x in repos)
        pathlib.Path(f"70-operations/versions/{name}.toml").write_text(
            f'version = "{name}"\nstatus  = "{status}"\nrepos = [{r}]\ngoals = [{g}]\n',
            encoding="utf-8")

    def repo(self, path, trailer="Spec: B1-R4, C1-R3"):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        def run(*a):
            return subprocess.run(["git", "-C", path, *a], check=True, capture_output=True)
        subprocess.run(["git", "init", "-q", path], check=True, capture_output=True)
        run("config", "commit.gpgsign", "false")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        (pathlib.Path(path) / "f").write_text("x")
        run("add", "f")
        run("commit", "-q", "-m", "feat: thing", "-m", trailer)

    def status_file(self, path="checkouts/lf/IMPLEMENTATION-STATUS.md"):
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HEADER + "| x | **B1-R4** | ✅ | y |\n"
                     "| x | **C1-R1..R12** | ✅ | y |\n"
                     "| x | **Z9-R9** | ☐ | y |\n", encoding="utf-8")
        return str(p)


class LandedTests(Workspace):
    """A row may name the commit that finished a goal, and it is checked — OPS-R34."""

    def head_of(self, path):
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def rows(self, text, path="checkouts/lf/IMPLEMENTATION-STATUS.md"):
        """A tracker holding `text` as the body of one table.

        The header is not decoration: a row's status is read from the column its
        table names, so a bare row has no status to read and cannot be done.
        """
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HEADER + text, encoding="utf-8")
        return p

    def test_a_row_naming_a_commit_in_the_history_carries_its_goals(self):
        """The whole point: a goal nothing cites, finished by a commit that is there."""
        self.repo("checkouts/lf", trailer="Spec: B1-R4")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| x | **Z9-R9** | ✅ | landed in `{sha}` |\n")
        landed = gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")})
        self.assertIn("Z9-R9", landed)

    def test_a_row_naming_a_commit_nobody_has_carries_nothing(self):
        """What stops this being a way to tick anything by writing eight characters."""
        self.repo("checkouts/lf")
        rows = self.rows("| x | **Z9-R9** | ✅ | landed in `deadbeefdeadbeef` |\n")
        landed = gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")})
        self.assertEqual(landed, set())

    def test_a_row_that_is_not_done_carries_nothing_however_it_is_written(self):
        self.repo("checkouts/lf")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| x | **Z9-R9** | ☐ | landed in `{sha}` |\n")
        self.assertEqual(gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")}), set())

    def test_a_done_row_with_no_commit_named_carries_nothing_here(self):
        """The ordinary row. This arm only ever adds; it never stands in for the tick."""
        self.repo("checkouts/lf")
        rows = self.rows("| x | **Z9-R9** | ✅ | nothing named |\n")
        self.assertEqual(gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")}), set())

    def test_a_range_on_a_named_row_is_spanned_like_any_other(self):
        self.repo("checkouts/lf")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| x | **C1-R1..R3** | ✅ | landed in `{sha}` |\n")
        landed = gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")})
        self.assertEqual(landed, {"C1-R1", "C1-R2", "C1-R3"})

    def test_the_verdict_says_which_arm_satisfied_each_goal(self):
        """An exception nobody can count is one that spreads."""
        results = gate.evaluate(["A1-R1", "A1-R2", "A1-R3"], {"A1-R1"}, {"A1-R1", "A1-R2"},
                                {"A1-R2"})
        by = {r["id"]: r["by"] for r in results}
        self.assertEqual(by, {"A1-R1": "trailer", "A1-R2": "landed", "A1-R3": None})
        self.assertTrue(results[1]["cited"], "a landed goal is cited for the verdict")

    def test_reachable_says_no_for_a_path_that_is_not_a_repository(self):
        self.assertFalse(gate.reachable(pathlib.Path("nowhere"), "HEAD"))


class ByColumnNotByLine(Workspace):
    """A row is done because its status column says so, and for no other reason.

    Both gates used to decide by whether the *line* held the glyph. The tracker's
    preamble records three requirements counted as met that way, and a fourth
    moved the release gate from 69 of 72 to 70 on a row that visibly says `◐` —
    its notes ended "this row is ✅ when they start". Every test here plants that
    exact shape.
    """

    def tracker(self, body, path="checkouts/lf/IMPLEMENTATION-STATUS.md"):
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        return p

    def test_the_glyph_in_a_partial_rows_prose_does_not_mark_it_done(self):
        rows = self.tracker(
            HEADER + "| Stack runs | `F1-R1` | ◐ | Three left; this row is ✅ when they start. |\n")
        self.assertEqual(gate.done_ids(rows), set())

    def test_the_glyph_in_the_status_column_does_mark_it_done(self):
        # The other direction, which matters as much: a gate that counts nothing
        # is as useless as one that counts everything.
        rows = self.tracker(HEADER + "| Stack runs | `F1-R1` | ✅ | All nineteen answer. |\n")
        self.assertEqual(gate.done_ids(rows), {"F1-R1"})

    def test_a_partial_row_beside_a_done_one_is_read_apart_from_it(self):
        rows = self.tracker(
            HEADER
            + "| Catalogue | `F2-R10` | ✅ | Done. |\n"
            + "| Stack runs | `F1-R1` | ◐ | Not yet — see the ✅ row above. |\n")
        self.assertEqual(gate.done_ids(rows), {"F2-R10"})

    def test_the_glyph_in_prose_outside_any_table_marks_nothing(self):
        # A paragraph is not a row, and the preamble of the real tracker is full
        # of sentences naming requirements.
        rows = self.tracker(
            "Never name an unfinished requirement such as `F1-R1` inside a ✅ row.\n")
        self.assertEqual(gate.done_ids(rows), set())

    def test_the_older_three_column_shape_is_still_read(self):
        # Its status column sits where the modern shape keeps requirements, which
        # is exactly why the column is found by name rather than by position.
        rows = self.tracker(
            "| Deliverable | Status | Landing |\n|---|---|---|\n"
            "| Form closure (`B1-R4`, `B1-R5`) | ✅ | #14 |\n")
        self.assertEqual(gate.done_ids(rows), {"B1-R4", "B1-R5"})

    def test_a_second_table_is_read_with_its_own_header(self):
        rows = self.tracker(
            HEADER + "| Stack runs | `F1-R1` | ◐ | y |\n"
            "\nProse between them.\n\n"
            "| Deliverable | Status | Landing |\n|---|---|---|\n"
            "| Retention (`C1-R1`) | ✅ | #21 |\n")
        self.assertEqual(gate.done_ids(rows), {"C1-R1"})

    def test_a_table_with_no_status_column_is_refused_rather_than_skipped(self):
        # A gate that cannot decide must not report success about the rest.
        rows = self.tracker(
            "| Deliverable | Spec | Landing |\n|---|---|---|\n"
            "| Stack runs | `F1-R1` | #76 |\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            gate.done_ids(rows)
        self.assertEqual(exit.exception.code, 2)
        self.assertIn("names no Status column", out.getvalue())

    def test_a_header_with_no_rows_under_it_is_not_refused(self):
        # A table nobody has filled in yet decides nothing and hides nothing.
        rows = self.tracker("| Deliverable | Spec | Landing |\n|---|---|---|\n")
        self.assertEqual(gate.done_ids(rows), set())

    def test_a_row_shorter_than_its_header_promised_is_not_done(self):
        # There is no cell to read a status from, and a row that cannot be read
        # is not a row that says yes.
        rows = self.tracker(HEADER + "| `F1-R1` ✅ |\n")
        self.assertEqual(gate.done_ids(rows), set())

    def test_a_landing_named_on_a_partial_row_carries_nothing(self):
        # The same reading, on the other arm: `landed_ids` shared the flaw.
        self.repo("checkouts/lf")
        sha = subprocess.run(["git", "-C", "checkouts/lf", "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        rows = self.tracker(
            HEADER + f"| Stack runs | `F1-R1` | ◐ | ✅ once done; landed in `{sha}` |\n")
        self.assertEqual(gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")}), set())


class GateTests(Workspace):
    def test_within_cwd_ok_and_escape(self):
        self.assertTrue(str(gate.within_cwd("70-operations")).endswith("70-operations"))
        with self.assertRaises(SystemExit):
            gate.within_cwd("/etc/hosts")

    def test_load_goals_and_empty(self):
        self.manifest("0.1.0")
        self.assertEqual(gate.load_goals(pathlib.Path("70-operations/versions/0.1.0.toml")),
                         ["B1-R4"])
        self.manifest("0.2.0", goals=())
        empty = pathlib.Path("70-operations/versions/0.2.0.toml")
        with self.assertRaises(SystemExit):
            gate.load_goals(empty)

    def test_parse_repos_ok_and_bad(self):
        self.repo("checkouts/lf")
        repos = gate.parse_repos(["lf=checkouts/lf"])
        self.assertIn("lf", repos)
        with self.assertRaises(SystemExit):
            gate.parse_repos(["noequals"])

    def test_a_search_of_nowhere_is_refused_rather_than_answered(self):
        """Naming no repository is a run that cannot look, not a verdict.

        Answered, it comes back as every goal uncited — which is what a version
        nobody has started also looks like, and the tracker renders the two
        identically. So it exits 2 the way a manifest locking no goals does,
        rather than 1.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            gate.parse_repos([])
        self.assertEqual(exit.exception.code, 2)
        self.assertIn("nowhere to read citations from", out.getvalue())

        self.manifest("0.1.0", goals=("B1-R4",))
        code, said = run_main(gate, ["--manifest", "70-operations/versions/0.1.0.toml",
                                     "--status", self.status_file()])
        self.assertEqual(code, 2)
        self.assertNotIn("B1-R4", said)

    def test_cited_and_done_and_evaluate(self):
        self.repo("checkouts/lf")
        cited = gate.cited_ids(gate.parse_repos(["lf=checkouts/lf"]))
        self.assertIn("B1-R4", cited)
        done = gate.done_ids(gate.within_cwd(self.status_file()))
        self.assertIn("C1-R7", done)          # spanned by the range
        results = gate.evaluate(["B1-R4", "Z9-R9"], cited, done)
        self.assertTrue(results[0]["cited"])
        gate.render_human("m.toml", ["lf"], results)   # exercise the renderer

    def test_shallow_clone_is_refused(self):
        self.repo("origin/lf", trailer="Spec: B1-R4")
        subprocess.run(["git", "-C", "origin/lf", "commit", "-q", "--allow-empty",
                        "-m", "feat: later", "-m", "Spec: C1-R3"],
                       check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        f"file://{pathlib.Path('origin/lf').resolve()}", "checkouts/lf"],
                       check=True, capture_output=True)
        repos = gate.parse_repos(["lf=checkouts/lf"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            gate.cited_ids(repos)
        self.assertEqual(exit.exception.code, 2)      # a usage error, not a verdict
        self.assertIn("shallow", out.getvalue())

    def test_main_pass_and_unmet_and_json(self):
        self.repo("checkouts/lf")
        status = self.status_file()
        self.manifest("0.1.0", goals=("B1-R4", "C1-R3"))
        args = ["--manifest", "70-operations/versions/0.1.0.toml",
                "--repo", "lf=checkouts/lf", "--status", status]
        code, out = run_main(gate, args)
        self.assertEqual(code, 0)
        self.assertIn("releasable", out)
        code, out = run_main(gate, [*args, "--format", "json"])
        self.assertEqual(code, 0)
        self.manifest("0.2.0", goals=("Z9-R9",))
        bad = ["--manifest", "70-operations/versions/0.2.0.toml",
               "--repo", "lf=checkouts/lf", "--status", status]
        self.assertEqual(run_main(gate, bad)[0], 1)
        self.assertEqual(run_main(gate, [*bad, "--format", "json"])[0], 1)


class PerRepositoryTrackers(Workspace):
    """Each searched repository's status.toml is a tracker the gate reads — OPS-R74."""

    def tracker(self, path, body):
        p = pathlib.Path(path) / "status.toml"
        p.write_text(body, encoding="utf-8")

    def head_of(self, path):
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def test_a_done_row_in_any_searched_repository_is_done(self):
        self.repo("checkouts/lf", trailer="Spec: B1-R4")
        self.repo("checkouts/web", trailer="Spec: C1-R3")
        self.tracker("checkouts/web", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n'
                     'evidence = ["f"]\n[[requirement]]\nid = "C1-R4"\nstate = "partial"\n')
        self.manifest("0.1.0", goals=("C1-R3", "C1-R4"))
        args = ["--manifest", "70-operations/versions/0.1.0.toml",
                "--repo", "lf=checkouts/lf", "--repo", "web=checkouts/web"]
        code, said = run_main(gate, args)
        self.assertEqual(code, 1)
        self.assertIn("lf: no tracker", said)
        self.assertIn("✓ C1-R3", said)
        self.assertIn("✗ C1-R4", said)

    def test_a_row_naming_its_commit_is_checked_in_its_own_repository(self):
        self.repo("checkouts/lf", trailer="Spec: GOV-R12")
        self.repo("checkouts/web", trailer="Spec: GOV-R13")
        sha = self.head_of("checkouts/web")
        repos = gate.parse_repos(["lf=checkouts/lf", "web=checkouts/web"])
        self.tracker("checkouts/web", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n'
                     f'evidence = ["f"]\nlanded = "{sha}"\n')
        self.tracker("checkouts/lf", '[[requirement]]\nid = "C1-R4"\nstate = "done"\n'
                     f'evidence = ["f"]\nlanded = "{sha}"\n[[requirement]]\nid = "C1-R5"\n'
                     'state = "partial"\nlanded = "{sha}"\n'.replace("{sha}", sha))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            landed = gate.tracked_landed(gate.trackers(repos), repos)
        self.assertEqual(landed, {"C1-R3"})
        self.assertIn("lf records C1-R4 as landed", out.getvalue())

    def test_the_old_milestone_shape_is_left_to_the_markdown_reading(self):
        self.repo("checkouts/lf")
        self.tracker("checkouts/lf", '[[milestone]]\nname = "M1"\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rows = gate.trackers(gate.parse_repos(["lf=checkouts/lf"]))
        self.assertEqual(rows, [])

    def test_a_tracker_that_cannot_be_read_stops_the_gate(self):
        self.repo("checkouts/lf")
        self.tracker("checkouts/lf", '[[requirement]]\nid = "C1-R3"\nstate = "done"\n')
        repos = gate.parse_repos(["lf=checkouts/lf"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            gate.trackers(repos)
        self.assertEqual(exit.exception.code, 2)
        self.assertIn("names no evidence", out.getvalue())


class SetStatusTests(Workspace):
    def test_manifest_for_and_pins_and_with_pins(self):
        self.assertTrue(str(set_status.manifest_for("0.1.0")).endswith("0.1.0.toml"))
        with self.assertRaises(SystemExit):
            set_status.manifest_for("not-semver")
        self.assertEqual(set_status.parse_pins(["a=b"]), ['a = "b"'])
        with self.assertRaises(SystemExit):
            set_status.parse_pins(["noequals"])
        text = 'status  = "staged"\n[pins]\nold = "1"\n'
        self.assertIn("[pins]", set_status.with_pins(text, ['x = "y"']))

    def test_main_status_pins_and_missing(self):
        self.manifest("0.1.0")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--pin", "lemonfiber-media-stack=abc"])
        self.assertEqual(code, 0)
        self.assertIn('status  = "released"', out)
        self.assertIn("[pins]", out)
        self.assertEqual(run_main(set_status, ["--version", "9.9.9",
                                               "--status", "staged"])[0], 1)

    def test_main_malformed_manifest(self):
        pathlib.Path("70-operations/versions/0.5.0.toml").write_text(
            'version = "0.5.0"\nrepos = []\n', encoding="utf-8")   # no status line
        self.assertEqual(run_main(set_status, ["--version", "0.5.0",
                                               "--status", "staged"])[0], 1)

    def test_release_date_is_stamped_above_the_pins(self):
        self.manifest("0.1.0")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-on", "2026-08-22",
                                          "--pin", "media-stack=abc"])
        self.assertEqual(code, 0)
        self.assertIn('released_on = "2026-08-22"', out)
        # Above [pins], or a line-wise reader files the date as a pin.
        self.assertLess(out.index("released_on"), out.index("[pins]"))
        self.assertEqual(tomllib.loads(out)["released_on"], "2026-08-22")

    def test_a_date_already_there_is_replaced_not_repeated(self):
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(
            'version = "0.1.0"\nstatus  = "released"\nreleased_on = "2020-01-01"\n',
            encoding="utf-8")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-on", "2026-08-22"])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("released_on"), 1)
        self.assertEqual(tomllib.loads(out)["released_on"], "2026-08-22")

    def test_a_date_is_refused_when_it_cannot_mean_anything(self):
        self.manifest("0.1.0")
        with self.assertRaises(SystemExit):
            set_status.with_released_on('status  = "released"\n', "22-08-2026")
        # Only a released manifest may carry one.
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "staged",
                                               "--released-on", "2026-08-22"])[0], 1)

    def test_the_tag_a_patch_finished_this_line_under_is_recorded(self):
        """A minor whose release run fails is finished by a patch, and the record
        has to name the artefact people actually installed."""
        self.manifest("0.1.0")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-on", "2026-08-26",
                                          "--released-as", "0.1.1",
                                          "--pin", "media-stack=abc"])
        self.assertEqual(code, 0)
        read = tomllib.loads(out)
        self.assertEqual(read["released_as"], "0.1.1")
        self.assertEqual(read["version"], "0.1.0", "the manifest is still the line's")
        # In the order the events happened, and above [pins] for the same reason
        # the date is: a line-wise reader would otherwise file it as a pin.
        self.assertLess(out.index("released_on"), out.index("released_as"))
        self.assertLess(out.index("released_as"), out.index("[pins]"))

    def test_the_tag_sits_under_status_where_there_is_no_date(self):
        """A manifest being corrected by hand carries no date, and the tag still
        belongs with the status rather than at the end of the goals."""
        self.manifest("0.1.0")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-as", "0.1.2"])
        self.assertEqual(code, 0)
        self.assertLess(out.index("status"), out.index("released_as"))
        self.assertLess(out.index("released_as"), out.index("repos"))

    def test_a_tag_already_there_is_replaced_not_repeated(self):
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(
            'version = "0.1.0"\nstatus  = "released"\nreleased_as = "0.1.1"\n',
            encoding="utf-8")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-as", "0.1.2"])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("released_as"), 1)
        self.assertEqual(tomllib.loads(out)["released_as"], "0.1.2")

    def test_a_tag_is_refused_when_it_cannot_mean_anything(self):
        self.manifest("0.1.0")
        with self.assertRaises(SystemExit):
            set_status.with_released_as('status  = "released"\n', "v0.1.1")
        # Only a released manifest may carry one.
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "staged",
                                               "--released-as", "0.1.1"])[0], 1)
        # And a manifest recording its own tag says so by being that version;
        # asking for it twice means the caller computed the wrong line.
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                               "--released-as", "0.1.0"])[0], 1)


    def test_a_withdrawal_records_why_beneath_what_it_withdrew(self):
        """A yank is the one transition that loses information if recorded bare."""
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(
            'version = "0.1.0"\nstatus  = "released"\nreleased_on = "2026-08-26"\n'
            'released_as = "0.1.1"\nrepos = []\n',
            encoding="utf-8")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "yanked",
                                          "--withdrawn-because", "the installer pinned a bad sha"])
        self.assertEqual(code, 0)
        read = tomllib.loads(out)
        self.assertEqual(read["status"], "yanked")
        self.assertEqual(read["withdrawn_because"], "the installer pinned a bad sha")
        # The release itself is never removed from the record, only marked.
        self.assertEqual(read["released_as"], "0.1.1")
        self.assertEqual(read["released_on"], "2026-08-26")
        # Last of the stamps, so the lines read in the order the events happened.
        self.assertLess(out.index("released_as"), out.index("withdrawn_because"))

    def test_a_withdrawal_falls_back_to_the_lines_a_manifest_actually_has(self):
        """A manifest with no tag stamps under the date; with neither, under status."""
        dated = set_status.with_withdrawn_because(
            'status  = "yanked"\nreleased_on = "2026-08-26"\n', "it broke")
        self.assertLess(dated.index("released_on"), dated.index("withdrawn_because"))
        bare = set_status.with_withdrawn_because('status  = "yanked"\n', "it broke")
        self.assertLess(bare.index("status"), bare.index("withdrawn_because"))

    def test_a_reason_already_there_is_replaced_not_repeated(self):
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(
            'version = "0.1.0"\nstatus  = "yanked"\nwithdrawn_because = "first"\n',
            encoding="utf-8")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "yanked",
                                          "--withdrawn-because", "second"])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("withdrawn_because"), 1)
        self.assertEqual(tomllib.loads(out)["withdrawn_because"], "second")

    def test_a_withdrawal_without_a_reason_is_refused(self):
        self.manifest("0.1.0")
        self.assertEqual(
            run_main(set_status, ["--version", "0.1.0", "--status", "yanked"])[0], 1)
        # And a reason on anything else is a withdrawal nobody made.
        self.assertEqual(
            run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                  "--withdrawn-because", "it broke"])[0], 1)
        # An empty reason is no reason, and a quote would break the line it writes.
        with self.assertRaises(SystemExit):
            set_status.with_withdrawn_because('status  = "yanked"\n', "   ")
        with self.assertRaises(SystemExit):
            set_status.with_withdrawn_because('status  = "yanked"\n', 'it "broke"')


class PrereleaseRecordTests(Workspace):
    """A pre-release is recorded without moving anything — OPS-R60, OPS-R61, OPS-R65."""

    def record(self, version="0.1.0", tag="v0.1.0-pre.1", when="2026-09-15",
               status="staged", unmet=("B1-R4",), pins=()):
        argv = ["--version", version, "--status", status,
                "--prerelease", tag, "--prerelease-on", when]
        for goal in unmet:
            argv += ["--unmet", goal]
        for pin in pins:
            argv += ["--pin", pin]
        return run_main(set_status, argv)

    def test_a_record_is_written_and_the_status_does_not_move(self):
        self.manifest("0.1.0")
        code, out = self.record(pins=["lemonfiber-media-stack=abc"])
        self.assertEqual(code, 0, out)
        read = tomllib.loads(out)
        self.assertEqual(read["status"], "staged")
        self.assertNotIn("released_on", read)
        self.assertEqual(read["prerelease"][0]["tag"], "v0.1.0-pre.1")
        self.assertEqual(read["prerelease"][0]["unmet"], ["B1-R4"])
        self.assertEqual(read["prerelease"][0]["pins"]["lemonfiber-media-stack"], "abc")

    def test_a_second_record_joins_the_first_rather_than_replacing_it(self):
        self.manifest("0.1.0")
        _, first = self.record()
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(first, encoding="utf-8")
        code, out = self.record(tag="v0.1.0-pre.2", unmet=())
        self.assertEqual(code, 0, out)
        self.assertEqual([r["tag"] for r in tomllib.loads(out)["prerelease"]],
                         ["v0.1.0-pre.1", "v0.1.0-pre.2"])

    def test_a_release_written_afterwards_does_not_swallow_the_records(self):
        # `with_pins` rewrites everything from `[pins]` to the end of the file, so a
        # record below it would disappear the moment the version went out — which is
        # exactly when somebody asks what went out before it.
        self.manifest("0.1.0")
        _, staged = self.record()
        pathlib.Path("70-operations/versions/0.1.0.toml").write_text(staged, encoding="utf-8")
        code, out = run_main(set_status, ["--version", "0.1.0", "--status", "released",
                                          "--released-on", "2026-09-20",
                                          "--pin", "lemonfiber-media-stack=999"])
        self.assertEqual(code, 0, out)
        read = tomllib.loads(out)
        self.assertEqual(read["status"], "released")
        self.assertEqual(len(read["prerelease"]), 1)
        self.assertEqual(read["pins"]["lemonfiber-media-stack"], "999")

    def test_a_tag_for_another_version_is_refused(self):
        self.manifest("0.1.0")
        self.assertEqual(self.record(tag="v0.2.0-pre.1")[0], 1)

    def test_the_versions_own_tag_is_not_a_pre_release_tag(self):
        self.manifest("0.1.0")
        self.assertEqual(self.record(tag="v0.1.0")[0], 1)

    def test_rc_is_refused_because_arch_r43_already_uses_it(self):
        self.manifest("0.1.0")
        for reserved in ("v0.1.0-rc.1", "v0.1.0-rc", "v0.1.0-rc2"):
            self.assertEqual(self.record(tag=reserved)[0], 1, reserved)
        # And an identifier that merely starts with those letters is fine.
        self.manifest("0.1.0")
        self.assertEqual(self.record(tag="v0.1.0-arc.1")[0], 0)

    def test_an_identifier_that_is_not_one_is_refused(self):
        self.manifest("0.1.0")
        self.assertEqual(self.record(tag="v0.1.0-pre_1")[0], 1)

    def test_a_manifest_not_in_flight_cannot_carry_one(self):
        self.manifest("0.1.0", status="released")
        self.assertEqual(self.record(status="released")[0], 1)
        self.manifest("0.1.0", status="planned")
        self.assertEqual(self.record(status="planned")[0], 1)

    def test_the_three_halves_of_the_record_are_required_together(self):
        self.manifest("0.1.0")
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "staged",
                                               "--prerelease", "v0.1.0-pre.1"])[0], 1)
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "staged",
                                               "--prerelease-on", "2026-09-15"])[0], 1)
        self.assertEqual(run_main(set_status, ["--version", "0.1.0", "--status", "staged",
                                               "--unmet", "B1-R4"])[0], 1)

    def test_a_date_that_cannot_mean_anything_is_refused(self):
        self.manifest("0.1.0")
        self.assertEqual(self.record(when="15-09-2026")[0], 1)

    def test_a_record_with_no_pins_says_so_rather_than_being_malformed(self):
        self.manifest("0.1.0")
        code, out = self.record(unmet=())
        self.assertEqual(code, 0, out)
        read = tomllib.loads(out)
        self.assertEqual(read["prerelease"][0]["pins"], {})
        self.assertEqual(read["prerelease"][0]["unmet"], [])


class CheckStageableTests(Workspace):
    def test_planned_ok(self):
        # a .md under a .git dir is skipped when scanning for defined ids
        pathlib.Path(".git").mkdir(exist_ok=True)
        pathlib.Path(".git/x.md").write_text("| **Q-R64** | t |\n", encoding="utf-8")
        pathlib.Path("40-quality").mkdir(exist_ok=True)
        pathlib.Path("40-quality/x.md").write_text("| **Q-R64** | text |\n", encoding="utf-8")
        self.manifest("0.2.0", status="planned", goals=("Q-R64",), repos=("lf", "ms"))
        code, out = run_main(check_stageable, ["0.2.0"])
        self.assertEqual(code, 0)
        self.assertIn("lf", out)

    def test_unknown_goal_with_nothing_in_flight(self):
        self.manifest("0.4.0", status="planned", goals=("ZZ9-R9",))
        self.assertNotEqual(run_main(check_stageable, ["0.4.0"])[0], 0)

    def test_not_planned_bad_and_missing(self):
        self.manifest("0.3.0", status="staged")
        self.assertNotEqual(run_main(check_stageable, ["0.3.0"])[0], 0)   # not planned
        self.assertNotEqual(run_main(check_stageable, ["nope"])[0], 0)    # bad version
        self.assertNotEqual(run_main(check_stageable, ["1.2.3"])[0], 0)   # no manifest

    def test_in_flight_blocks(self):
        self.manifest("0.2.0", status="releasable")
        self.manifest("0.3.0", status="planned", goals=("B1-R4",))
        self.assertNotEqual(run_main(check_stageable, ["0.3.0"])[0], 0)

    def test_a_withdrawn_goal_is_refused_by_name(self):
        """A retired row holds a number open; OPS-R30 forbids locking one.

        It is defined — the row is still there, which is the whole point of
        keeping it — so a gate asking only whether the spec defines the
        identifier lets it through, under a docstring naming OPS-R30.
        """
        pathlib.Path("40-quality").mkdir(exist_ok=True)
        pathlib.Path("40-quality/x.md").write_text(
            "| **Q-R64** | text |\n"
            "| **Q-R65** | *Withdrawn — carried to Q-R64. The number is not reused.* |\n",
            encoding="utf-8")
        self.manifest("0.2.0", status="planned", goals=("Q-R64", "Q-R65"), repos=("lf",))
        code, out = run_main(check_stageable, ["0.2.0"])
        self.assertNotEqual(code, 0)
        self.assertIn("Q-R65", out)
        self.assertNotIn("Q-R64", out)

    def test_a_version_locking_no_goal_is_refused_at_staging(self):
        """A manifest with an empty goal list has nothing to prove and nothing to fail.

        The release gate and the no-stub gate both refuse one. Staging did not, so a
        version could join the train and be answered about only at the end of it.
        """
        self.manifest("0.2.0", status="planned", goals=(), repos=("lf",))
        code, out = run_main(check_stageable, ["0.2.0"])
        self.assertNotEqual(code, 0)
        self.assertIn("locks no goal", out)

    def test_every_reason_a_version_is_unstageable_is_reported_at_once(self):
        """Four independent questions, and a manifest can fail several of them.

        Each answer costs a CI round trip, so reporting the first and stopping made
        finding the rest a sequence of pushes.
        """
        self.manifest("0.2.0", status="releasable")
        pathlib.Path("70-operations/versions/0.6.0.toml").write_text(
            'version = "0.6.0"\nstatus  = "draft"\nrepos = []\ngoals = []\n',
            encoding="utf-8")
        code, out = run_main(check_stageable, ["0.6.0"])
        self.assertNotEqual(code, 0)
        self.assertIn("not planned", out)
        self.assertIn("one version at a time", out)
        self.assertIn("locks no goal", out)
        self.assertIn("nowhere for the gate to search", out)

    def test_a_version_with_nowhere_to_search_is_refused_at_staging(self):
        """A manifest that cuts nothing has nowhere for the gate to look either,
        and staging is the last moment anybody reads this file on purpose."""
        pathlib.Path("40-quality").mkdir(exist_ok=True)
        pathlib.Path("40-quality/x.md").write_text("| **Q-R64** | text |\n", encoding="utf-8")
        pathlib.Path("70-operations/versions/0.6.0.toml").write_text(
            'version = "0.6.0"\nstatus  = "planned"\nrepos = []\ngoals = ["Q-R64"]\n',
            encoding="utf-8")
        self.assertNotEqual(run_main(check_stageable, ["0.6.0"])[0], 0)


class WhatTheManifestsSayTheyLock(unittest.TestCase):
    """The goal count a manifest opens with, against the list beneath it.

    Most manifests begin by saying how many goals they lock, and that sentence is
    what somebody reads instead of counting. It is also a number two people touch at
    different times — one appends a goal, the other wrote the sentence — and nothing
    has ever asked whether the two still agree. A count that has stopped being true
    reads exactly like one that is, which is the whole of the failure: there is
    nothing to notice, and `versions/README.md` says as much about a different count
    it deliberately refuses to write down.

    Stating one is not required. A manifest that says nothing claims nothing, and
    several say nothing. What is refused is a count the list under it contradicts.

    The real tree rather than a fixture, because the thing at risk is these files.
    """

    #: The first number the header offers as a count of goals.
    STATED = re.compile(r"(\d+)\s+goals\b")

    def manifests(self):
        found = sorted((HERE.parent / "70-operations" / "versions").glob("*.toml"))
        found = [f for f in found if f.name != "TEMPLATE.toml"]
        self.assertTrue(found, "no manifest was read, so nothing below is a claim")
        return found

    def test_a_stated_count_matches_the_goals_beneath_it(self):
        for manifest in self.manifests():
            text = manifest.read_text(encoding="utf-8")
            # The header only. A count is an opening sentence about the version; a
            # digit further down belongs to a requirement id or a pin.
            said = self.STATED.search(text.split("version =")[0])
            if said is None:
                continue
            with self.subTest(manifest=manifest.name):
                self.assertEqual(
                    int(said.group(1)),
                    len(tomllib.loads(text).get("goals", [])),
                    f"{manifest.name} opens by claiming a number of goals that its own "
                    "`goals` list does not hold",
                )

    def test_at_least_one_manifest_states_a_count(self):
        """So a regex that stopped matching is told apart from a tree with no counts."""
        stating = [
            manifest.name
            for manifest in self.manifests()
            if self.STATED.search(
                manifest.read_text(encoding="utf-8").split("version =")[0]
            )
        ]
        self.assertTrue(
            stating,
            "no manifest header states a goal count, so the check above compared nothing",
        )


class ManifestReposTests(Workspace):
    """What a version cuts and where its goals were satisfied — OPS-R58."""

    def toml(self, name, body):
        pathlib.Path(f"70-operations/versions/{name}.toml").write_text(body, encoding="utf-8")

    def test_a_manifest_that_says_nothing_is_searched_where_it_cuts(self):
        """Every manifest written before this existed says nothing, and searching
        none of them would report every goal unmet for a reason that is not true."""
        data = {"repos": ["lf", "ms"]}
        self.assertEqual(manifest_repos.searched(data), ["lf", "ms"])
        self.assertEqual(manifest_repos.cut(data), ["lf", "ms"])

    def test_where_it_says_the_two_lists_are_different_answers(self):
        data = {"repos": ["lf"], "satisfied_in": ["lf", "web"]}
        self.assertEqual(manifest_repos.cut(data), ["lf"], "naming it does not tag it")
        self.assertEqual(manifest_repos.searched(data), ["lf", "web"])

    def test_an_empty_list_is_not_an_instruction_to_search_nowhere(self):
        data = {"repos": ["lf"], "satisfied_in": []}
        self.assertEqual(manifest_repos.searched(data), ["lf"])

    def test_main_prints_each_list_one_per_line(self):
        self.toml("0.2.0", 'version = "0.2.0"\nrepos = ["lf"]\nsatisfied_in = ["lf", "web"]\n')
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "cut"])
        self.assertEqual((code, out), (0, "lf\n"))
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "searched"])
        self.assertEqual((code, out), (0, "lf\nweb\n"))

    def test_main_refuses_what_it_cannot_answer(self):
        self.assertEqual(run_main(manifest_repos, ["--version", "9.9.9", "--for", "cut"])[0], 1)
        with self.assertRaises(SystemExit):
            manifest_repos.manifest_for("not-semver")
        # A version that cuts nothing is a manifest somebody has not finished,
        # said here rather than left for a `while read` over an empty file.
        self.toml("0.3.0", 'version = "0.3.0"\nrepos = []\n')
        self.assertEqual(run_main(manifest_repos, ["--version", "0.3.0", "--for", "cut"])[0], 1)


class ImageReposTests(Workspace):
    """Which streams a version tags before the core, read from the registry — ADR-0033 §4."""

    def setUp(self):
        super().setUp()
        self.registry = {"repo": [{"name": "lf"}, {"name": "lemonfiber-decline", "service": "decline"},
                                  {"name": "lemonfiber-request-gate", "service": "request-gate"}]}

    def write_registry(self, body):
        pathlib.Path("30-repos").mkdir(exist_ok=True)
        pathlib.Path("30-repos/repos.toml").write_text(body, encoding="utf-8")

    def test_a_repository_the_registry_gives_a_service_is_tagged_first(self):
        data = {"repos": ["lf", "lemonfiber-decline", "ms"]}
        self.assertEqual(manifest_repos.images(data, self.registry),
                         [("lemonfiber-decline", "decline", "ghcr.io/lemonfiber/decline")])
        self.assertEqual(manifest_repos.others(data, self.registry), ["lf", "ms"])

    def test_a_service_the_version_does_not_cut_is_not_tagged(self):
        data = {"repos": ["lf"]}
        self.assertEqual(manifest_repos.images(data, self.registry), [])
        self.assertEqual(manifest_repos.others(data, self.registry), ["lf"])

    def test_a_repository_named_against_its_service_is_refused(self):
        """Skipped, it would be cut with the core in one step."""
        with self.assertRaises(SystemExit) as caught:
            manifest_repos.image_repos({"repo": [{"name": "decline-service", "service": "decline"}]})
        self.assertIn("names it lemonfiber-decline", str(caught.exception))

    def test_a_service_that_is_not_a_service_id_is_refused(self):
        """It becomes part of a reference handed to docker."""
        for service in ("Decline", "--output=x", "a--b", "", "decline/x"):
            with self.assertRaises(SystemExit) as caught:
                manifest_repos.image_repos({"repo": [{"name": f"lemonfiber-{service}",
                                                      "service": service}]})
            self.assertIn("is not a service id", str(caught.exception))

    def test_main_prints_both_halves_of_the_cut(self):
        self.write_registry('[[repo]]\nname = "lf"\n\n'
                            '[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n')
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lf", "lemonfiber-decline"]\n', encoding="utf-8")
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "images"])
        self.assertEqual((code, out), (0, "lemonfiber-decline\tdecline\tghcr.io/lemonfiber/decline\n"))
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "others"])
        self.assertEqual((code, out), (0, "lf\n"))

    def test_an_empty_half_is_an_answer_not_a_refusal(self):
        """Most versions build no image, and the workflow reads an empty list as one step."""
        self.write_registry('[[repo]]\nname = "lf"\n')
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lf"]\n', encoding="utf-8")
        self.assertEqual(run_main(manifest_repos, ["--version", "0.2.0", "--for", "images"]), (0, ""))

    def test_the_registry_this_repository_holds_reads_cleanly(self):
        """Every `service` the real registry gives is one the train can act on."""
        registry = tomllib.loads((HERE.parent / "30-repos/repos.toml").read_text(encoding="utf-8"))
        built = manifest_repos.image_repos(registry)
        self.assertEqual(built, {"lemonfiber-decline": "decline",
                                 "lemonfiber-request-gate": "request-gate"})


class TrainImages(Workspace):
    """A registry building `decline`, a manifest cutting it, and a stubbed registry."""

    DIGEST = "sha256:" + "a" * 64
    OTHER = "sha256:" + "b" * 64

    #: Stands in for `docker buildx imagetools inspect`. Prints DOCKER_REPLY as
    #: the index descriptor, unless the reference is named in DOCKER_MISSING.
    DOCKER = """#!/bin/sh
case " ${DOCKER_MISSING:-} " in *" $4 "*) echo "ERROR: $4: not found" >&2; exit 1 ;; esac
printf '%s' "${DOCKER_REPLY}"
"""

    def setUp(self):
        super().setUp()
        pathlib.Path("30-repos").mkdir()
        pathlib.Path("30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lf"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n',
            encoding="utf-8")
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber-decline", "lf"]\n', encoding="utf-8")
        pathlib.Path("70-operations/versions/0.3.0.toml").write_text(
            'version = "0.3.0"\nrepos = ["lf"]\n', encoding="utf-8")
        bin_dir = pathlib.Path(self.tmp, "bin")
        bin_dir.mkdir()
        (bin_dir / "docker").write_text(self.DOCKER, encoding="utf-8")
        (bin_dir / "docker").chmod(0o755)
        self.saved_env = dict(os.environ)
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        os.environ["DOCKER_REPLY"] = f'{{"mediaType": "index", "digest": "{self.DIGEST}"}}'
        os.environ.pop("GITHUB_OUTPUT", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved_env)
        super().tearDown()


class CheckImagePinsTests(TrainImages):
    """The embedded stack pins each tagged image at its tag and digest — ADR-0033 §4."""

    def stack(self, tag="v0.2.0", digest=TrainImages.DIGEST, image="ghcr.io/lemonfiber/decline"):
        return {"service": [{"id": "sonarr", "image": "lscr.io/linuxserver/sonarr"},
                            {"id": "decline", "image": image, "tag": tag, "digest": digest}]}

    def write_stack(self, tag):
        pathlib.Path("stack.toml").write_text(
            '[[service]]\nid = "decline"\nimage = "ghcr.io/lemonfiber/decline"\n'
            f'tag = "{tag}"\ndigest = "{self.DIGEST}"\n', encoding="utf-8")

    def check(self, tag, version="0.2.0"):
        return run_main(check_image_pins, ["--version", version, "--tag", tag, "--stack", "stack.toml"])

    def test_a_stack_pinning_the_tag_and_its_digest_passes(self):
        self.assertEqual(check_image_pins.problems(self.stack(), "v0.2.0", {"decline": self.DIGEST}), [])

    def test_each_way_a_pin_can_be_wrong_is_named(self):
        said = check_image_pins.problems(
            self.stack(tag="v0.2.0-pre.1", digest=self.OTHER, image="ghcr.io/else/decline"),
            "v0.2.0", {"decline": self.DIGEST})
        self.assertEqual(len(said), 3)
        self.assertIn("image is 'ghcr.io/else/decline'", said[0])
        self.assertIn("not 'v0.2.0'", said[1])
        self.assertIn("ghcr.io/lemonfiber/decline:v0.2.0 published", said[2])

    def test_a_service_declared_other_than_once_is_refused(self):
        self.assertIn("0 times", check_image_pins.problems(
            self.stack(), "v0.2.0", {"request-gate": self.DIGEST})[0])
        twice = self.stack()
        twice["service"].append(dict(twice["service"][1]))
        self.assertIn("2 times", check_image_pins.problems(twice, "v0.2.0", {"decline": self.DIGEST})[0])

    def test_only_a_tag_the_train_cuts_is_one(self):
        for tag in ("v0.2.0", "v0.2.0-pre.1", "v0.2.0-pre.2.a"):
            self.assertTrue(check_image_pins.cut_by_train(tag, "0.2.0"), tag)
        for tag in ("0.2.0", "v0.2", "v0.3.0", "v0.2.0-rc.1", "v0.2.0-", "v0.2.0-pre..1", "v0.2.0 --push"):
            self.assertFalse(check_image_pins.cut_by_train(tag, "0.2.0"), tag)
        self.assertFalse(check_image_pins.cut_by_train("v0.2", "0.2"), "a version is three numbers")

    def test_a_reference_that_is_not_one_never_reaches_docker(self):
        for reference in ("--output=x", "", "ghcr.io/x:v1 --push"):
            self.assertIn("is not a reference", check_image_pins.digest_of(reference)[1])

    def test_a_stack_outside_the_working_directory_is_refused(self):
        code, said = run_main(check_image_pins, ["--version", "0.2.0", "--tag", "v0.2.0",
                                                 "--stack", "/etc/hosts"])
        self.assertEqual(code, 1)
        self.assertIn("path escapes the working directory", said)

    def test_the_registry_is_asked_for_the_index_digest(self):
        self.assertEqual(check_image_pins.digest_of("ghcr.io/lemonfiber/decline:v0.2.0"), (self.DIGEST, ""))

    def test_each_way_the_registry_can_fail_to_answer_is_named(self):
        os.environ["DOCKER_MISSING"] = "ghcr.io/lemonfiber/decline:v0.2.0"
        self.assertIn("is not published (ERROR", check_image_pins.digest_of("ghcr.io/lemonfiber/decline:v0.2.0")[1])
        for reply, said in (("not json", "not a descriptor"), ("[]", "not a descriptor"),
                            ('{"digest": "sha256:short"}', "which is not one")):
            os.environ["DOCKER_REPLY"] = reply
            self.assertIn(said, check_image_pins.digest_of("ghcr.io/lemonfiber/x:v0.2.0")[1])

    def test_main_passes_a_stack_that_pins_the_tag(self):
        self.write_stack("v0.2.0-pre.1")
        code, out = self.check("v0.2.0-pre.1")
        self.assertEqual(code, 0)
        self.assertIn("decline is pinned at v0.2.0-pre.1", out)

    def test_main_refuses_a_stack_still_on_the_pre_release(self):
        """The pre-release's digests are not the release's, so the core waits for the repin."""
        self.write_stack("v0.2.0-pre.1")
        code, out = self.check("v0.2.0")
        self.assertEqual(code, 1)
        self.assertIn("does not pin what v0.2.0 published", out)

    def test_main_refuses_an_image_the_tag_has_not_published(self):
        self.write_stack("v0.2.0")
        os.environ["DOCKER_MISSING"] = "ghcr.io/lemonfiber/decline:v0.2.0"
        code, out = self.check("v0.2.0")
        self.assertEqual(code, 1)
        self.assertIn("ghcr.io/lemonfiber/decline:v0.2.0 is not published", out)

    def test_main_passes_a_version_that_cuts_no_image(self):
        self.assertEqual(self.check("v0.3.0", version="0.3.0"), (0, "0.3.0 cuts no image the stack has to pin.\n"))

    def test_main_refuses_what_it_cannot_read(self):
        self.assertEqual(self.check("v0.2.0")[0], 1, "no stack")
        self.assertEqual(self.check("v0.9.0", version="0.9.0")[0], 1, "no manifest")
        code, said = run_main(check_image_pins, ["--version", "0.2.0", "--tag", "v0.2.0 x", "--stack", "s"])
        self.assertEqual(code, 1)
        self.assertIn("is not a tag the train cuts", said)


class TrainStepTests(TrainImages):
    """Which step a run is on, read from the repositories — ADR-0033 §4."""

    def stream(self, name, tagged=()):
        """A remote for `name`, holding `tagged`, and its clone under checkouts/."""
        self.repo(f"remotes/{name}", trailer="Spec: B1-R4")
        for tag in tagged:
            subprocess.run(["git", "-C", f"remotes/{name}", "-c", "tag.gpgsign=false", "tag", tag],
                           check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", f"remotes/{name}", f"checkouts/{name}"],
                       check=True, capture_output=True)

    def step(self, version="0.2.0", tag="v0.2.0"):
        out = pathlib.Path(self.tmp, "output")
        out.unlink(missing_ok=True)
        os.environ["GITHUB_OUTPUT"] = str(out)
        code, said = run_main(train_step, ["--version", version, "--tag", tag])
        return (code, said, out.read_text(encoding="utf-8") if out.exists() else "",
                pathlib.Path("tagging.txt").read_text(encoding="utf-8") if code == 0 else "",
                pathlib.Path("declaring.txt").read_text(encoding="utf-8") if code == 0 else "")

    def test_an_untagged_image_makes_it_the_first_step(self):
        """The core is not tagged, and still has to declare the version first."""
        self.stream("lemonfiber-decline")
        self.stream("lf")
        code, _, output, tagging, declaring = self.step()
        self.assertEqual((code, output), (0, "step=images\n"))
        self.assertEqual(tagging, "lemonfiber-decline\n")
        self.assertEqual(declaring, "lemonfiber-decline\nlf\n")

    def test_every_image_tagged_makes_it_the_second_step(self):
        """An image already tagged has published, and its main may have moved on."""
        self.stream("lemonfiber-decline", tagged=("v0.2.0",))
        self.stream("lf")
        code, said, output, tagging, declaring = self.step()
        self.assertEqual((code, output), (0, "step=streams\n"))
        self.assertEqual((tagging, declaring), ("lf\n", "lf\n"))
        self.assertIn("tags lf at v0.2.0", said)

    def test_a_pre_release_tag_is_its_own_first_step(self):
        """The image carries the pre-release; the release still has to publish its own."""
        self.stream("lemonfiber-decline", tagged=("v0.2.0-pre.1",))
        self.stream("lf")
        self.assertEqual(self.step()[2], "step=images\n")
        self.assertEqual(self.step(tag="v0.2.0-pre.1")[2], "step=streams\n")

    def test_a_version_cutting_no_image_is_one_step(self):
        self.stream("lf")
        code, _, output, tagging, _ = self.step(version="0.3.0", tag="v0.3.0")
        self.assertEqual((code, output, tagging), (0, "step=streams\n", "lf\n"))

    def test_without_a_runner_output_it_still_says_the_step(self):
        self.stream("lf")
        os.environ.pop("GITHUB_OUTPUT", None)
        code, said = run_main(train_step, ["--version", "0.3.0", "--tag", "v0.3.0"])
        self.assertEqual(code, 0)
        self.assertIn("step=streams", said)

    def test_a_lookup_that_fails_is_a_refusal_not_an_untagged_image(self):
        """Read as untagged, it would publish an image twice under one tag."""
        self.repo("checkouts/lemonfiber-decline")
        with self.assertRaises(SystemExit) as caught:
            train_step.carries("lemonfiber-decline", "v0.2.0")
        self.assertIn("could not ask lemonfiber-decline", str(caught.exception))

    def test_a_lookup_that_is_not_one_never_reaches_git(self):
        for repo, tag in (("--upload-pack=x", "v0.2.0"), ("..", "v0.2.0"), ("lf", "-v0.2.0"),
                          ("lf", "v0.2.0 x")):
            with self.assertRaises(SystemExit) as caught:
                train_step.carries(repo, tag)
            self.assertIn("is not a lookup", str(caught.exception))

    def test_main_refuses_what_it_cannot_settle(self):
        self.assertEqual(self.step(version="0.9.0", tag="v0.9.0")[0], 1)
        self.assertEqual(self.step(tag="v0.2.0-rc.1")[0], 1)


class SubmodulePinsTests(Workspace):
    """Every submodule a tag embeds, named as a manifest pins it — OPS-R35.

    The fixture is `lemonfiber`'s own `.gitmodules` at `v0.10.0`, the release
    whose manifest recorded the stack and said nothing about `assets/web`.
    """

    #: What `v0.10.0` actually declares.
    GITMODULES = (
        '[submodule "assets/media-stack"]\n'
        "\tpath = assets/media-stack\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-media-stack.git\n"
        '[submodule "assets/web"]\n'
        "\tpath = assets/web\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-web.git\n"
    )

    def test_a_tag_with_two_submodules_yields_both(self):
        """The defect: 0.10.0 embeds the stack and the web app, and the manifest
        named only the stack because the workflow named the path it knew."""
        code, out = run_main(submodule_pins, [], stdin=self.GITMODULES)
        self.assertEqual(code, 0)
        self.assertEqual(out, "lemonfiber-media-stack\tassets/media-stack\n"
                              "lemonfiber-web\tassets/web\n")

    def test_a_pin_is_named_for_the_repository_not_the_path(self):
        """`lemonfiber-media-stack`, which is the naming the manifests already
        use — the basename of the url, and the name a reader can look up."""
        for url in ("https://github.com/lemonfiber/lemonfiber-web.git",
                    "https://github.com/lemonfiber/lemonfiber-web/",
                    "git@github.com:lemonfiber/lemonfiber-web.git"):
            self.assertEqual(submodule_pins.named(url), "lemonfiber-web")

    def test_settings_that_are_not_a_submodule_are_passed_over(self):
        declared = submodule_pins.declared(
            "# a comment\n" + self.GITMODULES + "\tbranch = main\n\tshallow = true\n")
        self.assertEqual(declared, [("lemonfiber-media-stack", "assets/media-stack"),
                                    ("lemonfiber-web", "assets/web")])

    def test_a_value_keeps_no_surrounding_whitespace(self):
        """Taken to the end of the line and trimmed here, rather than by a lazy
        pattern closed with a trailing `\\s*$` that backtracks."""
        self.assertEqual(
            submodule_pins.declared('[submodule "assets/web"]\n'
                                    "  path =   assets/web   \n"
                                    "  url = https://github.com/lemonfiber/lemonfiber-web.git  \n"),
            [("lemonfiber-web", "assets/web")])

    def test_a_stanza_missing_half_of_itself_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            submodule_pins.declared('[submodule "assets/web"]\n\tpath = assets/web\n')
        self.assertIn("wants a path and a url", str(caught.exception))

    def test_a_tag_that_declares_nothing_is_refused(self):
        """Recording no pins at all is the failure being fixed, so it is said
        rather than left for a `while read` over an empty file."""
        self.assertEqual(run_main(submodule_pins, [], stdin="")[0], 1)


class TrackerAndPrGoalsTests(Workspace):
    def test_tracker_body(self):
        payload = ('{"version":"0.2.0","releasable":false,"goals":['
                   '{"id":"A2-R1","cited":true,"done":true},'
                   '{"id":"A2-R6","cited":true,"done":false}]}')
        code, out = run_main(tracker_body, [], stdin=payload)
        self.assertEqual(code, 0)
        self.assertIn("## Release 0.2.0 — 1/2 goals", out)
        self.assertIn("- [x] `A2-R1`", out)
        self.assertIn("not yet releasable", out)

    def test_an_unmet_goal_reads_as_unmet_in_both_halves(self):
        """Each half of the line says what is absent, and neither reads as present.

        The tick is the trap. A list of absences whose second item was spelled
        `tracker ✅` renders as `missing citation, tracker ✅`, which is an
        English sentence saying the tracker has ticked it — the opposite of the
        verdict it was rendering, on every goal that has neither.
        """
        payload = ('{"version":"0.3.0","releasable":false,"goals":['
                   '{"id":"A2-R1","cited":false,"done":false},'
                   '{"id":"A2-R2","cited":true,"done":false},'
                   '{"id":"A2-R3","cited":false,"done":true}]}')
        code, out = run_main(tracker_body, [], stdin=payload)
        self.assertEqual(code, 0)
        self.assertIn("- [ ] `A2-R1` — no citation, no tracker tick", out)
        self.assertIn("- [ ] `A2-R2` — no tracker tick", out)
        self.assertIn("- [ ] `A2-R3` — no citation", out)
        # The glyph is what made the old rendering readable as its own opposite,
        # and only a done goal may carry one. Counted first, because a sweep of
        # the unchecked lines proves nothing if the prefix moved and there are
        # none — which is the same silence this whole change is about.
        unchecked = [line for line in out.splitlines() if line.startswith("- [ ]")]
        self.assertEqual(len(unchecked), 3)
        for line in unchecked:
            self.assertNotIn("✅", line)

    def test_every_goal_met_reads_as_releasable(self):
        payload = ('{"version":"0.4.0","releasable":true,"goals":['
                   '{"id":"A2-R1","cited":true,"done":true}]}')
        code, out = run_main(tracker_body, [], stdin=payload)
        self.assertEqual(code, 0)
        self.assertIn("## Release 0.4.0 — 1/1 goals", out)
        self.assertIn("✅ releasable", out)
        self.assertNotIn("- [ ]", out)

    def _pr(self, text):
        pathlib.Path("pr.txt").write_text(text, encoding="utf-8")
        return run_main(pr_goals, ["--pr-text", "pr.txt"])

    def test_the_template_is_not_the_version_in_flight(self):
        """It is a file whose job is to be read as an example.

        Every other manifest walker skips it; these two read it, so a real status
        written into it to document the lifecycle would classify every pull
        request against a manifest with no version and no goals, and refuse every
        staging attempt naming a version that is not one.
        """
        pathlib.Path("70-operations/versions/TEMPLATE.toml").write_text(
            'version = "0.0.0"\nstatus  = "staged"\ngoals = []\n', encoding="utf-8")
        self.assertIsNone(pr_goals.staged_manifest())
        self.manifest("0.2.0", status="planned")
        self.assertIsNone(check_stageable.in_flight("0.2.0.toml"))

    def test_the_version_in_flight_is_the_earliest_by_number(self):
        self.manifest("0.2.0", status="staged")
        self.manifest("0.10.0", status="staged")
        self.assertEqual(pr_goals.staged_manifest()["version"], "0.2.0")

    def test_pr_goals_scopes(self):
        # nothing staged
        _, out = self._pr("Spec: B1-R4\n")
        self.assertIn('"staged": null', out)
        # in-scope
        self.manifest("0.1.0", status="staged", goals=("B1-R4",))
        self.assertIn('"in_scope": ["B1-R4"]', self._pr("Spec: B1-R4\n")[1])
        # advisory (cites something out of scope)
        self.assertIn('"advisory": true', self._pr("Spec: F1-R3\n")[1])
        # helpers directly
        self.assertEqual(pr_goals.staged_manifest()["version"], "0.1.0")
        with self.assertRaises(SystemExit):
            pr_goals.within_cwd("/etc/hosts")


if __name__ == "__main__":
    unittest.main(verbosity=2)
