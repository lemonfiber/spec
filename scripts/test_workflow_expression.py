#!/usr/bin/env python3
"""What the expression evaluator answers, held against GitHub's documented rules.

The evaluator is the ruler the job conditions are measured with, so a wrong
answer here passes a wrong condition there. Each rule the conditions rely on is
pinned by a case that would fail if the rule were read the other way: `||`
returning an operand rather than a boolean, string comparison ignoring case, a
missing property reading as null, the implied `success()`.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_workflow_expression.py
"""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from workflow_expression import (
    Unsupported,
    decides,
    equal,
    evaluate,
    number,
    order,
    text_of,
    tokens,
    truthy,
)

CONTEXT = {
    "github": {
        "event_name": "pull_request",
        "repository": "lemonfiber/core",
        "event": {
            "pull_request": {
                "labels": [{"name": "ci"}, {"name": "awaiting-maintainer"}],
                "head": {"repo": {"full_name": "lemonfiber/core"}},
            },
        },
    },
    "inputs": {"build-log": True, "checks": "hygiene dco"},
    "matrix": {"items": ["a", "b"], "count": 2},
}


def value(expression: str):
    return evaluate(expression, CONTEXT)


class Literals(unittest.TestCase):
    def test_each_kind(self):
        self.assertIs(value("true"), True)
        self.assertIs(value("false"), False)
        self.assertIsNone(value("null"))
        self.assertEqual(value("42"), 42.0)
        self.assertEqual(value("-1.5e2"), -150.0)
        self.assertEqual(value("0xff"), 255.0)
        self.assertEqual(value("'it''s'"), "it's")

    def test_the_wrapper_is_read_through(self):
        self.assertIs(value("${{ true }}"), True)

    def test_an_empty_expression_is_refused(self):
        with self.assertRaises(Unsupported):
            value("")

    def test_a_character_the_language_lacks_is_refused(self):
        with self.assertRaises(Unsupported):
            tokens("a $ b")


class Properties(unittest.TestCase):
    def test_dotted_and_indexed_read_the_same(self):
        self.assertEqual(value("github.event_name"), "pull_request")
        self.assertEqual(value("github['event_name']"), "pull_request")

    def test_a_name_is_read_whatever_its_case(self):
        self.assertEqual(value("GitHub.Event_Name"), "pull_request")

    def test_a_hyphen_belongs_to_the_name(self):
        self.assertIs(value("inputs.build-log"), True)

    def test_a_missing_property_is_null(self):
        self.assertIsNone(value("github.event.workflow_run.conclusion"))
        self.assertIsNone(value("nothing.here"))
        self.assertIsNone(value("github.event_name.length"))

    def test_a_number_does_not_index_an_object(self):
        self.assertIsNone(value("github[1]"))

    def test_an_array_index(self):
        self.assertEqual(value("matrix.items[1]"), "b")
        self.assertIsNone(value("matrix.items[5]"))
        self.assertIsNone(value("matrix.items['x']"))

    def test_a_filter_maps_a_property_over_an_array(self):
        self.assertEqual(value("github.event.pull_request.labels.*.name"), ["ci", "awaiting-maintainer"])

    def test_a_filter_over_an_object_takes_its_values(self):
        self.assertEqual(value("matrix.*"), [["a", "b"], 2])

    def test_a_filter_over_a_scalar_is_empty(self):
        self.assertEqual(value("github.event_name.*"), [])

    def test_a_string_is_not_a_property_name(self):
        with self.assertRaises(Unsupported):
            value("github.'x'")


class Operators(unittest.TestCase):
    def test_or_returns_the_first_truthy_operand(self):
        self.assertEqual(value("'' || 'b'"), "b")
        self.assertEqual(value("'a' || 'b'"), "a")

    def test_and_returns_the_first_falsy_operand(self):
        self.assertEqual(value("'' && 'b'"), "")
        self.assertEqual(value("'a' && 'b'"), "b")

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(value("false && 'x' || 'y'"), "y")
        self.assertTrue(value("true || false && false"))
        self.assertEqual(value("'a' || 'b' && ''"), "a")

    def test_not_and_parentheses(self):
        self.assertIs(value("!(true && false)"), True)
        self.assertIs(value("!''"), True)

    def test_comparisons(self):
        self.assertIs(value("matrix.count > 1"), True)
        self.assertIs(value("matrix.count >= 2"), True)
        self.assertIs(value("matrix.count < 2"), False)
        self.assertIs(value("matrix.count <= 1"), False)
        self.assertIs(value("'B' > 'a'"), True)
        self.assertIs(value("'x' < 1"), False)

    def test_inequality(self):
        self.assertIs(value("github.event_name != 'push'"), True)

    def test_a_dangling_operator_is_refused(self):
        with self.assertRaises(Unsupported):
            value("true &&")

    def test_a_stray_token_is_refused(self):
        with self.assertRaises(Unsupported):
            value("true true")

    def test_an_operator_where_a_value_belongs_is_refused(self):
        with self.assertRaises(Unsupported):
            value(", true")

    def test_an_unclosed_parenthesis_is_refused(self):
        with self.assertRaises(Unsupported):
            value("(true")


