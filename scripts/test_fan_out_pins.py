#!/usr/bin/env python3
"""Coverage tests for fan_out_pins.py — the bump nothing used to open (OPS-R48).

The property worth more than any single case is the last class here: after the
fan-out has run over a checkout, the gate must pass on it. The two halves read
the same pins through the same reader, and a test that holds them to each other
is what keeps them from drifting into a fan-out that bumps what the gate does not
name, or leaves what it does.

The second thing these are careful about is the answer that looks like good news:
a repository reported as current because the question could not be asked. That is
how nine repositories went red on one afternoon with nothing having said a word
beforehand.

Stdlib unittest, no dependencies (the repo has none).
Run:  python3 scripts/test_fan_out_pins.py
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
import time
import unittest
import unittest.mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import fan_out_pins
import workflow_pins

#: The pin check's limits as `hygiene.yml` declares them, for the tests that do not measure them.
LIMITS = fan_out_pins.Limits(commits=75, days=30)

#: When the tests run, for the age the pin check counts in days.
NOW = int(time.time())

#: `hygiene.yml` as far as the fan-out reads it: the two limits its pin check keeps.
DECLARED = '          STALE_DAYS: "30"\n          STALE_COMMITS: "75"\n'


def a_pin(workflow: str, sha: str, comment: str | None = "# v1.0.1") -> str:
    said = f"    uses: lemonfiber/spec/.github/workflows/{workflow}@{sha}"
    return f"{said} {comment}\n" if comment else f"{said}\n"


class Rewriting(unittest.TestCase):
    """The text a bump leaves behind, with no repository involved."""

    def test_the_revision_and_the_tag_both_move(self):
        said = fan_out_pins.rewritten(
            a_pin("dco.yml", "a" * 40), "dco.yml", "a" * 40, "b" * 40, "v1.0.9"
        )
        self.assertIn("dco.yml@" + "b" * 40, said)
        self.assertIn("# v1.0.9", said)
        self.assertNotIn("v1.0.1", said)

    def test_a_pin_carrying_no_comment_gains_one(self):
        # The comment is what Dependabot compares. A bump that moved the
        # revision and left a bare pin behind would silence the bot that is the
        # other half of keeping these current.
        said = fan_out_pins.rewritten(
            a_pin("dco.yml", "a" * 40, comment=None),
            "dco.yml",
            "a" * 40,
            "b" * 40,
            "v1.0.9",
        )
        self.assertIn("# v1.0.9", said)

    def test_another_workflow_at_the_same_revision_is_left_alone(self):
        # The per-file rule, at the level of one line. Two pins can name the same
        # commit and only one of their files have moved.
        text = a_pin("dco.yml", "a" * 40) + a_pin("hygiene.yml", "a" * 40)
        said = fan_out_pins.rewritten(text, "dco.yml", "a" * 40, "b" * 40, "v1.0.9")
        self.assertIn("dco.yml@" + "b" * 40, said)
        self.assertIn("hygiene.yml@" + "a" * 40, said)

    def test_somebody_elses_action_is_never_touched(self):
        text = "    uses: actions/checkout@" + "a" * 40 + " # v7\n"
        said = fan_out_pins.rewritten(text, "dco.yml", "a" * 40, "b" * 40, "v1.0.9")
        self.assertEqual(said, text)


class ARepositoryAndASpec:
    """A consumer checkout and a spec beside it, holding no tests of its own.

    Split from the tests so a second class can take the same fixture without
    inheriting — and re-running under its own name — the eight that belong to
    the first. A mixin rather than a `TestCase`, because it is not one: a
    `TestCase` carrying no test is a class the runner collects, reports on and
    finds nothing in, and its helpers read as dead to anything looking at this
    class alone.
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.spec = self.root / "spec"
        self.repo = self.root / "repo"
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        self.spec.mkdir()

        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")

        self.first = self.commit("one", "dco.yml")
        # A commit touching a different workflow, so `dco.yml` and `hygiene.yml`
        # are at different distances from HEAD and the per-file rule has
        # something to distinguish.
        self.second = self.commit(DECLARED, "hygiene.yml")
        self.third = self.commit("two", "dco.yml")

        # The number the tests bump to, cut where the tests expect it to point.
        # It used to name nothing: every call passed `v1.0.9` at a repository
        # holding no tag at all, and the script went to `HEAD` without noticing
        # — which is how a bump could carry a number beside a revision that
        # number does not name. A fixture that cannot tell the two apart cannot
        # fail when they differ.
        self.git("tag", "-a", "-m", "v1.0.9", "v1.0.9", self.third)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.spec), *args], check=True, capture_output=True
        )

    def commit(self, said: str, workflow: str) -> str:
        where = self.spec / ".github" / "workflows" / workflow
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(said, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", f"{workflow}: {said}")
        got = subprocess.run(
            ["git", "-C", str(self.spec), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return got.stdout.strip()

    def wrote(self, name: str, text: str) -> pathlib.Path:
        where = self.repo / ".github" / "workflows" / name
        where.write_text(text, encoding="utf-8")
        return where

    def named(self) -> str:
        """The revision `v1.0.9` names — what a bump in these tests writes."""
        return fan_out_pins.commit_named_by(self.spec, "v1.0.9")


class AgainstARepository(ARepositoryAndASpec, unittest.TestCase):
    """The half that needs a real checkout to answer."""

    def test_a_stale_pin_is_brought_forward(self):
        where = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)

        self.assertIsNotNone(moved)
        self.assertEqual(len(moved[0]), 1)
        self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def test_a_pin_whose_own_workflow_has_not_moved_is_left_where_it_is(self):
        # `hygiene.yml` last changed at `self.second` and nothing since has
        # touched it, so a pin there is current however many tags have been cut.
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)

        self.assertEqual(moved[0], [])
        self.assertIn(self.second, where.read_text(encoding="utf-8"))

    def test_one_pin_in_two_files_moves_in_both(self):
        first = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        second = self.wrote("labels.yml", a_pin("dco.yml", self.first))

        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)

        self.assertEqual(len(moved[0]), 2)
        for where in (first, second):
            self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def test_no_spec_checkout_is_could_not_ask_rather_than_nothing_to_do(self):
        self.wrote("ci.yml", a_pin("dco.yml", self.first))
        self.assertIsNone(
            fan_out_pins.bring_forward(
                self.repo, self.root / "absent", "v1.0.9", self.third, LIMITS, NOW
            )
        )

    def test_a_pin_this_checkout_cannot_resolve_is_could_not_ask(self):
        # A commit rewritten away, or a shallow clone that does not reach it.
        # Reported rather than skipped: the repository is not current, and
        # nobody can tell from the outside which of the two it was.
        self.wrote("ci.yml", a_pin("dco.yml", "f" * 40))
        self.assertIsNone(
            fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)
        )

    def test_a_repository_pinning_nothing_of_ours_is_answered_not_refused(self):
        self.wrote("ci.yml", "    uses: actions/checkout@" + "a" * 40 + " # v7\n")
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)
        self.assertEqual(moved[0], [])

    def test_the_same_workflow_called_from_two_jobs_in_one_file_is_one_rewrite(self):
        # The reader lists a file once per occurrence, so this file is named
        # twice for one pin. Both lines move on the first pass; a second pass
        # over the same path would find nothing left to change and report the
        # repository unanswerable, which is a refusal about nothing.
        where = self.wrote(
            "ci.yml", a_pin("dco.yml", self.first) + a_pin("dco.yml", self.first)
        )

        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)

        self.assertIsNotNone(moved, "one file naming a pin twice is not unanswerable")
        self.assertEqual(len(moved[0]), 1)
        self.assertEqual(where.read_text(encoding="utf-8").count(self.named()), 2)

    def test_a_pin_the_reader_names_and_this_cannot_rewrite_is_refused(self):
        # Defensive, and reached only if the two halves stop sharing a reader.
        # It matters because the alternative is a branch pushed as the bump that
        # does not contain the bump.
        # A genuinely stale pin — `dco.yml` has moved since `self.first` — named
        # against a file that does not contain it. Anything the history calls
        # current would be skipped before the rewrite is ever attempted.
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        named = {("dco.yml", self.first): [str(where)]}

        was = fan_out_pins.pins_under
        fan_out_pins.pins_under = lambda _root: named
        self.addCleanup(setattr, fan_out_pins, "pins_under", was)

        self.assertIsNone(
            fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, LIMITS, NOW)
        )


