#!/usr/bin/env python3
"""A pin bump committed as the App, so GitHub signs it — OPS-R85.

`gh` is replaced on a PATH prefix by a stub that records every call and answers
as each case asks; `git` is the real one, on a clone made here, so the files the
commit carries are the ones the working tree really changed.

Run:  python3 scripts/test_signed_pin_commit.py
"""

from __future__ import annotations

import base64
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import signed_pin_commit

OID = "0123456789abcdef0123456789abcdef01234567"

GH_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "${GH_LOG}"
case "$1 $2" in
"api graphql")
  cat > "${GH_REQUEST}"
  [ -z "${GH_COMMIT_FAILS:-}" ] || { echo "graphql said no" >&2; exit 1; }
  printf '%s\\n' "${GH_OID}"
  exit 0
  ;;
esac
case "$*" in
*git/ref/heads/*)
  for one in ${GH_EXISTS:-}; do
    case "$*" in *"/git/ref/heads/$one") exit 0 ;; esac
  done
  exit 1
  ;;
*"--method DELETE"*)
  [ -z "${GH_DELETE_FAILS:-}" ] || exit 1
  exit 0
  ;;
*git/refs*)
  for one in ${GH_REF_FAILS:-}; do
    case "$*" in *"$one"*) echo "ref refused" >&2; exit 1 ;; esac
  done
  exit 0
  ;;
esac
exit 0
"""


class SignedPinCommit(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.repo = self.root / "repo"
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        (self.repo / ".github" / "workflows" / "ci.yml").write_text("old\n", encoding="utf-8")
        (self.repo / ".github" / "workflows" / "gone.yml").write_text("x\n", encoding="utf-8")
        for args in (
            ("init", "-q", "-b", "main"),
            ("config", "user.email", "t@example.com"),
            ("config", "user.name", "T"),
            ("add", "-A"),
            ("commit", "-qm", "as it stands"),
        ):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)
        self.base = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        (self.repo / ".github" / "workflows" / "ci.yml").write_text("new\n", encoding="utf-8")
        (self.repo / ".github" / "workflows" / "gone.yml").unlink()

        self.bin = self.root / "bin"
        self.bin.mkdir()
        stub = self.bin / "gh"
        stub.write_text(GH_STUB, encoding="utf-8")
        stub.chmod(0o755)

        self.log = self.root / "gh.log"
        self.request = self.root / "request.json"
        self.message = self.root / "message"
        self.message.write_text(
            "ci(workflows): take the shared workflows at v1.0.9\n\nWhy.\n\nSpec: OPS-R85\n",
            encoding="utf-8",
        )

    def run_main(self, **env) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        settings = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.log),
            "GH_REQUEST": str(self.request),
            "GH_OID": OID,
            **env,
        }
        with mock.patch.dict(os.environ, settings), redirect_stdout(out), redirect_stderr(err):
            code = signed_pin_commit.main([
                "--repo", str(self.repo), "--slug", "lemonfiber/alpha",
                "--branch", "ci/take-the-shared-workflows", "--message", str(self.message),
            ])
        return code, out.getvalue(), err.getvalue()

    def calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines()

    def test_a_new_branch_is_made_at_the_commit_by_way_of_staging(self):
        code, out, _ = self.run_main()

        self.assertEqual((code, out.strip()), (0, OID))
        calls = self.calls()
        self.assertIn(
            "api --method POST repos/lemonfiber/alpha/git/refs "
            f"-f ref=refs/heads/ci/take-the-shared-workflows-staging -f sha={self.base}",
            calls,
        )
        self.assertIn(
            "api --method POST repos/lemonfiber/alpha/git/refs "
            f"-f ref=refs/heads/ci/take-the-shared-workflows -f sha={OID}",
            calls,
        )
        self.assertEqual(
            calls[-1],
            "api --method DELETE repos/lemonfiber/alpha/git/refs/heads/ci/take-the-shared-workflows-staging",
        )

    def test_an_existing_branch_is_moved_forced_and_never_to_main(self):
        code, _, _ = self.run_main(
            GH_EXISTS="ci/take-the-shared-workflows ci/take-the-shared-workflows-staging"
        )

        self.assertEqual(code, 0)
        calls = self.calls()
        self.assertIn(
            "api --method PATCH repos/lemonfiber/alpha/git/refs/heads/ci/take-the-shared-workflows "
            f"-f sha={OID} -F force=true",
            calls,
        )
        self.assertNotIn(
            "api --method PATCH repos/lemonfiber/alpha/git/refs/heads/ci/take-the-shared-workflows "
            f"-f sha={self.base} -F force=true",
            calls,
        )

    def test_the_commit_carries_what_the_working_tree_changed(self):
        self.run_main()

        sent = json.loads(self.request.read_text(encoding="utf-8"))["variables"]["input"]
        self.assertEqual(
            sent["branch"],
            {"repositoryNameWithOwner": "lemonfiber/alpha",
             "branchName": "ci/take-the-shared-workflows-staging"},
        )
        self.assertEqual(sent["expectedHeadOid"], self.base)
        self.assertEqual(
            sent["message"],
            {"headline": "ci(workflows): take the shared workflows at v1.0.9",
             "body": "Why.\n\nSpec: OPS-R85"},
        )
        self.assertEqual(
            sent["fileChanges"]["additions"],
            [{"path": ".github/workflows/ci.yml",
              "contents": base64.b64encode(b"new\n").decode()}],
        )
        self.assertEqual(sent["fileChanges"]["deletions"], [{"path": ".github/workflows/gone.yml"}])

    def test_a_staging_branch_that_will_not_place_refuses_before_any_commit(self):
        code, out, err = self.run_main(GH_REF_FAILS="ref=refs/heads/ci/take-the-shared-workflows-staging")

        self.assertEqual((code, out), (1, ""))
        self.assertIn("ci/take-the-shared-workflows-staging could not be placed", err)
        self.assertIn("ref refused", err)
        self.assertFalse(any("graphql" in call for call in self.calls()))

    def test_a_commit_github_will_not_make_refuses(self):
        code, _, err = self.run_main(GH_COMMIT_FAILS="1")

        self.assertEqual(code, 1)
        self.assertIn("the commit was not made: graphql said no", err)

    def test_an_answer_that_is_not_a_commit_refuses(self):
        code, _, err = self.run_main(GH_OID="")

        self.assertEqual(code, 1)
        self.assertIn("the commit was not made: no answer", err)

    def test_a_branch_that_will_not_move_refuses(self):
        code, _, err = self.run_main(GH_REF_FAILS=f"sha={OID}")

        self.assertEqual(code, 1)
        self.assertIn(f"ci/take-the-shared-workflows could not be moved to {OID}: ref refused", err)

    def test_a_staging_branch_left_behind_is_said_and_does_not_refuse(self):
        code, out, err = self.run_main(GH_DELETE_FAILS="1")

        self.assertEqual((code, out.strip()), (0, OID))
        self.assertIn("ci/take-the-shared-workflows-staging could not be removed", err)

    def test_a_refusal_with_nothing_said_still_says_refused(self):
        with mock.patch.object(
            signed_pin_commit, "gh",
            return_value=subprocess.CompletedProcess([], 1, stdout="", stderr=""),
        ):
            self.assertEqual(signed_pin_commit.place("o/r", "b", OID), "refused")


if __name__ == "__main__":
    unittest.main(verbosity=2)
