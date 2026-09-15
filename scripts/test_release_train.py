#!/usr/bin/env python3
"""Coverage tests for the release-train scripts — gate, set_status,
check_stageable, tracker_body, pr_goals, submodule_pins.

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
import check_stageable  # noqa: E402
import gate  # noqa: E402
import manifest_repos  # noqa: E402
import pr_goals  # noqa: E402
import set_status  # noqa: E402
import submodule_pins  # noqa: E402
import tracker_body  # noqa: E402


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

    def test_a_version_with_nowhere_to_search_is_refused_at_staging(self):
        """A manifest that cuts nothing has nowhere for the gate to look either,
        and staging is the last moment anybody reads this file on purpose."""
        pathlib.Path("40-quality").mkdir(exist_ok=True)
        pathlib.Path("40-quality/x.md").write_text("| **Q-R64** | text |\n", encoding="utf-8")
        pathlib.Path("70-operations/versions/0.6.0.toml").write_text(
            'version = "0.6.0"\nstatus  = "planned"\nrepos = []\ngoals = ["Q-R64"]\n',
            encoding="utf-8")
        self.assertNotEqual(run_main(check_stageable, ["0.6.0"])[0], 0)


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
        self.assertIn("- [x] `A2-R1`", out)
        self.assertIn("missing", out)

    def _pr(self, text):
        pathlib.Path("pr.txt").write_text(text, encoding="utf-8")
        return run_main(pr_goals, ["--pr-text", "pr.txt"])

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