class ThePinCheckLimits(ARepositoryAndASpec, unittest.TestCase):
    """A pin the pin check refuses is brought forward, whatever its own file did."""

    def test_a_pin_more_commits_behind_main_than_the_check_allows_is_brought_forward(self):
        # `hygiene.yml` has not changed since `self.second`, and `main` is one
        # commit past it: over a limit of none, inside a limit of one.
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        tight = fan_out_pins.Limits(commits=0, days=30)
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, tight, NOW)

        self.assertEqual(len(moved[0]), 1)
        self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def test_a_pin_exactly_as_far_behind_as_the_check_allows_is_left(self):
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        edge = fan_out_pins.Limits(commits=1, days=30)
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third, edge, NOW)

        self.assertEqual(moved[0], [])
        self.assertIn(self.second, where.read_text(encoding="utf-8"))

    def test_a_pin_older_than_the_check_allows_is_brought_forward_and_one_a_day_younger_is_left(self):
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        dated = int(self.git_out("show", "-s", "--format=%ct", self.second))

        kept = fan_out_pins.bring_forward(
            self.repo, self.spec, "v1.0.9", self.third, LIMITS, dated + 31 * fan_out_pins.DAY - 1
        )
        self.assertEqual(kept[0], [])

        moved = fan_out_pins.bring_forward(
            self.repo, self.spec, "v1.0.9", self.third, LIMITS, dated + 31 * fan_out_pins.DAY
        )
        self.assertEqual(len(moved[0]), 1)
        self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def git_out(self, *args) -> str:
        return subprocess.run(
            ["git", "-C", str(self.spec), *args], capture_output=True, text=True, check=True
        ).stdout.strip()


