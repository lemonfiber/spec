#!/usr/bin/env python3
"""Evaluate a GitHub Actions expression against a context, the way a runner would.

A job-level `if:` decides whether a runner starts at all, and nothing runs it
before a pull request merges: a condition that is wrong skips a check that
should have run, or starts the runner it was written to save, and either shows
only in a run nobody reads. So the conditions that decide whether a runner
starts are evaluated here, over the events they answer, by the tests that hold
them.

This is the language as GitHub documents it, to the extent those conditions use
it: literals, context properties (dotted, indexed and `*`-filtered), `!`, the
comparisons, `&&` and `||` returning an operand, string comparison that ignores
case, loose equality that coerces to a number, and the functions `contains`,
`startsWith`, `endsWith`, `format`, `join`, `toJSON`, `fromJSON` and the four
status functions. Anything outside that is refused, not guessed.

Usage, from a test:

    from workflow_expression import evaluate
    evaluate("github.event_name == 'push'", {"github": {"event_name": "push"}})
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

#: The token kinds, each its own simple pattern, tried in this order at each place.
TOKENS = (
    ("number", re.compile(r"0x[0-9a-fA-F]+")),
    ("number", re.compile(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?")),
    ("number", re.compile(r"-?\.\d+(?:[eE][+-]?\d+)?")),
    ("string", re.compile(r"'(?:[^']|'')*'")),
    ("op", re.compile(r"==|!=|<=|>=|&&|\|\||[!<>()\[\],.*]")),
    ("name", re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")),
)


class Unsupported(ValueError):
    """An expression this evaluator does not read, named rather than guessed at."""


@dataclass
class Token:
    kind: str
    text: str


def tokens(text: str) -> list[Token]:
    """The expression's tokens, refusing anything the language does not have."""
    text = text.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    found: list[Token] = []
    where = 0
    while text[where:].strip():
        while text[where].isspace():
            where += 1
        token = next(
            (Token(kind, match.group(0)) for kind, pattern in TOKENS if (match := pattern.match(text, where))),
            None,
        )
        if token is None:
            raise Unsupported(f"cannot read {text[where:]!r}")
        found.append(token)
        where += len(token.text)
    return found


class Filtered(list):
    """The array a `*` filter makes, which a property access maps over."""


def truthy(value) -> bool:
    """GitHub's truthiness: false, 0, -0, '', null and NaN are false."""
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not (value == 0 or math.isnan(value))
    if isinstance(value, str):
        return value != ""
    return True


def number(value) -> float:
    """A value coerced to a number, as loose comparison does."""
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return 0.0
        try:
            return float(int(text, 16)) if text.lower().startswith("0x") else float(text)
        except ValueError:
            return math.nan
    return math.nan


def equal(left, right) -> bool:
    """Loose equality: case-insensitive between strings, numeric between kinds."""
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    if isinstance(left, (dict, list)) or isinstance(right, (dict, list)):
        return left is right
    if left is None and right is None:
        return True
    if type(left) is type(right):
        return left == right
    return number(left) == number(right)


def order(left, right, compare) -> bool:
    """A comparison: strings by case-insensitive text, anything else by number."""
    if isinstance(left, str) and isinstance(right, str):
        return compare(left.casefold(), right.casefold())
    a, b = number(left), number(right)
    if math.isnan(a) or math.isnan(b):
        return False
    return compare(a, b)


