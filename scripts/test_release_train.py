#!/usr/bin/env python3
"""Coverage tests for the release-train scripts — gate, set_status,
check_stageable, tracker_body, pr_goals.

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

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_stageable  # noqa: E402
import gate  # noqa: E402
import manifest_repos  # noqa: E402
import pr_goals  # noqa: E402
import set_status  # noqa: E402
import tracker_body  # noqa: E402


def run_main(mod, argv, stdin=""):
    """Call a module's main() with argv/stdin patched; return (exit_code, stdout)."""
    out = io.StringIO()
    saved_argv, saved_stdin = sys.argv, sys.stdin
    sys.argv = [mod.__name__, *argv]
    sys.stdin = io.StringIO(stdin)
    code = 0
    try:
        with contextlib.redirect_stdout(out):
            result = mod.main()
        code = result if isinstance(result, int) else 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv, sys.stdin = saved_argv, saved_stdin
    return code, out.getvalue()


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
        p.write_text("| **B1-R4** | x | ✅ |\n| **C1-R1..R12** | x | ✅ |\n"
                     "| **Z9-R9** | x | ☐ |\n", encoding="utf-8")
        return str(p)


class LandedTests(Workspace):
    """A row may name the commit that finished a goal, and it is checked — OPS-R34."""

    def head_of(self, path):
        return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def rows(self, text, path="checkouts/lf/IMPLEMENTATION-STATUS.md"):
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_a_row_naming_a_commit_in_the_history_carries_its_goals(self):
        """The whole point: a goal nothing cites, finished by a commit that is there."""
        self.repo("checkouts/lf", trailer="Spec: B1-R4")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| **Z9-R9** | x | ✅ | landed in `{sha}` |\n")
        landed = gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")})
        self.assertIn("Z9-R9", landed)

    def test_a_row_naming_a_commit_nobody_has_carries_nothing(self):
        """What stops this being a way to tick anything by writing eight characters."""
        self.repo("checkouts/lf")
        rows = self.rows("| **Z9-R9** | x | ✅ | landed in `deadbeefdeadbeef` |\n")
        landed = gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")})
        self.assertEqual(landed, set())

    def test_a_row_that_is_not_done_carries_nothing_however_it_is_written(self):
        self.repo("checkouts/lf")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| **Z9-R9** | x | ☐ | landed in `{sha}` |\n")
        self.assertEqual(gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")}), set())

    def test_a_done_row_with_no_commit_named_carries_nothing_here(self):
        """The ordinary row. This arm only ever adds; it never stands in for the tick."""
        self.repo("checkouts/lf")
        rows = self.rows("| **Z9-R9** | x | ✅ | nothing named |\n")
        self.assertEqual(gate.landed_ids(rows, {"lf": pathlib.Path("checkouts/lf")}), set())

    def test_a_range_on_a_named_row_is_spanned_like_any_other(self):
        self.repo("checkouts/lf")
        sha = self.head_of("checkouts/lf")
        rows = self.rows(f"| **C1-R1..R3** | x | ✅ | landed in `{sha}` |\n")
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