class TheLimitsAreReadWhereTheCheckKeepsThem(unittest.TestCase):
    """`hygiene.yml` declares the two limits once each, or the fan-out cannot ask."""

    def setUp(self):
        self.spec = pathlib.Path(tempfile.mkdtemp())
        (self.spec / ".github" / "workflows").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.spec, ignore_errors=True)

    def declared(self, text: str) -> fan_out_pins.Limits | None:
        (self.spec / fan_out_pins.HYGIENE).write_text(text, encoding="utf-8")
        return fan_out_pins.limits_in(self.spec)

    def test_both_limits_are_read(self):
        self.assertEqual(self.declared(DECLARED), fan_out_pins.Limits(commits=75, days=30))

    def test_a_limit_missing_or_declared_twice_is_could_not_ask(self):
        self.assertIsNone(self.declared('          STALE_DAYS: "30"\n'))
        self.assertIsNone(self.declared(DECLARED + '          STALE_DAYS: "31"\n'))

    def test_no_hygiene_workflow_is_could_not_ask(self):
        self.assertIsNone(fan_out_pins.limits_in(self.spec / "absent"))

    def test_the_check_in_this_repository_declares_both(self):
        self.assertEqual(
            fan_out_pins.limits_in(pathlib.Path(__file__).resolve().parent.parent),
            fan_out_pins.Limits(commits=75, days=30),
        )

    def test_a_pin_that_is_not_a_revision_here_cannot_be_measured(self):
        self.assertIsNone(fan_out_pins.refused_by_age(self.spec, "f" * 40, LIMITS, NOW))


