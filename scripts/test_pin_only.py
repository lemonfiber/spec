#!/usr/bin/env python3
"""What `pin_only.py` lets through, and what it refuses — Q-R83.

A pull request is driven against a stand-in forge holding its files at the
merge base and at its head, and spec's history as the compare API reports it.

Stdlib unittest plus PyYAML, for the workflow's own shape.
Run:  python3 scripts/test_pin_only.py
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pin_only

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "pin-only.yml"
REPO = "lemonfiber/core"
OLD, NEW, OFF = "a" * 40, "b" * 40, "c" * 40
BASE, HEAD, MERGE_BASE = "1" * 40, "2" * 40, "3" * 40

CALLER = """name: ci
on: [pull_request]
jobs:
  gates:
    uses: lemonfiber/spec/.github/workflows/gates.yml@{gates} # v1.0.{version}
  pins:
    uses: lemonfiber/spec/.github/workflows/workflow-pins.yml@{pins}
"""


def caller(gates=OLD, pins=OLD, version="57") -> str:
    return CALLER.format(gates=gates, pins=pins, version=version)


def blob(text: str) -> str:
    """A stand-in object id for a file's text."""
    return format(abs(hash(text)) % (16 ** 40), "040x")


class Forge:
    """The REST API for one pull request: git's trees at the merge base and the
    head, and spec's history as the compare API reports it."""

    def __init__(self, files: dict[str, tuple[str | None, str | None]], history=None, modes=None):
        # path under .github -> (text at the merge base, text at the head); None where absent
        self.files = files
        self.modes = modes or {}
        # (base, head) -> status; NEW is ahead of OLD and on main, OFF is not on main
        self.history = history or {(OLD, NEW): "ahead", (NEW, "main"): "identical",
                                   (OLD, OFF): "ahead", (OFF, "main"): "diverged",
                                   (NEW, OLD): "behind", (OLD, "main"): "ahead"}
        self.truncated: set[str] = set()
        # The head each read of the pull request answers with, in turn; the last repeats.
        self.heads = [HEAD]
        self.blobs: dict[str, str] = {}
        self.asked: list[list[str]] = []

    def tree(self, at: int) -> list[dict]:
        entries = []
        for path, texts in self.files.items():
            text = texts[at]
            if text is None:
                continue
            self.blobs[blob(text)] = text
            mode = self.modes.get((path, at), "100644")
            entries.append({"path": path, "mode": mode, "sha": blob(text),
                            "type": "commit" if mode == "160000" else "blob"})
        return entries

    def __call__(self, args: list[str], raw: bool):
        self.asked.append(args)
        path = args[0]
        if path == f"repos/{REPO}/pulls/7":
            head = self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]
            return {"head": {"sha": head}, "base": {"sha": BASE}}
        if path == f"repos/{REPO}/compare/{BASE}...{HEAD}":
            return {"merge_base_commit": {"sha": MERGE_BASE}}
        for at, commit in ((0, MERGE_BASE), (1, HEAD)):
            if path == f"repos/{REPO}/git/trees/{commit}":
                return {"tree": [{"path": "src", "type": "tree", "mode": "040000", "sha": "f" * 40},
                                 {"path": ".github", "type": "tree", "mode": "040000", "sha": f"{at}" * 40}],
                        "truncated": f"root{at}" in self.truncated}
            if path == f"repos/{REPO}/git/trees/{str(at) * 40}?recursive=1":
                inside = [dict(e, path=e["path"].removeprefix(".github/")) for e in self.tree(at)
                          if e["path"].startswith(".github/")]
                inside.append({"path": "workflows", "type": "tree", "mode": "040000", "sha": "e" * 40})
                return {"tree": inside, "truncated": f"github{at}" in self.truncated}
        if path.startswith(f"repos/{REPO}/git/blobs/"):
            assert raw
            return self.blobs[path.rsplit("/", 1)[1]]
        if path.startswith("repos/lemonfiber/spec/compare/"):
            old, new = path.removeprefix("repos/lemonfiber/spec/compare/").split("...")
            return {"status": self.history[(old, new)]}
        raise AssertionError(f"unexpected call {args}")