class Equality(unittest.TestCase):
    def test_strings_compare_without_case(self):
        self.assertTrue(equal("Approved", "approved"))

    def test_kinds_compare_as_numbers(self):
        self.assertTrue(equal("1", 1.0))
        self.assertTrue(equal(True, 1.0))
        self.assertTrue(equal(None, 0.0))
        self.assertFalse(equal("abc", 0.0))

    def test_null_equals_null_and_like_kinds_compare_directly(self):
        self.assertTrue(equal(None, None))
        self.assertTrue(equal(2.0, 2.0))

    def test_objects_are_equal_only_to_themselves(self):
        one = {"a": 1}
        self.assertTrue(equal(one, one))
        self.assertFalse(equal({"a": 1}, {"a": 1}))

    def test_coercions(self):
        self.assertEqual(number(""), 0.0)
        self.assertEqual(number(" 0x10 "), 16.0)
        self.assertEqual(number(False), 0.0)
        self.assertTrue(math.isnan(number([])))
        self.assertTrue(math.isnan(number("nope")))
        self.assertTrue(order(2.0, "3", lambda a, b: a < b))


class Truth(unittest.TestCase):
    def test_the_falsy_values(self):
        for falsy in (False, 0.0, -0.0, "", None, math.nan):
            self.assertFalse(truthy(falsy), falsy)
        for true in (True, 1.0, "false", [], {}):
            self.assertTrue(truthy(true), true)


class Functions(unittest.TestCase):
    def test_contains_over_a_string_and_an_array(self):
        self.assertIs(value("contains(github.event.pull_request.labels.*.name, 'AWAITING-maintainer')"), True)
        self.assertIs(value("contains(inputs.checks, 'DCO')"), True)
        self.assertIs(value("contains(inputs.checks, 'labeler')"), False)

    def test_starts_and_ends(self):
        self.assertIs(value("startsWith(github.repository, 'LEMONFIBER/')"), True)
        self.assertIs(value("endsWith(github.repository, '/core')"), True)

    def test_format_and_join(self):
        self.assertEqual(value("format('{0}-{1} {{x}}', 'a', 2)"), "a-2 {x}")
        self.assertEqual(value("join(matrix.items, '+')"), "a+b")
        self.assertEqual(value("join(matrix.items)"), "a,b")
        self.assertEqual(value("join('solo')"), "solo")

    def test_format_naming_an_argument_it_lacks_is_refused(self):
        with self.assertRaises(Unsupported):
            value("format('{1}', 'a')")

    def test_json_both_ways(self):
        self.assertEqual(value("fromJSON('[\"a\"]')"), ["a"])
        self.assertEqual(value("toJSON(matrix.count)"), "2")

    def test_text_of_each_kind(self):
        self.assertEqual(text_of(None), "")
        self.assertEqual(text_of(True), "true")
        self.assertEqual(text_of(False), "false")
        self.assertEqual(text_of(1.5), "1.5")
        self.assertEqual(text_of([1]), "[1]")

    def test_an_unknown_function_is_refused(self):
        with self.assertRaises(Unsupported):
            value("hashFiles('x')")

    def test_the_wrong_number_of_arguments_is_refused(self):
        with self.assertRaises(Unsupported):
            value("contains('a')")

    def test_a_status_function_takes_no_argument(self):
        with self.assertRaises(Unsupported):
            value("always(1)")


class Status(unittest.TestCase):
    def test_each_status_function(self):
        self.assertIs(evaluate("success()", {}, "success"), True)
        self.assertIs(evaluate("failure()", {}, "failure"), True)
        self.assertIs(evaluate("cancelled()", {}, "cancelled"), True)
        self.assertIs(evaluate("always()", {}, "failure"), True)

    def test_a_condition_with_no_status_function_implies_success(self):
        self.assertTrue(decides("true", {}, "success"))
        self.assertFalse(decides("true", {}, "failure"))

    def test_a_condition_naming_one_decides_for_itself(self):
        self.assertTrue(decides("!cancelled()", {}, "failure"))
        self.assertFalse(decides("!cancelled()", {}, "cancelled"))


if __name__ == "__main__":
    unittest.main()