class TheTwoHalvesAgree(unittest.TestCase):
    """What the gate refuses, the fan-out fixes — and nothing else."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.spec = self.root / "spec"
        self.repo = self.root / "repo"
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        self.spec.mkdir()

        subprocess.run(
            ["git", "-C", str(self.spec), "init", "-q", "-b", "main"],
            check=True,
            capture_output=True,
        )
        for name, value in (("user.email", "t@example.com"), ("user.name", "T")):
            subprocess.run(
                ["git", "-C", str(self.spec), "config", name, value],
                check=True,
                capture_output=True,
            )

        self.first = self.commit("one", "dco.yml")
        self.settled = self.commit(DECLARED, "hygiene.yml")
        self.latest = self.commit("two", "dco.yml")

        # The number these tests bump to. The fan-out reads the revision from
        # the tag rather than from `HEAD`, so a fixture without one is a
        # fixture the run cannot answer against.
        subprocess.run(
            ["git", "-C", str(self.spec), "tag", "-a", "-m", "v1.0.9", "v1.0.9"],
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def commit(self, said: str, workflow: str) -> str:
        where = self.spec / ".github" / "workflows" / workflow
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(said, encoding="utf-8")
        for args in (["add", "-A"], ["commit", "-qm", workflow]):
            subprocess.run(
                ["git", "-C", str(self.spec), *args], check=True, capture_output=True
            )
        got = subprocess.run(
            ["git", "-C", str(self.spec), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return got.stdout.strip()

    def gate(self) -> int:
        """The gate's own `main`, run over the consumer checkout."""
        was = pathlib.Path.cwd()
        try:
            os.chdir(self.repo)
            with contextlib.redirect_stdout(io.StringIO()):
                return workflow_pins.main()
        finally:
            os.chdir(was)

    def test_the_gate_refuses_before_and_passes_after(self):
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            a_pin("dco.yml", self.first) + a_pin("hygiene.yml", self.settled),
            encoding="utf-8",
        )

        sys.argv = ["workflow_pins.py", str(self.spec)]
        self.assertEqual(self.gate(), 1, "the gate should refuse a stale pin")

        fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.latest, LIMITS, NOW)

        self.assertEqual(self.gate(), 0, "the fan-out should have satisfied it")

    def test_the_whole_run_reports_what_it_moved(self):
        # `main` end to end, which is what the workflow actually calls.
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            a_pin("dco.yml", self.first), encoding="utf-8"
        )
        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v1.0.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 0)

        self.assertIn("brought 1 pin(s) forward", said.getvalue())
        self.assertIn("dco.yml", said.getvalue())

    def test_a_consumer_with_nothing_stale_is_reported_and_not_failed(self):
        # Exit 0, and the commonest outcome by far. A script that failed here
        # would teach its caller to ignore the code that means something broke.
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            a_pin("hygiene.yml", self.settled), encoding="utf-8"
        )
        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v1.0.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 0)

        self.assertIn("every pin holds the newest revision", said.getvalue())

    def test_a_run_that_could_not_ask_says_so_and_fails(self):
        (self.repo / ".github" / "workflows" / "ci.yml").write_text(
            a_pin("dco.yml", self.first), encoding="utf-8"
        )
        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.root / "absent"),
            "--tag",
            "v1.0.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)

        self.assertIn("must not report a repository as current", said.getvalue())

    def test_the_settled_pin_is_still_where_it_was(self):
        # The other direction of the same agreement: a fan-out that satisfied the
        # gate by rewriting everything would pass the test above and be wrong.
        where = self.repo / ".github" / "workflows" / "ci.yml"
        where.write_text(
            a_pin("dco.yml", self.first) + a_pin("hygiene.yml", self.settled),
            encoding="utf-8",
        )

        fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.latest, LIMITS, NOW)

        self.assertIn(self.settled, where.read_text(encoding="utf-8"))