def run(forge, head: str = HEAD) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pin_only.main(["--repo", REPO, "--number", "7", "--head", head], api=forge)
    return code, out.getvalue()


CI = ".github/workflows/ci.yml"


class Passes(unittest.TestCase):
    def test_no_workflow_changed(self):
        code, said = run(Forge({CI: (caller(), caller()), ".github/dependabot.yml": ("a: 1\n", "a: 2\n")}))
        self.assertEqual(code, 0, said)
        self.assertIn("No workflow or action changes.", said)

    def test_spec_pins_moved_forward_with_their_version(self):
        forge = Forge({CI: (caller(), caller(gates=NEW, pins=NEW, version="58"))})
        code, said = run(forge)
        self.assertEqual(code, 0, said)
        self.assertIn("1 workflow file(s) change only spec's pins", said)

    def test_judged_against_the_merge_base_from_git_s_trees(self):
        forge = Forge({CI: (caller(), caller(gates=NEW))})
        run(forge)
        trees = [a[0] for a in forge.asked if "/git/trees/" in a[0] and "recursive" not in a[0]]
        self.assertEqual(trees, [f"repos/{REPO}/git/trees/{MERGE_BASE}", f"repos/{REPO}/git/trees/{HEAD}"])
        self.assertFalse([a for a in forge.asked if "/files" in a[0] or "/contents/" in a[0]])

    def test_a_repository_with_no_github_directory(self):
        forge = Forge({})
        original = forge.__call__

        def bare(args, raw):
            answer = original(args, raw)
            if "/git/trees/" in args[0] and "recursive" not in args[0]:
                answer["tree"] = answer["tree"][:1]
            return answer

        code, said = run(bare)
        self.assertEqual(code, 0, said)


class Refuses(unittest.TestCase):
    def refused(self, forge, *words: str) -> None:
        code, said = run(forge)
        self.assertEqual(code, 1, said)
        for word in words:
            self.assertIn(word, said)
        self.assertIn("merged by a maintainer", said)

    def test_any_other_change_to_a_workflow(self):
        self.refused(Forge({CI: (caller(), caller() + "  extra:\n    runs-on: x\n")}),
                     f"::error::{CI} changes more than spec's pins")

    def test_a_pin_pointed_at_another_workflow(self):
        after = caller().replace("workflow-pins.yml", "gates.yml")
        self.refused(Forge({CI: (caller(), after)}), "changes more than spec's pins")

    def test_a_pin_taken_away_or_added(self):
        after = caller().replace(f"workflow-pins.yml@{OLD}", "workflow-pins.yml")
        self.refused(Forge({CI: (caller(), after)}), "changes more than spec's pins")

    def test_a_pin_moved_to_another_repository(self):
        after = caller().replace("lemonfiber/spec/.github/workflows/gates.yml", "someone/spec/.github/workflows/gates.yml")
        self.refused(Forge({CI: (caller(), after)}), "changes more than spec's pins")

    def test_a_pin_moved_backward(self):
        self.refused(Forge({CI: (caller(gates=NEW), caller())}),
                     f"moves lemonfiber/spec/.github/workflows/gates.yml: {OLD[:8]} is not ahead of {NEW[:8]} (behind)")

    def test_a_pin_moved_off_main(self):
        self.refused(Forge({CI: (caller(), caller(gates=OFF))}),
                     f"{OFF[:8]} is not on lemonfiber/spec main (diverged)")

    def test_a_workflow_added_or_removed(self):
        self.refused(Forge({".github/workflows/new.yml": (None, "on: push\n")}), ".github/workflows/new.yml is added")
        self.refused(Forge({".github/workflows/old.yml": ("on: push\n", None)}), ".github/workflows/old.yml is removed")

    def test_a_workflow_renamed_is_one_removed_and_one_added(self):
        self.refused(Forge({CI: (caller(), None), ".github/workflows/elsewhere.yml": (None, caller())}),
                     f"{CI} is removed", ".github/workflows/elsewhere.yml is added")

    def test_an_action_changed(self):
        self.refused(Forge({".github/actions/setup/action.yml": ("a: 1\n", "a: 2\n")}),
                     ".github/actions/setup/action.yml changes more than spec's pins")

    def test_a_file_turned_into_a_link_or_a_submodule(self):
        for mode in ("120000", "160000"):
            with self.subTest(mode):
                forge = Forge({CI: (caller(), "elsewhere.yml")}, modes={(CI, 1): mode})
                self.refused(forge, f"{CI} changes its mode from 100644 to {mode}")

    def test_a_script_made_executable(self):
        script = ".github/actions/setup/run.sh"
        forge = Forge({script: ("echo hi\n", "echo hi\n")}, modes={(script, 1): "100755"})
        self.refused(forge, f"{script} changes its mode from 100644 to 100755")

    def test_a_link_changed_where_it_points(self):
        forge = Forge({CI: ("a.yml", "b.yml")}, modes={(CI, 0): "120000", (CI, 1): "120000"})
        self.refused(forge, f"{CI} changes its mode from 120000 to 120000")

    def test_the_directory_itself_replaced_by_a_link(self):
        self.refused(Forge({".github/workflows": (None, "../elsewhere")}, modes={(".github/workflows", 1): "120000"}),
                     ".github/workflows is added")

    def test_every_problem_is_named(self):
        forge = Forge({CI: (caller(), caller(gates=OFF)),
                       ".github/workflows/b.yml": (None, "x\n"),
                       ".github/workflows/c.yml": ("x\n", "y\n")})
        code, said = run(forge)
        self.assertEqual(code, 1)
        self.assertEqual(said.count("::error::"), 3, said)


