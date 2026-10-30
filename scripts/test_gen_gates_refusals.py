#!/usr/bin/env python3
"""What `gen_gates.py` will not carry, each named, and the command that writes the gates workflow — Q-R82.

Run:  python3 scripts/test_gen_gates_refusals.py
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_gates


class Refusals(unittest.TestCase):
    """What the generator will not carry, each named."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patches = [
            mock.patch.object(gen_gates, "WORKFLOWS", self.tmp),
            mock.patch.object(gen_gates, "OUTPUT", self.tmp / "gates.yml"),
            mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job"),)),
            mock.patch.object(gen_gates, "MOVED", {}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def source(self, job: str, top: str = "permissions:\n  contents: read\n") -> None:
        text = f"name: one\non:\n  workflow_call:\n{top}jobs:\n  job:\n{job}"
        (self.tmp / "one.yml").write_text(text, encoding="utf-8")

    STEP = "    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@" + "1" * 40 + " # v7\n"

    def refused(self, *words: str) -> None:
        with self.assertRaises(gen_gates.Refused) as caught:
            gen_gates.build()
        for word in words:
            self.assertIn(word, str(caught.exception))

    def test_a_source_that_is_not_there(self):
        self.refused("one.yml could not be read")

    def test_a_job_in_a_source_that_no_check_names(self):
        self.source(self.STEP + "  other:\n" + self.STEP)
        self.refused("one.yml job 'other' is in a reusable gates.yml is made of", "Add it to CHECKS")

    def test_a_job_that_is_not_there(self):
        self.source(self.STEP)
        with mock.patch.object(gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "other"),)):
            self.refused("has no job 'other'")

    def test_a_key_it_cannot_carry(self):
        self.source(self.STEP + "    services:\n      db:\n        image: x\n")
        self.refused("holds services")

    def test_a_runner_that_is_not_the_shared_one(self):
        self.source(self.STEP.replace("ubuntu-latest", "macos-latest"))
        self.refused("runs on 'macos-latest'")

    def test_an_action_nobody_has_read(self):
        self.source(self.STEP + "      - uses: someone/tool@" + "2" * 40 + " # v1\n")
        self.refused("uses someone/tool", "name it in INERT or GUARDED")

    def test_a_guarded_action_with_no_guard_before_it(self):
        lint = "      - uses: DavidAnson/markdownlint-cli2-action@" + "3" * 40 + " # v24\n"
        self.source(self.STEP + lint)
        self.refused("uses DavidAnson/markdownlint-cli2-action with no step 'markdown-only' before it")
        self.source(self.STEP + lint + "      - id: markdown-only\n        run: 'true'\n")
        self.refused("with no step 'markdown-only' before it")

    def test_a_guarded_action_after_its_guard_is_carried(self):
        lint = "      - uses: DavidAnson/markdownlint-cli2-action@" + "3" * 40 + " # v24\n"
        self.source(self.STEP + "      - id: markdown-only\n        run: 'true'\n" + lint)
        self.assertIn("markdownlint-cli2-action@", gen_gates.build())

    def test_an_actor_is_not_asked_about_its_actions(self):
        # report runs only actions/ ones, which a test of the generated file holds.
        self.source(
            self.STEP + "      - uses: someone/tool@" + "2" * 40 + " # v1\n",
            top="permissions:\n  pull-requests: write\n",
        )
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)
        ):
            self.assertIn("someone/tool@", gen_gates.build())

    def test_python_started_beside_the_tree(self):
        for script in (
            "python3 - <<'PY'",
            "python3 -c 'import json'",
            "python3 scripts/x.py",
            "python3 -E -s -m x",
            "python3 -E -s - <<'PY'",
            "python -c x",
            "x | python3 -E y.py",
        ):
            self.source(self.STEP + f"      - run: {json.dumps(script)}\n")
            self.refused("starts Python without isolating it", "python3 -I", "python3 -E -s <path>")

    def test_python_started_isolated_is_carried(self):
        for script in (
            "python3 -I - <<'PY'",
            "python3 -E -s .spec-tooling/scripts/x.py",
            'python3 -E -s "$reader" --root .',
        ):
            self.source(self.STEP + f"      - run: {json.dumps(script)}\n")
            self.assertIn(script, gen_gates.build())

    def test_an_explainer_starting_python_beside_the_tree(self):
        (self.tmp / "explain-check.yml").write_text(
            "on:\n  workflow_call:\njobs:\n  explain:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: python3 - <<'PY'\n",
            encoding="utf-8",
        )
        self.source("    uses: ./.github/workflows/explain-check.yml\n")
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)
        ):
            self.refused("explain-check.yml job 'explain' starts Python without isolating it")

    def test_a_script_carrying_an_expression(self):
        self.source(self.STEP + "      - run: echo ${{ github.event.pull_request.title }}\n")
        self.refused("has an expression in its script", "Pass it through env")

    def test_an_explainer_script_carrying_an_expression(self):
        called = (
            pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/explain-check.yml"
        ).read_text(encoding="utf-8")
        (self.tmp / "explain-check.yml").write_text(
            called.replace(
                "set -euo pipefail\n", 'set -euo pipefail\n          echo "${{ inputs.title }}"\n', 1
            ),
            encoding="utf-8",
        )
        self.source(
            "    uses: ./.github/workflows/explain-check.yml\n"
            "    with:\n      check: x\n      title: t\n      body: b\n"
        )
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)
        ):
            self.refused("explain-check.yml job 'explain' has an expression in its script")

    def test_a_write_permission_put_nowhere(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        self.refused("asks for a write permission")

    def test_a_write_permission_on_a_check_that_acts_is_carried(self):
        self.source(self.STEP, top="permissions:\n  pull-requests: write\n")
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)
        ):
            self.assertIn("one / job", gen_gates.build())

    def test_an_explainer_that_is_not_a_plain_call(self):
        self.source("    uses: ./.github/workflows/other.yml\n")
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)
        ):
            self.refused("is not a plain call")

    def test_an_explainer_missing_an_input(self):
        shutil.copy(
            pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/explain-check.yml",
            self.tmp / "explain-check.yml",
        )
        self.source("    uses: ./.github/workflows/explain-check.yml\n    with:\n      check: x\n")
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.EXPLAIN),)
        ):
            self.refused("reads inputs.title, which an explainer does not pass")

    def test_a_job_read_that_nothing_carries(self):
        self.source(
            self.STEP
            + '      - name: write\n        run: echo "$X"\n        env:\n          X: ${{ needs.elsewhere.outputs.x }}\n',
            top="permissions:\n  pull-requests: write\n",
        )
        with mock.patch.object(
            gen_gates, "CHECKS", (gen_gates.Check("one", "one.yml", "job", gen_gates.ACT),)
        ):
            self.refused("reads needs.elsewhere.outputs.x")

    def test_a_job_deciding_by_a_status_function(self):
        self.source("    if: always()\n" + self.STEP)
        self.refused("decides by a status function")

    def test_a_step_deciding_by_a_status_function(self):
        self.source(self.STEP + "      - run: echo\n        if: failure()\n")
        self.refused("step deciding by a status function")

    def test_a_reference_to_a_step_that_is_not_earlier(self):
        self.source(
            self.STEP + '      - run: echo "$X"\n        env:\n          X: ${{ steps.later.outputs.x }}\n'
        )
        self.refused("steps.later")

    def test_a_moved_step_referring_to_a_step_that_is_not_earlier(self):
        self.source(
            self.STEP
            + '      - name: write\n        run: echo "$X"\n        env:\n          X: ${{ steps.later.outputs.x }}\n',
            top="permissions:\n  pull-requests: write\n",
        )
        with mock.patch.object(gen_gates, "MOVED", {("one", "job"): frozenset({"write"})}):
            self.refused("steps.later")

    def test_a_pin_with_no_version(self):
        self.source(self.STEP.replace(" # v7", ""))
        self.refused("pinned with no version comment")

    def test_one_pin_named_two_ways(self):
        self.source(self.STEP + "      - uses: actions/checkout@" + "1" * 40 + " # v8\n")
        self.refused("is called 'v7' in one reusable and 'v8' in another")

    def test_a_job_environment_reaches_each_step(self):
        self.source("    env:\n      KEPT: 'yes'\n" + self.STEP)
        self.assertIn("KEPT: 'yes'", gen_gates.build())

    def test_a_wrapped_condition_and_a_list_are_carried(self):
        self.source(
            self.STEP + "      - run: echo\n        if: ${{ github.event_name == 'push' }}\n"
            "        with:\n          many: [a, b]\n"
        )
        workflow = yaml.safe_load(gen_gates.build())
        step = workflow["jobs"]["gates"]["steps"][-3]
        self.assertTrue(step["if"].endswith("&& (github.event_name == 'push') }}"), step["if"])
        self.assertEqual(step["with"]["many"], ["a", "b"])

    def test_a_moved_step_waits_on_the_steps_before_it_in_gates(self):
        self.source(
            self.STEP + "      - run: make\n      - name: write\n        run: echo\n",
            top="permissions:\n  pull-requests: write\n",
        )
        with mock.patch.object(gen_gates, "MOVED", {("one", "job"): frozenset({"write"})}):
            workflow = yaml.safe_load(gen_gates.build())
        moved = next(s for s in workflow["jobs"]["report"]["steps"] if s["id"] == "one--job--2")
        self.assertIn("needs.gates.outputs.one--job--reached-2 == 'true'", moved["if"])
        reached = workflow["jobs"]["gates"]["outputs"]["one--job--reached-2"]
        self.assertIn("steps.one--job--0.outcome != 'failure'", reached)
        self.assertIn("steps.one--job--1.outcome != 'failure'", reached)

    def test_a_job_condition_and_an_unnamed_step(self):
        self.source("    if: github.event_name == 'pull_request'\n" + self.STEP + "      - run: echo\n")
        text = gen_gates.build()
        self.assertIn("(github.event_name == 'pull_request')", text)
        self.assertIn("one / job: step 2", text)


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patch = mock.patch.object(gen_gates, "OUTPUT", self.tmp / "gates.yml")
        patch.start()
        self.addCleanup(patch.stop)

    def call(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen_gates.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_write_then_check(self):
        self.assertEqual(self.call()[0], 0)
        code, out, _ = self.call("--check")
        self.assertEqual((code, out.strip()), (0, "gates.yml is what the reusables say"))

    def test_a_check_against_a_drifted_copy(self):
        (self.tmp / "gates.yml").write_text("edited by hand\n")
        code, _, err = self.call("--check")
        self.assertEqual(code, 1)
        self.assertIn("Run `python3 scripts/gen_gates.py`", err)

    def test_a_check_against_no_copy(self):
        self.assertEqual(self.call("--check")[0], 1)

    def test_a_refusal_is_said_and_fails(self):
        with mock.patch.object(gen_gates, "build", side_effect=gen_gates.Refused("no")):
            code, _, err = self.call()
        self.assertEqual((code, err.strip()), (1, "::error::no"))


if __name__ == "__main__":
    unittest.main()