class WhoItVisits(unittest.TestCase):
    """Read off the org's own map, never kept as a second copy of it."""

    def wrote(self, text: str) -> pathlib.Path:
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        where = root / "repos.toml"
        where.write_text(text, encoding="utf-8")
        return where

    def test_this_repository_is_not_one_of_its_own_consumers(self):
        # `spec` calls its reusable workflows with `./` and pins nothing of its
        # own, so visiting it opens an empty pull request on every tag.
        where = self.wrote(
            '[[repo]]\nname = "spec"\n\n[[repo]]\nname = "lemonfiber"\n'
        )
        self.assertEqual(fan_out_pins.consumers(where), ["lemonfiber"])

    def test_the_ungoverned_table_is_visited_after_the_map(self):
        # A plugin repository is outside the map and still pins the shared
        # workflows, so its pins go stale the same way.
        where = self.wrote(
            '[[ungoverned]]\nname = "plugin-plex"\n\n[[repo]]\nname = "lemonfiber"\n'
        )
        self.assertEqual(fan_out_pins.consumers(where), ["lemonfiber", "plugin-plex"])

    def test_the_map_order_is_kept(self):
        # The README's order runs from the specification outward. A fan-out that
        # sorted them would report its work in an order nothing else uses.
        where = self.wrote(
            '[[repo]]\nname = "zulu"\n\n[[repo]]\nname = "alpha"\n'
        )
        self.assertEqual(fan_out_pins.consumers(where), ["zulu", "alpha"])

    def test_the_real_map_is_readable_and_holds_every_repository_but_this_one(self):
        # Against the committed file, because the value of reading the map is
        # that it is the map — a test using only a fixture would pass over a
        # `repos.toml` this could no longer parse.
        registry = pathlib.Path(__file__).parent.parent / fan_out_pins.REGISTRY
        named = fan_out_pins.consumers(registry)

        self.assertGreater(len(named), 1)
        self.assertNotIn("spec", named)
        self.assertIn("lemonfiber", named)


def outputs_in(text: str) -> dict[str, list[str]]:
    """The step outputs a `GITHUB_OUTPUT` file holds, each as its lines."""
    found: dict[str, list[str]] = {}
    lines = iter(text.splitlines())

    for line in lines:
        name, _, ends = line.partition("<<")
        found[name] = list(iter(lines.__next__, ends))

    return found