class Truncated(unittest.TestCase):
    """A tree the forge answers only in part is refused, never read as the whole."""

    def test_a_truncated_tree_at_either_commit(self):
        for which in ("root0", "root1", "github0", "github1"):
            with self.subTest(which):
                forge = Forge({CI: (caller(), caller(gates=NEW))})
                forge.truncated.add(which)
                code, said = run(forge)
                self.assertEqual(code, 2, said)
                self.assertIn("came back truncated", said)

    def test_a_change_past_any_file_list_cap_is_still_seen(self):
        # The pull request's file list stops at 3,000; git's trees do not.
        files = {f"src/{n}.rs": ("a", "b") for n in range(3500)}
        files[".github/workflows/z.yml"] = ("on: push\n", "on: [push, pull_request]\n")
        code, said = run(Forge(files))
        self.assertEqual(code, 1, said)
        self.assertIn(".github/workflows/z.yml changes more than spec's pins", said)

    def test_a_github_directory_that_is_a_file(self):
        forge = Forge({})
        original = forge.__call__

        def flat(args, raw):
            answer = original(args, raw)
            if args[0].endswith(f"/git/trees/{HEAD}"):
                answer["tree"][1] = {"path": ".github", "type": "blob", "mode": "120000", "sha": "9" * 40}
            return answer

        code, said = run(flat)
        self.assertEqual(code, 1, said)
        self.assertIn(".github is added", said)


SPEC_GATES = "lemonfiber/spec/.github/workflows/gates.yml"


def steps(*step_lines: str) -> str:
    """A workflow with one job whose steps are the lines given."""
    return "on: [pull_request]\njobs:\n  one:\n    runs-on: ubuntu-latest\n    steps:\n" + "".join(step_lines)


