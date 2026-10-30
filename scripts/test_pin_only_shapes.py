#!/usr/bin/env python3
"""Each way YAML can make the text `pin_only.py` judges differ from what Actions runs — Q-R83.

Run:  python3 scripts/test_pin_only_shapes.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pin_only
from test_pin_only import CI, NEW, OFF, OLD, Forge, caller, run

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
        self.refused(
            steps(script.format(pin=SPEC_GATES, sha=OLD)),
            steps(script.format(pin=SPEC_GATES, sha=NEW)),
            "at jobs.one.steps.0.run",
        )

    def test_a_step_written_as_a_flow_mapping_is_a_step(self):
        step = "      - {{uses: {pin}@{sha}}}\n"
        code, said = self.judged(
            steps(step.format(pin=SPEC_GATES, sha=OLD)), steps(step.format(pin=SPEC_GATES, sha=NEW))
        )
        self.assertEqual(code, 0, said)
        self.refused(
            steps(step.format(pin=SPEC_GATES, sha=OLD)),
            steps(step.format(pin=SPEC_GATES, sha=OFF)),
            "is not on lemonfiber/spec main",
        )

    def test_an_anchor_and_an_alias(self):
        text = "x: &p {pin}@{sha}\n" + steps("      - uses: *p\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD),
            text.format(pin=SPEC_GATES, sha=NEW),
            "two readers could take differently",
            "the anchor &p",
        )

    def test_an_alias_elsewhere_in_the_file(self):
        text = "x: &p 1\ny: *p\n" + steps("      - uses: {pin}@{sha}\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "two readers"
        )

    def test_an_alias_naming_no_anchor(self):
        with self.assertRaisesRegex(pin_only.Unsafe, "an alias"):
            pin_only.strict("a: *p\n")

    def test_a_merge_key(self):
        text = steps("      - <<: {{uses: {pin}@{sha}}}\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "a merge key"
        )

    def test_an_explicit_tag(self):
        text = steps("      - uses: !!str {pin}@{sha}\n")
        self.refused(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "the tag")

    def test_a_key_given_twice(self):
        text = steps("      - uses: {pin}@{sha}\n        uses: {pin}@" + OLD + "\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW), "the key 'uses' twice"
        )

    def test_a_quoted_key_that_is_not_uses(self):
        text = steps('      - "uses ": {pin}@{sha}\n        run: x\n')
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD),
            text.format(pin=SPEC_GATES, sha=NEW),
            "at jobs.one.steps.0.uses ",
        )

    def test_an_escaped_key_that_is_uses_is_read_as_uses(self):
        text = steps('      - "use\\x73": {pin}@{sha}\n')
        code, said = self.judged(text.format(pin=SPEC_GATES, sha=OLD), text.format(pin=SPEC_GATES, sha=NEW))
        self.assertEqual(code, 0, said)

    def test_a_pin_in_a_comment(self):
        text = steps("      # was {pin}@{sha}\n      - uses: {pin}@" + OLD + "\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD),
            text.format(pin=SPEC_GATES, sha=NEW),
            "somewhere Actions does not read as a workflow to call",
        )

    def test_a_value_continued_onto_the_next_line(self):
        text = steps("      - uses: {pin}@{sha}\n          trailing\n")
        self.refused(
            text.format(pin=SPEC_GATES, sha=OLD),
            text.format(pin=SPEC_GATES, sha=NEW),
            "at jobs.one.steps.0.uses",
        )

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
        self.assertEqual(
            pin_only.differences({"jobs": {"a": {"uses": old}}}, {"jobs": {"a": {"uses": new}}}),
            ([("jobs", "a", "uses")], []),
        )
        self.assertEqual(pin_only.differences({"a": 1, "b": 2}, {"b": 2, "a": 1}), ([()], []))
        self.assertEqual(pin_only.differences({"a": 1}, {"a": True}), ([("a",)], []))
        self.assertEqual(
            pin_only.differences({"x": {"a": {"uses": old}}}, {"x": {"a": {"uses": f"{SPEC_GATES}@{NEW}"}}}),
            ([("x", "a", "uses")], []),
        )
        keyed = {"jobs": {"a": {"steps": {"k": {"uses": f"{SPEC_GATES}@{OLD}"}}}}}
        moved = {"jobs": {"a": {"steps": {"k": {"uses": f"{SPEC_GATES}@{NEW}"}}}}}
        self.assertEqual(pin_only.differences(keyed, moved), ([("jobs", "a", "steps", "k", "uses")], []))

    def test_a_pin_moved_at_a_place_that_is_not_uses(self):
        old, new = f"{SPEC_GATES}@{OLD}", f"{SPEC_GATES}@{NEW}"
        self.assertEqual(
            pin_only.differences(
                {"jobs": {"a": {"with": {"x": old}}}}, {"jobs": {"a": {"with": {"x": new}}}}
            ),
            ([("jobs", "a", "with", "x")], []),
        )
        self.assertEqual(pin_only.differences({"uses": old}, {"uses": new}), ([("uses",)], []))
        self.assertEqual(
            pin_only.differences({"jobs": {"a": {"uses": old}}}, {"jobs": {"a": {"uses": new}}}),
            ([], [(SPEC_GATES, OLD, NEW)]),
        )


if __name__ == "__main__":
    unittest.main()