def text_of(value) -> str:
    """A value as `format` and `join` write it."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def contains(search, item) -> bool:
    if isinstance(search, list):
        return any(equal(one, item) for one in search)
    return text_of(item).casefold() in text_of(search).casefold()


def formatted(template, *args) -> str:
    def swap(match: re.Match) -> str:
        if match.group(0) == "{{":
            return "{"
        if match.group(0) == "}}":
            return "}"
        index = int(match.group(1))
        if index >= len(args):
            raise Unsupported(f"format names argument {index} of {len(args)}")
        return text_of(args[index])

    return re.sub(r"\{\{|\}\}|\{(\d+)\}", swap, text_of(template))


FUNCTIONS = {
    "contains": (2, contains),
    "startswith": (2, lambda a, b: text_of(a).casefold().startswith(text_of(b).casefold())),
    "endswith": (2, lambda a, b: text_of(a).casefold().endswith(text_of(b).casefold())),
    "join": (None, lambda items, sep=",": text_of(sep).join(text_of(i) for i in items)
             if isinstance(items, list) else text_of(items)),
    "tojson": (1, lambda value: json.dumps(value, indent=2)),
    "fromjson": (1, lambda value: json.loads(value)),
    "format": (None, formatted),
}

#: The job's state the four status functions read.
STATUS = {"success", "failure", "cancelled", "always"}


class Parser:
    """A precedence parser over the tokens, evaluating as it goes."""

    def __init__(self, found: list[Token], context: dict, status: str):
        self.found = found
        self.at = 0
        self.context = context
        self.status = status

    def peek(self) -> Token | None:
        return self.found[self.at] if self.at < len(self.found) else None

    def take(self, text: str | None = None) -> Token:
        token = self.peek()
        if token is None or (text is not None and token.text != text):
            raise Unsupported(f"expected {text or 'more'} at token {self.at}")
        self.at += 1
        return token

    def parse(self):
        value = self.disjunction()
        if self.peek() is not None:
            raise Unsupported(f"unexpected {self.peek().text!r}")
        return value

    def disjunction(self):
        value = self.conjunction()
        while self.peek() and self.peek().text == "||":
            self.take()
            right = self.conjunction()
            value = value if truthy(value) else right
        return value

    def conjunction(self):
        value = self.equality()
        while self.peek() and self.peek().text == "&&":
            self.take()
            right = self.equality()
            value = right if truthy(value) else value
        return value

    def equality(self):
        value = self.comparison()
        while self.peek() and self.peek().text in ("==", "!="):
            op = self.take().text
            right = self.comparison()
            value = equal(value, right) if op == "==" else not equal(value, right)
        return value

    def comparison(self):
        value = self.unary()
        while self.peek() and self.peek().text in ("<", "<=", ">", ">="):
            op = self.take().text
            right = self.unary()
            value = order(value, right, {
                "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
                ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
            }[op])
        return value

    def unary(self):
        if self.peek() and self.peek().text == "!":
            self.take()
            return not truthy(self.unary())
        return self.postfix(self.primary())

    def primary(self):
        token = self.take()
        if token.text == "(":
            value = self.disjunction()
            self.take(")")
            return value
        if token.kind == "number":
            return float(int(token.text, 16)) if token.text.lower().startswith("0x") else float(token.text)
        if token.kind == "string":
            return token.text[1:-1].replace("''", "'")
        if token.kind != "name":
            raise Unsupported(f"unexpected {token.text!r}")
        word = token.text
        if self.peek() and self.peek().text == "(":
            return self.call(word)
        if word == "true":
            return True
        if word == "false":
            return False
        if word == "null":
            return None
        return self.index(self.context, word)

    def call(self, word: str):
        self.take("(")
        args = []
        while self.peek() and self.peek().text != ")":
            args.append(self.disjunction())
            if self.peek() and self.peek().text == ",":
                self.take()
        self.take(")")
        name = word.lower()
        if name in STATUS:
            if args:
                raise Unsupported(f"{word}() takes no arguments")
            return {
                "always": True,
                "success": self.status == "success",
                "failure": self.status == "failure",
                "cancelled": self.status == "cancelled",
            }[name]
        if name not in FUNCTIONS:
            raise Unsupported(f"{word}() is not a function this evaluator reads")
        arity, function = FUNCTIONS[name]
        if arity is not None and len(args) != arity:
            raise Unsupported(f"{word}() takes {arity} arguments, not {len(args)}")
        return function(*args)

    def postfix(self, value):
        while self.peek() and self.peek().text in (".", "["):
            if self.take().text == ".":
                token = self.take()
                key = "*" if token.text == "*" else token.text
                if token.kind != "name" and key != "*":
                    raise Unsupported(f"cannot read property {token.text!r}")
            else:
                inner = self.disjunction()
                self.take("]")
                key = inner
            value = self.index(value, key)
        return value

    @staticmethod
    def index(value, key):
        if key == "*":
            return filtered(value)
        if isinstance(value, Filtered):
            return Filtered(item for item in (Parser.index(one, key) for one in value) if item is not None)
        if isinstance(value, dict):
            return named(value, key)
        if isinstance(value, list):
            return at(value, key)
        return None


def filtered(value) -> Filtered:
    """What a `*` filter makes of a value: an object's values, an array's items, or nothing."""
    if isinstance(value, dict):
        return Filtered(value.values())
    if isinstance(value, list):
        return Filtered(value)
    return Filtered()


def named(value: dict, key):
    """An object's property, read whatever its case; null where it has none."""
    if not isinstance(key, str):
        return None
    return next((item for name, item in value.items() if name.casefold() == key.casefold()), None)


def at(value: list, key):
    """An array's item at a whole-number index; null anywhere else."""
    if not (isinstance(key, float) and key.is_integer()):
        return None
    whole = int(key)
    return value[whole] if 0 <= whole < len(value) else None


def evaluate(expression: str, context: dict, status: str = "success"):
    """The value of one expression, with the job in the given status."""
    return Parser(tokens(expression), context, status).parse()


def decides(expression: str, context: dict, status: str = "success") -> bool:
    """Whether a job or step condition holds, with the implied `success()` added.

    A condition that names no status function is read by GitHub as
    `success() && (condition)`.
    """
    named = any(t.kind == "name" and t.text.lower() in STATUS for t in tokens(expression))
    held = truthy(evaluate(expression, context, status))
    return held if named else (status == "success" and held)
