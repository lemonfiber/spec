#!/usr/bin/env python3
"""Asking a registry through `docker buildx imagetools inspect`: a registry is called
empty only where it says so, and one that did not answer is asked again before the
reference could not be checked.

Run:  python3 scripts/test_imagetools.py
"""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

import imagetools

REFERENCE = "ghcr.io/lemonfiber/fence:v0.18.0"
DESCRIPTOR = '{"digest": "sha256:' + "a" * 64 + '"}\n'
HELD = subprocess.CompletedProcess([], 0, stdout=DESCRIPTOR, stderr="")
ABSENT = subprocess.CompletedProcess([], 1, stdout="", stderr=f"ERROR: {REFERENCE}: not found\n")
LIMITED = subprocess.CompletedProcess([], 1, stdout="", stderr="ERROR: unexpected status: 429 Too Many Requests\n")
SILENT = subprocess.CompletedProcess([], 1, stdout="", stderr="")


class Manifest(unittest.TestCase):
    def asked(self, *answers: subprocess.CompletedProcess) -> tuple[str | Exception, int, list]:
        with (
            mock.patch.object(imagetools.subprocess, "run", side_effect=list(answers)) as run,
            mock.patch.object(imagetools.time, "sleep") as sleep,
        ):
            try:
                said: str | Exception = imagetools.manifest(REFERENCE)
            except (imagetools.Absent, imagetools.Unanswered) as why:
                said = why
        return said, run.call_count, [call.args[0] for call in sleep.call_args_list]

    def test_what_the_registry_holds_is_its_descriptor(self):
        self.assertEqual(self.asked(HELD), (DESCRIPTOR, 1, []))

    def test_a_reference_the_registry_holds_none_of_is_absent_at_once(self):
        said, asked, waits = self.asked(ABSENT)
        self.assertIsInstance(said, imagetools.Absent)
        self.assertEqual((str(said), asked, waits), (f"ERROR: {REFERENCE}: not found", 1, []))

    def test_a_rate_limit_that_lifts_is_asked_again(self):
        self.assertEqual(self.asked(LIMITED, HELD), (DESCRIPTOR, 2, [imagetools.FIRST_WAIT_S]))

    def test_a_registry_that_never_answers_could_not_be_checked(self):
        said, asked, waits = self.asked(*[LIMITED] * imagetools.ATTEMPTS)
        self.assertIsInstance(said, imagetools.Unanswered)
        self.assertEqual(
            str(said),
            f"{REFERENCE} could not be checked: its registry did not answer in {imagetools.ATTEMPTS} "
            "attempts (ERROR: unexpected status: 429 Too Many Requests)",
        )
        self.assertEqual(asked, imagetools.ATTEMPTS)
        self.assertEqual(
            waits, [imagetools.FIRST_WAIT_S * imagetools.BACKOFF**at for at in range(imagetools.ATTEMPTS - 1)]
        )

    def test_a_failure_that_says_nothing_names_its_exit(self):
        said, _, _ = self.asked(*[SILENT] * imagetools.ATTEMPTS)
        self.assertIn(f"in {imagetools.ATTEMPTS} attempts (exit 1)", str(said))


if __name__ == "__main__":
    unittest.main(verbosity=2)