class Shapes(unittest.TestCase):
    """Each way YAML can make the text judged differ from what Actions runs."""

    def judged(self, before: str, after: str) -> tuple[int, str]:
        return run(Forge({CI: (before, after)}))

    def refused(self, before: str, after: str, *words: str) -> None:
        code, said = self.judged(before, after)
        self.assertEqual(code, 1, said)
        for word in words:
            self.assertIn(word, said)

    def test_a_pin_inside_a_block_scalar(self):
        script = "      - run: |\n          echo uses: {pin}@{sha}\n"
        self.refused(steps(script.format(pin=SPEC_GATES, sha=OLD)), steps(script.format(pin=SPEC_GATES, sha=NEW)),
                     "at jobs.one.steps.0.run")

    def test_a_step_written_as_a_flow_mapping_is_a_step(self):
        step = "      - {{uses: {pin}@{sha}}}\n"
        code, said = self.judged(steps(step.format(pin=SPEC_GATES, sha=OLD)), steps(step.format(pin=SPEC_GATES, sha=NEW)))
        self.assertEqual(code, 0, said)
        self.refused(steps(step.format(pin=SPEC_GATES, sha=OLD)), steps(step.format(pin=SPEC_GATES, sha=OFF)),
                     "is not on lemonfiber/spec main")

    def test_an_anchor_and_an_alias(self):
        text = "x: &p {pin}@{sha}\n" + steps("      - uses: *p\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW),
                     "two readers could take differently", "the anchor &p")

    def test_an_alias_elsewhere_in_the_file(self):
        text = "x: &p 1\ny: *p\n" + steps("      - uses: {pin}@{sha}\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "two readers")

    def test_an_alias_naming_no_anchor(self):
        with self.assertRaisesRegex(pin_only.Unsafe, "an alias"):
            pin_only.strict("a: *p\n")

    def test_a_merge_key(self):
        text = steps("      - <<: {{uses: {pin}@{sha}}}\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "a merge key")

    def test_an_explicit_tag(self):
        text = steps("      - uses: !!str {pin}@{sha}\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "the tag")

    def test_a_key_given_twice(self):
        text = steps("      - uses: {pin}@{sha}\n        uses: {pin}@" + OLD + "\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "the key 'uses' twice")

    def test_a_quoted_key_that_is_not_uses(self):
        text = steps('      - "uses ": {pin}@{sha}\n        run: x\n')
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "at jobs.one.steps.0.uses ")

    def test_an_escaped_key_that_is_uses_is_read_as_uses(self):
        text = steps('      - "use\\x73": {pin}@{sha}\n')
        code, said = self.judged(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW))
        self.assertEqual(code, 0, said)

    def test_a_pin_in_a_comment(self):
        text = steps("      # was {pin}@{sha}\n      - uses: {pin}@" + OLD + "\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW),
                     "somewhere Actions does not read as a workflow to call")

    def test_a_value_continued_onto_the_next_line(self):
        text = steps("      - uses: {pin}@{sha}\n          trailing\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "at jobs.one.steps.0.uses")

    def test_line_endings_changed(self):
        self.refused(caller(), caller(gates=NEW).replace("\n", "\r\n"), "changes more than spec's pins")

    def test_line_endings_kept(self):
        code, said = self.judged(caller().replace("\n", "\r\n"), caller(gates=NEW).replace("\n", "\r\n"))
        self.assertEqual(code, 0, said)

    def test_a_value_spelt_another_way(self):
        self.refused(caller() + "x: yes\n", caller(gates=NEW) + "x: true\n", "changes more than spec's pins")

    def test_a_second_document(self):
        self.refused(caller(), caller(gates=NEW) + "---\n", "changes more than spec's pins")
        self.refused(caller() + "---\na: 1\n", caller(gates=NEW) + "---\na: 1\n", "two readers")

    def test_a_pin_in_a_script_beside_the_workflows(self):
        script = ".github/actions/setup/run.sh"
        code, said = run(Forge({script: (f"echo {SPEC_GATES}@{OLD}\n", f"echo {SPEC_GATES}@{NEW}\n")}))
        self.assertEqual(code, 1, said)
        self.assertIn(f"{script} changes, and only a workflow's spec pins may", said)

    def test_a_job_reordered(self):
        before = "jobs:\n  a:\n    uses: x\n  b:\n    uses: y\n"
        after = "jobs:\n  b:\n    uses: y\n  a:\n    uses: x\n"
        self.refused(before, after, "changes more than spec's pins")

    def test_a_list_grown_and_a_type_changed(self):
        self.assertEqual(pin_only.differences([1], [1, 2]), ([()], []))
        self.assertEqual(pin_only.differences({"a": 1}, {"b": 1}), ([()], []))
        self.assertEqual(pin_only.differences({"a": "1"}, {"a": 1}), ([("a",)], []))
        self.assertEqual(pin_only.differences({"a": [1]}, {"a": {"b": 1}}), ([("a",)], []))

    def test_each_reading_stands_without_the_text_check(self):
        # The text check refuses these first; the structure refuses them on its own too.
        old, new = f"{SPEC_GATES}@{OLD}", f"lemonfiber/spec/.github/workflows/dco.yml@{NEW}"
        self.assertEqual(pin_only.differences({"jobs": {"a": {"uses": old}}}, {"jobs": {"a": {"uses": new}}}),
                         ([("jobs", "a", "uses")], []))
        self.assertEqual(pin_only.differences({"a": 1, "b": 2}, {"b": 2, "a": 1}), ([()], []))
        self.assertEqual(pin_only.differences({"a": 1}, {"a": True}), ([("a",)], []))
        self.assertEqual(pin_only.differences({"x": {"a": {"uses": old}}}, {"x": {"a": {"uses": f"{SPEC_GATES}@{NEW}"}}}),
                         ([("x", "a", "uses")], []))
        keyed = {"jobs": {"a": {"steps": {"k": {"uses": f"{SPEC_GATES}@{OLD}"}}}}}
        moved = {"jobs": {"a": {"steps": {"k": {"uses": f"{SPEC_GATES}@{NEW}"}}}}}
        self.assertEqual(pin_only.differences(keyed, moved), ([("jobs", "a", "steps", "k", "uses")], []))

    def test_a_pin_moved_at_a_place_that_is_not_uses(self):
        old, new = f"{SPEC_GATES}@{OLD}", f"{SPEC_GATES}@{NEW}"
        self.assertEqual(pin_only.differences({"jobs": {"a": {"with": {"x": old}}}},
                                              {"jobs": {"a": {"with": {"x": new}}}}), ([("jobs", "a", "with", "x")], []))
        self.assertEqual(pin_only.differences({"uses": old}, {"uses": new}), ([("uses",)], []))
        self.assertEqual(pin_only.differences({"jobs": {"a": {"uses": old}}}, {"jobs": {"a": {"uses": new}}}),
                         ([], [(SPEC_GATES, OLD, NEW)]))


class StaleHead(unittest.TestCase):
    """A verdict is about the commit the event named, and only while it is the head."""

    def test_a_head_that_moved_before_the_run_read_it(self):
        forge = Forge({CI: (caller(), caller(gates=NEW))})
        forge.heads = [OFF]
        code, said = run(forge)
        self.assertEqual(code, 1, said)
        self.assertIn(f"the pull request's head is {OFF[:8]}, not {HEAD[:8]}", said)

    def test_a_head_that_moved_while_the_run_read_it(self):
        forge = Forge({CI: (caller(), caller(gates=NEW))})
        forge.heads = [HEAD, OFF]
        code, said = run(forge)
        self.assertEqual(code, 1, said)
        self.assertIn("the commit this run was started for", said)

    def test_every_read_names_the_commit_and_never_a_branch(self):
        forge = Forge({CI: (caller(), caller(gates=NEW))})
        run(forge)
        reads = [a[0] for a in forge.asked]
        self.assertIn(f"repos/{REPO}/git/trees/{HEAD}", reads)
        self.assertIn(f"repos/{REPO}/compare/{BASE}...{HEAD}", reads)
        self.assertFalse([r for r in reads if "ref=" in r or "/branches/" in r or "heads/" in r], reads)

    def test_a_head_that_is_not_a_commit(self):
        for head in ("main", "a" * 39, "A" * 40, ""):
            with self.subTest(head):
                code, said = run(Forge({}), head=head)
                self.assertEqual(code, 2, said)


class CannotRead(unittest.TestCase):
    def test_a_forge_that_refuses_is_a_failure_not_a_pass(self):
        def refusing(args, raw):
            raise subprocess.CalledProcessError(1, "gh", stderr="HTTP 404\n")

        code, said = run(refusing)
        self.assertEqual(code, 2)
        self.assertIn("could not be read", said)
        self.assertIn("HTTP 404", said)

    def test_an_answer_of_another_shape(self):
        code, said = run(lambda args, raw: {})
        self.assertEqual(code, 2, said)


class Gh(unittest.TestCase):
    def test_json_and_raw(self):
        calls = []

        def fake(cmd, capture_output, text, check):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout='{"a": 1}')

        original = pin_only.subprocess.run
        pin_only.subprocess.run = fake
        try:
            self.assertEqual(pin_only.gh(["repos/x"]), {"a": 1})
            self.assertEqual(pin_only.gh(["repos/x"], raw=True), '{"a": 1}')
        finally:
            pin_only.subprocess.run = original
        self.assertEqual(calls[0], ["gh", "api", "repos/x"])
        self.assertEqual(calls[1], ["gh", "api", "-H", "Accept: application/vnd.github.raw", "repos/x"])


class TheWorkflow(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.steps = self.workflow["jobs"]["pin-only"]["steps"]

    def test_it_reads_and_writes_nothing(self):
        held = {"contents": "read", "pull-requests": "read"}
        self.assertEqual(self.workflow["permissions"], held)
        self.assertEqual(self.workflow["jobs"]["pin-only"]["permissions"], held)
        self.assertEqual(list(self.workflow[True]), ["workflow_call"])

    def test_nothing_of_the_pull_request_is_checked_out(self):
        checkouts = [s for s in self.steps if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0]["with"]["repository"], "lemonfiber/spec")
        self.assertEqual(checkouts[0]["with"]["ref"], "main")
        self.assertIs(checkouts[0]["with"]["persist-credentials"], False)

    def test_it_runs_spec_s_script_with_the_pull_request_through_env(self):
        last = self.steps[-1]
        self.assertTrue(last["run"].startswith("python3 .spec-canonical/scripts/pin_only.py"))
        self.assertNotIn("${{", last["run"])
        self.assertIn('--head "$HEAD_SHA"', last["run"])
        self.assertEqual(last["env"]["HEAD_SHA"], "${{ github.event.pull_request.head.sha }}")

    def test_the_caller_it_documents_runs_on_every_new_head_and_cancels_per_pull_request(self):
        # GitHub attaches a pull_request_target run's checks to the pull request's head
        # commit (on website-lemonfiber.app#133, run 37852167512's check suite named head
        # 14c2666e, the pull request's head, while main was 577a86dd), and protection asks
        # for the check on the commit it would merge. So each new head needs its own run.
        documented = "\n".join(line[4:] for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
                               if line.startswith("#   "))
        caller_text = documented[documented.index("on:"):documented.index("jobs:")]
        shown = yaml.safe_load(caller_text)
        self.assertEqual(set(shown[True]["pull_request_target"]["types"]), {"opened", "synchronize", "reopened"})
        import check_superseded_runs
        self.assertEqual(shown["concurrency"]["group"], check_superseded_runs.TARGET_GROUP)
        self.assertIs(shown["concurrency"]["cancel-in-progress"], True)

    def test_it_refuses_any_event_but_pull_request_target(self):
        script = self.steps[0]["run"]
        for event, code in (("pull_request_target", 0), ("pull_request", 1), ("push", 1)):
            with self.subTest(event):
                done = subprocess.run(["bash", "-c", script], env={"EVENT": event, "PATH": "/usr/bin:/bin"},
                                      capture_output=True, text=True)
                self.assertEqual(done.returncode, code, done.stdout)


if __name__ == "__main__":
    unittest.main()
