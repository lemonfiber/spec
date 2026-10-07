#!/usr/bin/env python3
"""Which version the report judges, and what blocks it — OPS-R44, OPS-R83.

The version in flight is the first staged or in-progress one in train order,
never a releasable, planned or released one and never the template; a version's
blockers are the tables its manifest lists, each named in the refusal; a
manifest that is not there or cannot be read stops the question.

Stdlib unittest.
Run:  python3 scripts/test_in_flight.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import in_flight  # noqa: E402


def run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["in_flight.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = in_flight.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class InFlight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        pathlib.Path("70-operations/versions").mkdir(parents=True)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manifest(self, version, status, extra=""):
        pathlib.Path(f"70-operations/versions/{version}.toml").write_text(
            f'version = "{version}"\nstatus = "{status}"\ngoals = []\n{extra}',
            encoding="utf-8")

    def test_the_first_staged_or_in_progress_version_in_train_order(self):
        self.manifest("0.10.0", "in_progress")
        self.manifest("0.9.0", "staged")
        self.manifest("0.8.0", "releasable")
        self.manifest("0.1.0", "released")
        self.manifest("0.11.0", "planned")
        self.manifest("TEMPLATE", "staged")
        self.assertEqual(run_main(["version"]), (0, "0.9.0\n"))

    def test_nothing_in_flight(self):
        self.manifest("0.1.0", "released")
        self.manifest("0.2.0", "releasable")
        self.assertEqual(run_main(["version"]), (0, "\n"))

    def test_no_blocker_listed(self):
        self.manifest("0.2.0", "staged")
        self.assertEqual(run_main(["blockers", "--version", "0.2.0"]), (0, ""))

    def test_each_blocker_named(self):
        self.manifest("0.2.0", "staged",
                      '[[blockers]]\nwhat = "the stack image"\nwhere = "https://x/1"\n'
                      '[[blockers]]\n')
        code, said = run_main(["blockers", "--version", "0.2.0"])
        self.assertEqual(code, 1)
        self.assertIn("::error::0.2.0 is blocked: the stack image — https://x/1", said)
        self.assertIn("(unnamed) — nowhere named", said)

    def test_a_manifest_that_is_not_there(self):
        code, said = run_main(["blockers", "--version", "9.9.9"])
        self.assertEqual(code, 2)
        self.assertIn("::error::", said)

    def test_a_manifest_that_cannot_be_read(self):
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text("version = [",
                                                                      encoding="utf-8")
        self.assertEqual(run_main(["version"])[0], 2)


if __name__ == "__main__":
    unittest.main()
