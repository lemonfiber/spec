#!/usr/bin/env python3
"""Moving the pins the core's substitute proofs run at — F14-R14, OPS-R87.

Run:  python3 scripts/test_substitute_pin.py
"""

from __future__ import annotations

import io
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import substitute_pin
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/substitute-pin.yml"

OLD = "0" * 40
NEW = "a" * 40
PLEX = "https://github.com/lemonfiber/plugin-plex"
EMBY = "https://github.com/lemonfiber/plugin-emby"

PINS = f"""# Each arm.
schema = 1

[[substitute]]
arm      = "plex"
origin   = "{PLEX}"
revision = "{OLD}"  # the pin
claimed  = false

[[substitute]]
arm      = "emby"
origin   = "{EMBY}"
revision = "{NEW}"
claimed  = true
"""


def answering(stdout: str = f"{NEW}\tHEAD\n", code: int = 0, stderr: str = "") -> mock._patch:
    """`git ls-remote`, answering every repository alike."""
    return mock.patch.object(
        substitute_pin.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], code, stdout, stderr),
    )


class Reading(unittest.TestCase):
    def test_the_arms_are_read(self):
        self.assertEqual([arm["arm"] for arm in substitute_pin.arms(PINS)], ["plex", "emby"])

    def test_anything_else_is_refused_naming_it(self):
        for text, said in (
            ("not toml =", "not TOML"),
            ("schema = 2", "schema 2"),
            ('schema = 1\n[[substitute]]\narm = "x"\norigin = "https://example.test/x"', "first-party"),
            ('schema = 1\n[[substitute]]\narm = "x"\norigin = "https://github.com/lemonfiber/sdk-php"', "first-party"),
        ):
            with self.subTest(text), self.assertRaisesRegex(substitute_pin.Refused, said):
                substitute_pin.arms(text)


class Asking(unittest.TestCase):
    def test_a_repository_is_asked_what_its_default_branch_names(self):
        with answering() as run:
            self.assertEqual(substitute_pin.head_of(PLEX), NEW)
        self.assertEqual(run.call_args.args[0], ["git", "ls-remote", "--", PLEX, "HEAD"])

    def test_no_answer_or_no_commit_is_refused(self):
        with answering(code=128, stderr="not found"), self.assertRaisesRegex(substitute_pin.Refused, "not found"):
            substitute_pin.head_of(PLEX)
        with answering(stdout=""), self.assertRaisesRegex(substitute_pin.Refused, "names no commit"):
            substitute_pin.head_of(PLEX)
        with (
            mock.patch.object(
                substitute_pin.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("git", substitute_pin.PATIENCE),
            ),
            self.assertRaisesRegex(substitute_pin.Refused, "did not answer within"),
        ):
            substitute_pin.head_of(PLEX)


class Moving(unittest.TestCase):
    def test_each_revision_moves_and_nothing_else(self):
        after = substitute_pin.moved(PINS, substitute_pin.arms(PINS), {PLEX: NEW, EMBY: NEW})
        self.assertEqual(after, PINS.replace(OLD, NEW))
        self.assertIn(f'revision = "{NEW}"  # the pin', after)

    def test_an_arm_without_a_revision_line_is_refused(self):
        text = f'[[substitute]]\narm = "plex"\norigin = "{PLEX}"\n'
        with self.assertRaisesRegex(substitute_pin.Refused, "0 revision lines"):
            substitute_pin.moved(text, [{"arm": "plex", "origin": PLEX}], {PLEX: NEW})

    def test_the_message_names_what_moved_and_cites_the_rows(self):
        said = substitute_pin.message(substitute_pin.arms(PINS), {PLEX: NEW, EMBY: NEW})
        self.assertIn(f"- plex: plugin-plex at {NEW}", said)
        self.assertNotIn("- emby", said)
        self.assertTrue(said.endswith(f"{substitute_pin.CITED}\n"))


class Main(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.dir)
        self.pins = self.dir / "substitutes.toml"
        self.pins.write_text(PINS, encoding="utf-8")
        self.message = self.dir / "message.txt"

    def apply(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = substitute_pin.main(
                ["apply", "--pins", "substitutes.toml", "--message", "message.txt", *argv]
            )
        return code, out.getvalue(), err.getvalue()

    def test_a_moved_pin_is_written_with_its_message(self):
        with answering():
            code, out, _ = self.apply()
        self.assertEqual((code, out), (0, "moved=yes\n"))
        self.assertEqual(self.pins.read_text(encoding="utf-8"), PINS.replace(OLD, NEW))
        self.assertIn("plugin-plex", self.message.read_text(encoding="utf-8"))

    def test_pins_already_there_write_nothing(self):
        self.pins.write_text(PINS.replace(OLD, NEW), encoding="utf-8")
        with answering():
            code, out, _ = self.apply()
        self.assertEqual((code, out), (0, "moved=no\n"))
        self.assertFalse(self.message.exists())

    def test_a_refusal_writes_nothing_and_says_why(self):
        with answering(code=1, stderr="gone"):
            code, _, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)
        self.assertEqual(self.pins.read_text(encoding="utf-8"), PINS)

    def test_it_runs_as_a_script(self):
        with (
            answering(),
            mock.patch.object(sys, "argv", ["substitute_pin.py", "apply", "--pins", "substitutes.toml", "--message", "m"]),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as ended,
        ):
            runpy.run_path(substitute_pin.__file__, run_name="__main__")
        self.assertEqual(ended.exception.code, 0)


class Workflow(unittest.TestCase):
    def test_it_commits_only_in_the_core_and_the_token_writes_contents_alone(self):
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        self.assertIn("github.repository == 'lemonfiber/lemonfiber'", jobs["commit"]["if"])
        minted = next(step for step in jobs["commit"]["steps"] if "create-github-app-token" in step.get("uses", ""))
        self.assertEqual(minted["with"]["permission-contents"], "write")
        self.assertEqual(minted["with"]["repositories"], "lemonfiber")


if __name__ == "__main__":
    unittest.main()
