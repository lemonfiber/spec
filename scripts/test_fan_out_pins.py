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
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import fan_out_pins
import workflow_pins


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
        self.second = self.commit("one", "hygiene.yml")
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
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)

        self.assertIsNotNone(moved)
        self.assertEqual(len(moved[0]), 1)
        self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def test_a_pin_whose_own_workflow_has_not_moved_is_left_where_it_is(self):
        # `hygiene.yml` last changed at `self.second` and nothing since has
        # touched it, so a pin there is current however many tags have been cut.
        where = self.wrote("ci.yml", a_pin("hygiene.yml", self.second))
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)

        self.assertEqual(moved[0], [])
        self.assertIn(self.second, where.read_text(encoding="utf-8"))

    def test_one_pin_in_two_files_moves_in_both(self):
        first = self.wrote("ci.yml", a_pin("dco.yml", self.first))
        second = self.wrote("labels.yml", a_pin("dco.yml", self.first))

        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)

        self.assertEqual(len(moved[0]), 2)
        for where in (first, second):
            self.assertIn(self.named(), where.read_text(encoding="utf-8"))

    def test_no_spec_checkout_is_could_not_ask_rather_than_nothing_to_do(self):
        self.wrote("ci.yml", a_pin("dco.yml", self.first))
        self.assertIsNone(
            fan_out_pins.bring_forward(
                self.repo, self.root / "absent", "v1.0.9", self.third
            )
        )

    def test_a_pin_this_checkout_cannot_resolve_is_could_not_ask(self):
        # A commit rewritten away, or a shallow clone that does not reach it.
        # Reported rather than skipped: the repository is not current, and
        # nobody can tell from the outside which of the two it was.
        self.wrote("ci.yml", a_pin("dco.yml", "f" * 40))
        self.assertIsNone(
            fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)
        )

    def test_a_repository_pinning_nothing_of_ours_is_answered_not_refused(self):
        self.wrote("ci.yml", "    uses: actions/checkout@" + "a" * 40 + " # v7\n")
        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)
        self.assertEqual(moved[0], [])

    def test_the_same_workflow_called_from_two_jobs_in_one_file_is_one_rewrite(self):
        # The reader lists a file once per occurrence, so this file is named
        # twice for one pin. Both lines move on the first pass; a second pass
        # over the same path would find nothing left to change and report the
        # repository unanswerable, which is a refusal about nothing.
        where = self.wrote(
            "ci.yml", a_pin("dco.yml", self.first) + a_pin("dco.yml", self.first)
        )

        moved = fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)

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
            fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.third)
        )


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
        self.settled = self.commit("one", "hygiene.yml")
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

        fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.latest)

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

        fan_out_pins.bring_forward(self.repo, self.spec, "v1.0.9", self.latest)

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

    def test_the_ungoverned_table_is_not_visited(self):
        where = self.wrote(
            '[[repo]]\nname = "lemonfiber"\n\n[[ungoverned]]\nname = "something-else"\n'
        )
        self.assertEqual(fan_out_pins.consumers(where), ["lemonfiber"])

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
            self.repo, self.spec, "v1.0.9", self.named()
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