class WhatTheAppCanReach(unittest.TestCase):
    """Which consumers the write token is minted for, and which are named and left."""

    MAP = '[[repo]]\nname = "spec"\n\n[[repo]]\nname = "zulu"\n\n[[repo]]\nname = "unmade"\n\n[[repo]]\nname = "alpha"\n'

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.registry = self.root / "repos.toml"
        self.registry.write_text(self.MAP, encoding="utf-8")
        self.output = self.root / "output"
        self.summary = self.root / "summary.md"
        self.output.touch()
        self.summary.touch()

        env = {"GITHUB_OUTPUT": str(self.output), "GITHUB_STEP_SUMMARY": str(self.summary)}
        patched = unittest.mock.patch.dict(os.environ, env)
        patched.start()
        self.addCleanup(patched.stop)

    def installed(self, *names: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()) as said:
            answered = fan_out_pins.reach("".join(f"{one}\n" for one in names), self.registry)
        self.said = said.getvalue()
        return answered

    def test_the_split_keeps_the_map_order(self):
        reachable, skipped = fan_out_pins.within_reach(["zulu", "unmade", "alpha", "gone"], {"alpha", "zulu"})
        self.assertEqual(reachable, ["zulu", "alpha"])
        self.assertEqual(skipped, ["unmade", "gone"])

    def test_the_token_is_minted_for_the_reachable_ones_only(self):
        # `unmade` is declared on the map and absent from the installation. Minted
        # for it, the token is refused for every repository, not just that one.
        self.assertEqual(self.installed("alpha", "zulu", "spec", "somebody-elses"), 0)

        written = outputs_in(self.output.read_text(encoding="utf-8"))
        self.assertEqual(written, {fan_out_pins.REACHABLE: ["zulu", "alpha"]})

    def test_a_skipped_repository_is_a_warning_naming_it(self):
        self.installed("alpha", "zulu")

        self.assertIn("::warning::unmade is on the map and not in the app's installation", self.said)
        self.assertNotIn("::warning::alpha", self.said)
        self.assertIn("3 repositories on the map, 2 within the app's reach", self.said)

    def test_a_skipped_repository_is_named_in_the_summary(self):
        self.installed("alpha", "zulu")

        said = self.summary.read_text(encoding="utf-8")
        self.assertIn("- unmade\n", said)
        self.assertNotIn("- alpha", said)

    def test_nothing_skipped_writes_no_summary(self):
        self.assertEqual(self.installed("alpha", "zulu", "unmade"), 0)

        self.assertEqual(self.summary.read_text(encoding="utf-8"), "")
        self.assertNotIn("::warning::", self.said)

    def test_blank_lines_in_the_listing_are_not_repositories(self):
        self.installed("", "alpha", "  ", "zulu")

        written = outputs_in(self.output.read_text(encoding="utf-8"))
        self.assertEqual(written[fan_out_pins.REACHABLE], ["zulu", "alpha"])

    def test_an_installation_listing_nothing_is_could_not_ask(self):
        self.assertEqual(self.installed(), 2)

        self.assertIn("listed no repositories", self.said)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")

    def test_a_listing_of_blank_lines_is_a_listing_of_nothing(self):
        self.assertEqual(self.installed("", "  "), 2)

        self.assertIn("listed no repositories", self.said)

    def test_a_map_the_app_reaches_none_of_mints_nothing(self):
        # An empty `repositories` input mints for the whole installation, which is
        # the widest token this workflow could hold. No output is written, so the
        # write mint never has an empty list to be given.
        self.assertEqual(self.installed("somebody-elses"), 2)

        self.assertIn("none of the 3 repositories on the map", self.said)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")

    def test_run_by_hand_it_refuses_rather_than_writing_nowhere(self):
        del os.environ["GITHUB_OUTPUT"]

        self.assertEqual(self.installed("alpha"), 2)
        self.assertIn("run by the workflow", self.said)

    def test_the_real_map_answers_through_the_command_line(self):
        was = pathlib.Path.cwd()
        os.chdir(pathlib.Path(__file__).parent.parent)
        self.addCleanup(os.chdir, was)
        sys.argv = ["fan_out_pins.py", "--reach"]
        with (
            unittest.mock.patch("sys.stdin", io.StringIO("lemonfiber\n")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(fan_out_pins.main(), 0)

        written = outputs_in(self.output.read_text(encoding="utf-8"))
        self.assertEqual(written[fan_out_pins.REACHABLE], ["lemonfiber"])


class TheRevisionItWrites(ARepositoryAndASpec, unittest.TestCase):
    """Which commit ends up beside the number, when the two could differ.

    The fixture's tag is cut at `self.third` and every test here moves `main`
    past it, which is the state the fan-out's own dispatch input exists for:
    bringing consumers up to a number published before today.
    """

    def test_the_pin_follows_the_tag_and_not_the_branch(self):
        # The regression. The revision used to come from `head_of(spec)`, which
        # agrees with the tag only when the fan-out fires the instant the tag is
        # cut. A dispatch naming an earlier number wrote whatever `main` had
        # reached, beside a comment naming the number — a pin that is wrong in
        # the one way `workflow-pins` cannot see, because the file it compares
        # is the same file either way.
        moved_on = self.commit("three", "dco.yml")
        where = self.wrote("ci.yml", a_pin("dco.yml", self.first))

        moved = fan_out_pins.bring_forward(
            self.repo, self.spec, "v1.0.9", self.named(), LIMITS, NOW
        )
        said = where.read_text(encoding="utf-8")

        self.assertIsNotNone(moved)
        self.assertEqual(self.named(), self.third)
        self.assertIn(self.third, said)
        self.assertNotIn(moved_on, said)

    def test_a_number_this_checkout_does_not_hold_is_refused(self):
        # A clone that fetched no tags answers every `rev-parse` the same way an
        # unpublished number does, and both must stop the run. Writing a pin
        # from a revision nobody can name is the failure this refuses.
        self.commit("three", "dco.yml")
        self.wrote("ci.yml", a_pin("dco.yml", self.first))

        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v9.9.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)

        self.assertIn("is not a tag in", said.getvalue())

    def test_a_pin_the_checkout_cannot_resolve_is_reported_by_the_run(self):
        # The tag is here and the checkout is here, so neither refusal above
        # fires — what cannot be answered is how far behind this pin is. It has
        # its own sentence because it has its own cure, and it reaches `main`
        # only through `bring_forward` coming back empty-handed.
        self.wrote("ci.yml", a_pin("dco.yml", "f" * 40))

        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v1.0.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)

        self.assertIn("could not read the pins", said.getvalue())
        self.assertIn("must not report a repository as current", said.getvalue())

    def test_a_spec_whose_pin_check_declares_no_limits_is_reported_by_the_run(self):
        where = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        (self.spec / fan_out_pins.HYGIENE).write_text("one", encoding="utf-8")

        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v1.0.9",
        ]
        with unittest.mock.patch.object(fan_out_pins, "ROOT", self.spec), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)

        self.assertIn("does not declare STALE_COMMITS and STALE_DAYS", said.getvalue())
        self.assertIn(self.first, where.read_text(encoding="utf-8"))

    def test_the_limits_are_this_checkout_s_wherever_the_spec_path_leads(self):
        where = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        (self.spec / fan_out_pins.HYGIENE).write_text("one", encoding="utf-8")
        self.assertFalse(self.spec.resolve().is_relative_to(fan_out_pins.ROOT))

        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v1.0.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 0)

        self.assertNotIn("does not declare", said.getvalue())
        self.assertIn(self.third, where.read_text(encoding="utf-8"))

    def test_an_unpublished_number_writes_nothing(self):
        # Refused *before* anything is rewritten, not after. A run that edited
        # the checkout and then failed would leave a branch half-bumped for
        # whoever looked next.
        self.commit("three", "dco.yml")
        where = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        before = where.read_text(encoding="utf-8")

        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            str(self.repo),
            "--spec",
            str(self.spec),
            "--tag",
            "v9.9.9",
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            fan_out_pins.main()

        self.assertEqual(where.read_text(encoding="utf-8"), before)


