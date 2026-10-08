#!/usr/bin/env python3
"""Turning an RFC issue into a proposal pull request — GOV-R40, GOV-R43.

The proposal written from an issue is held to the shape `integrity.py` checks,
its untrusted fields stay text, and the forge is a fake that records each call.

Stdlib unittest.
Run:  python3 scripts/test_rfc_convert.py
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import integrity  # noqa: E402
import rfc_convert as convert  # noqa: E402

BODY = """### Area

B — Running it

### Proposal title

Scheduled scans

### The problem

Scans run only by hand.
## Rationale
# not a heading of mine

### Proposed behaviour

- The tool MUST scan nightly.
The tool SHOULD say when it last scanned.

### Rationale & alternatives

_No response_
"""

ENV = {"ISSUE_BODY": BODY, "ISSUE_NUMBER": "42", "ISSUE_TITLE": "RFC: Scheduled scans",
       "ISSUE_URL": "https://github.com/lemonfiber/spec/issues/42", "ISSUE_AUTHOR": "someone",
       "REPO": "lemonfiber/spec"}
AREAS = {"A", "B"}


class Render(unittest.TestCase):
    def test_a_proposal_in_the_shape_integrity_checks(self):
        proposal = convert.render(ENV, AREAS)
        self.assertEqual((proposal.number, proposal.title, proposal.path),
                         ("42", "Scheduled scans", "10-functional/proposals/rfc-42.md"))
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp, "rfc-42.md")
            path.write_text(proposal.text, encoding="utf-8")
            self.assertEqual(integrity.proposal_faults(path, AREAS), [])

    def test_the_fields_stay_text(self):
        text = convert.render(ENV, AREAS).text
        self.assertIn("\\## Rationale", text)
        self.assertIn("\\# not a heading of mine", text)
        self.assertIn("- The tool MUST scan nightly.\n- The tool SHOULD say when it last scanned.", text)
        self.assertIn("## Rationale\n\n(none given)", text)
        self.assertIn("opened by @someone", text)

    def test_the_issue_title_where_the_form_gave_none(self):
        env = {**ENV, "ISSUE_BODY": BODY.replace("Scheduled scans\n", "\n"), "ISSUE_TITLE": "RFC: It's here"}
        proposal = convert.render(env, AREAS)
        self.assertEqual(proposal.title, "It's here")
        self.assertIn("title: 'It''s here'", proposal.text)

    def test_refused(self):
        cases = {
            "number": ({**ENV, "ISSUE_NUMBER": "4/2"}, "not a number"),
            "area": ({**ENV, "ISSUE_BODY": BODY.replace("B — Running it", "Z — Nowhere")}, "the area"),
            "title": ({**ENV, "ISSUE_BODY": BODY.replace("Scheduled scans\n", "\n"), "ISSUE_TITLE": "RFC:"},
                      "no title"),
        }
        for why, (env, said) in cases.items():
            with self.subTest(why), self.assertRaisesRegex(convert.Refused, said):
                convert.render(env, AREAS)

    def test_fields_and_nothing_given(self):
        self.assertEqual(convert.field("### A\n\nx\n", "B"), "")
        self.assertEqual(convert.statements(""), "- (none given)")
        self.assertEqual(convert.text(""), "(none given)")


class Forge:
    def __init__(self):
        self.calls = []

    def __call__(self, args, request):
        self.calls.append((args, request))
        if args[0].endswith("git/ref/heads/main"):
            return {"object": {"sha": "base"}}
        if args[0].endswith("/pulls"):
            return {"html_url": "https://github.com/lemonfiber/spec/pull/700"}
        return {}


class Open(unittest.TestCase):
    def test_a_signed_commit_on_its_own_branch_and_the_pull_request(self):
        forge = Forge()
        url = convert.open_proposal(ENV, convert.render(ENV, AREAS), forge)
        self.assertEqual(url, "https://github.com/lemonfiber/spec/pull/700")
        (_, _), (_, ref), (_, commit), (_, pull), (comment_args, comment) = forge.calls
        self.assertEqual(ref, {"ref": "refs/heads/proposal/rfc-42", "sha": "base"})
        change = commit["variables"]["input"]
        self.assertEqual(change["expectedHeadOid"], "base")
        added = change["fileChanges"]["additions"][0]
        self.assertEqual(added["path"], "10-functional/proposals/rfc-42.md")
        self.assertIn("kind: proposal", base64.b64decode(added["contents"]).decode())
        self.assertIn("Spec: GOV-R40", change["message"]["body"])
        self.assertEqual(pull["title"], "Proposal: Scheduled scans")
        self.assertIn("Closes #42", pull["body"])
        self.assertTrue(pull["maintainer_can_modify"])
        self.assertEqual(comment_args, ["repos/lemonfiber/spec/issues/42/comments"])
        self.assertIn("pull/700", comment["body"])


class Main(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        catalogue = pathlib.Path("10-functional/features/README.md")
        catalogue.parent.mkdir(parents=True)
        catalogue.write_text("## B — Running it\n", encoding="utf-8")

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, env, api):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = convert.main(env, api)
        return code, out.getvalue()

    def test_opens_the_proposal(self):
        code, said = self.run_main(ENV, Forge())
        self.assertEqual(code, 0)
        self.assertIn("opened https://github.com/lemonfiber/spec/pull/700 with 10-functional/proposals/rfc-42.md",
                      said)

    def test_refused_and_broken(self):
        self.assertEqual(self.run_main({**ENV, "ISSUE_NUMBER": "x"}, Forge())[0], 1)

        def down(args, request):
            raise subprocess.CalledProcessError(1, "gh")

        self.assertEqual(self.run_main(ENV, down)[0], 2)


class Gh(unittest.TestCase):
    def test_a_request_on_standard_input(self):
        done = mock.Mock(stdout='{"ok": 1}')
        with mock.patch("subprocess.run", return_value=done) as ran:
            self.assertEqual(convert.gh(["repos/x"], {"a": 1}), {"ok": 1})
        self.assertEqual(ran.call_args.args[0], ["gh", "api", "repos/x", "--input", "-"])
        self.assertEqual(json.loads(ran.call_args.kwargs["input"]), {"a": 1})
        with mock.patch("subprocess.run", return_value=mock.Mock(stdout="")) as ran:
            self.assertEqual(convert.gh(["repos/x"]), {})
        self.assertIsNone(ran.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