class TheTagItWrites(unittest.TestCase):
    """What may be written into fourteen repositories as a version."""

    def test_something_that_is_not_a_version_is_refused(self):
        sys.argv = [
            "fan_out_pins.py",
            "--repo",
            ".",
            "--spec",
            ".",
            "--tag",
            "main",
        ]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)
        self.assertIn("is not a pin tag", said.getvalue())

    def test_naming_no_checkout_says_what_is_missing_rather_than_traceback(self):
        sys.argv = ["fan_out_pins.py", "--tag", "v1.0.9"]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 2)
        self.assertIn("all required", said.getvalue())

    def test_asking_who_it_visits_prints_them_and_stops(self):
        was = pathlib.Path.cwd()
        os.chdir(pathlib.Path(__file__).parent.parent)
        self.addCleanup(os.chdir, was)

        sys.argv = ["fan_out_pins.py", "--consumers"]
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(fan_out_pins.main(), 0)

        self.assertIn("lemonfiber", said.getvalue())
        self.assertNotIn("\nspec\n", "\n" + said.getvalue())

    def test_a_published_series_number_is_accepted(self):
        self.assertTrue(fan_out_pins.TAG.match("v1.0.9"))
        self.assertTrue(fan_out_pins.TAG.match("v1.0.10"))
        self.assertFalse(fan_out_pins.TAG.match("v1.0"))
        self.assertFalse(fan_out_pins.TAG.match("1.0.9"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
