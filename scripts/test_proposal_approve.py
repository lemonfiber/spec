#!/usr/bin/env python3
"""Approving a proposal: identifiers allocated, rows written as Draft, the
proposal moved where it belongs — and the refusals (GOV-R41, GOV-R42, GOV-R43).

Stdlib unittest.
Run:  python3 scripts/test_proposal_approve.py
"""

from __future__ import annotations

import base64
import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import integrity  # noqa: E402
import proposal_approve as approve  # noqa: E402

FEATURE = """---
id: B1
title: Forms
kind: feature
area: B
audience: operator
status: accepted
maturity: building
---

# B1 — Forms

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **B1-R1** | The tool MUST start. |
| **B1-R2** | The tool MUST stop. |

## Related

- nothing
"""

PAGE = """# Rules

**Status:** Accepted

| ID | Requirement |
|----|-------------|
| **GOV-R1** | A rule MUST hold. |
"""

CATALOGUE = """# Features

## B — Running it

| ID | Feature | Audience |
|----|---------|----------|
| [B1](b-running/b1-forms.md) | Forms | Operator |

## Traceability
"""

PROPOSAL = """---
kind: proposal
area: B
title: Scheduled scans
{amends}status: draft
---

# Scheduled scans

## Problem

Libraries go stale.

## Proposed behaviour

- The tool MUST scan every night.
- The tool SHOULD say when it | last scanned.

## Rationale

Because.
"""

GAP = """---
kind: gap
area: B
title: Silence on scans
amends: B1
status: draft
---

# Silence on scans

## What the specification does not say

When scans run.
"""

FAMILIES = {"B1": {1: "x", 2: "x", 7: "(origin/other)"}, "GOV": {1: "x"}, "B4": {1: "x"}}


class Tree(unittest.TestCase):
    """A spec checkout with one feature, one page and the catalogue."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        running = self.root / "10-functional" / "features" / "b-running"
        running.mkdir(parents=True)
        (running / "b1-forms.md").write_text(FEATURE, encoding="utf-8")
        (self.root / "10-functional" / "features" / "README.md").write_text(CATALOGUE, encoding="utf-8")
        (self.root / "10-functional" / "proposals").mkdir()
        (self.root / "50-governance").mkdir()
        (self.root / "50-governance" / "rules.md").write_text(PAGE, encoding="utf-8")
        was = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, was)
        for target, name, value in ((integrity, "ROOT", self.root),
                                    (approve.next_id, "defined", lambda: FAMILIES)):
            patch = mock.patch.object(target, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def plan(self, text, name="scans.md"):
        return approve.plan(self.root, name, text)


class Amending(Tree):
    def test_a_feature_gains_draft_rows_after_every_identifier_on_any_branch(self):
        made = self.plan(PROPOSAL.format(amends="amends: B1\n"))
        self.assertEqual(made.identifiers, ["B1-R8", "B1-R9"])
        self.assertEqual(made.where, "10-functional/features/b-running/b1-forms.md")
        text = made.writes[made.where]
        self.assertIn("| **B1-R2** | The tool MUST stop. |\n"
                      "| **B1-R8** | *Draft:* The tool MUST scan every night. |\n"
                      "| **B1-R9** | *Draft:* The tool SHOULD say when it \\| last scanned. |\n\n"
                      "## Related", text)
        self.assertEqual(made.removes, ["10-functional/proposals/scans.md"])

    def test_a_page_takes_its_one_prefix(self):
        made = self.plan(PROPOSAL.format(amends="amends: 50-governance/rules.md\n"))
        self.assertEqual(made.identifiers, ["GOV-R2", "GOV-R3"])
        self.assertTrue(made.writes["50-governance/rules.md"].endswith(
            "| **GOV-R3** | *Draft:* The tool SHOULD say when it \\| last scanned. |\n"))

    def test_a_page_outside_the_specification_is_refused(self):
        (self.root.parent / "outside.md").write_text(PAGE, encoding="utf-8")
        self.addCleanup((self.root.parent / "outside.md").unlink)
        for amends in ("../outside.md", "50-governance"):
            with self.subTest(amends=amends), self.assertRaisesRegex(approve.Refused, "not a page"):
                approve.amendment(self.root, amends, ["x"], FAMILIES)

    def test_a_page_with_two_prefixes_or_no_table_is_refused(self):
        proposal = PROPOSAL.format(amends="amends: 50-governance/rules.md\n")
        (self.root / "50-governance" / "rules.md").write_text(PAGE + "| **Q-R1** | Also. |\n", encoding="utf-8")
        with self.assertRaisesRegex(approve.Refused, "defines 2 identifier prefixes"):
            self.plan(proposal)
        (self.root / "50-governance" / "rules.md").write_text("# Rules\n\n| **GOV-R1** | x |\n", encoding="utf-8")
        with self.assertRaisesRegex(approve.Refused, "no requirements table"):
            self.plan(proposal)


class NewFeature(Tree):
    def test_a_proposal_amending_nothing_becomes_a_draft_feature_in_its_area(self):
        made = self.plan(PROPOSAL.format(amends=""))
        self.assertEqual(made.identifiers, ["B5-R1", "B5-R2"])
        self.assertEqual(made.where, "10-functional/features/b-running/b5-scheduled-scans.md")
        doc = made.writes[made.where]
        self.assertIn("id: B5\ntitle: Scheduled scans\nkind: feature\narea: B\naudience: both\n"
                      "status: draft\nmaturity: planned\n", doc)
        self.assertIn("**Area:** B — Running it", doc)
        self.assertIn("## Purpose\n\nLibraries go stale.", doc)
        self.assertIn("| **B5-R1** | The tool MUST scan every night. |", doc)
        self.assertNotIn("*Draft:*", doc, "the whole feature is Draft")
        self.assertIn("| [B1](b-running/b1-forms.md) | Forms | Operator |\n"
                      "| [B5](b-running/b5-scheduled-scans.md) | Scheduled scans | Both |",
                      made.writes[approve.FEATURES_README])

    def test_the_catalogue_must_have_somewhere_to_list_it(self):
        with self.assertRaisesRegex(approve.Refused, "no section for area C"):
            approve.catalogue_row(CATALOGUE, "C", "C1", "c/c1.md", "x")
        bare = CATALOGUE.replace("| [B1](b-running/b1-forms.md) | Forms | Operator |\n", "")
        with self.assertRaisesRegex(approve.Refused, "lists no feature under area B"):
            approve.catalogue_row(bare, "B", "B5", "b/b5.md", "x")

    def test_a_slug_from_any_title(self):
        self.assertEqual(approve.slug("  Scans, nightly — & more! "), "scans-nightly-more")
        self.assertEqual(approve.slug("!!!"), "feature")


class Refusals(Tree):
    def test_a_gap_is_answered_rather_than_numbered(self):
        with self.assertRaisesRegex(approve.Refused, "a gap names what the specification does not say"):
            self.plan(GAP, "silence.md")

    def test_a_proposal_out_of_shape(self):
        proposal = PROPOSAL.format(amends="amends: Z9\n")
        with self.assertRaisesRegex(approve.Refused, "not in the shape"):
            self.plan(proposal)


class Api:
    """The forge, answered from a table; every call is recorded."""

    def __init__(self, files, head_repo="lemonfiber/spec"):
        self.calls = []
        self.files = files
        self.head_repo = head_repo

    def __call__(self, args, request=None):
        self.calls.append((args[0], request))
        path = args[0]
        if path.endswith("/files?per_page=100"):
            return self.files
        if "/contents/" in path:
            return {"content": base64.b64encode(PROPOSAL.format(amends="amends: B1\n").encode()).decode()}
        if path.endswith("git/ref/heads/main"):
            return {"object": {"sha": "m" * 40}}
        if path.endswith("/pulls"):
            return {"html_url": "https://github.com/lemonfiber/spec/pull/99"}
        return {}


ADDED = [{"filename": "10-functional/proposals/scans.md", "status": "added"}]


def environment(head_repo="lemonfiber/spec"):
    return {"REPO": "lemonfiber/spec", "PR_NUMBER": "42", "PR_TITLE": "Proposal: scans",
            "PR_AUTHOR": "ana", "PR_AUTHOR_ID": "7", "HEAD_REPO": head_repo,
            "HEAD_REF": "proposal/scans", "HEAD_SHA": "h" * 40}


class Main(Tree):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(approve, "write", side_effect=self.written)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch.object(approve, "changed", return_value=(["10-functional/features/b-running/b1-forms.md"], []))
        patch.start()
        self.addCleanup(patch.stop)

    def written(self, root, made):
        for path, text in made.writes.items():
            (root / path).write_text(text, encoding="utf-8")

    def run_main(self, api, env):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = approve.main(env, api, self.root)
        return code, out.getvalue()

    def test_a_branch_here_gets_the_commit_and_a_comment(self):
        api = Api(ADDED)
        code, out = self.run_main(api, environment())
        self.assertEqual(code, 0)
        self.assertIn("approved: B1-R8, B1-R9", out)
        graphql = next(request for path, request in api.calls if path == "graphql")
        change = graphql["variables"]["input"]
        self.assertEqual(change["branch"]["branchName"], "proposal/scans")
        self.assertEqual(change["expectedHeadOid"], "h" * 40)
        self.assertEqual(change["fileChanges"]["deletions"], [{"path": "10-functional/proposals/scans.md"}])
        self.assertIn("Co-authored-by: ana <7+ana@users.noreply.github.com>", change["message"]["body"])
        self.assertIn("Spec: GOV-R42", change["message"]["body"])
        said = api.calls[-1]
        self.assertEqual(said[0], "repos/lemonfiber/spec/issues/42/comments")
        self.assertIn("B1-R8, B1-R9 are allocated", said[1]["body"])

    def test_a_fork_gets_a_pull_request_of_its_own_and_the_original_is_closed(self):
        api = Api(ADDED)
        code, _ = self.run_main(api, environment("ana/spec"))
        self.assertEqual(code, 0)
        paths = [path for path, _ in api.calls]
        self.assertIn("repos/lemonfiber/spec/git/refs", paths)
        graphql = next(request for path, request in api.calls if path == "graphql")
        self.assertEqual(graphql["variables"]["input"]["branch"]["branchName"], "proposal/approved-42")
        self.assertEqual(graphql["variables"]["input"]["fileChanges"]["deletions"], [])
        opened = next(request for path, request in api.calls if path == "repos/lemonfiber/spec/pulls")
        self.assertIn("@ana opened in #42", opened["body"])
        self.assertIn(("repos/lemonfiber/spec/pulls/42", {"state": "closed"}), api.calls)
        self.assertIn("carried by https://github.com/lemonfiber/spec/pull/99", api.calls[-1][1]["body"])

    def test_a_pull_request_changing_more_than_one_proposal_is_refused(self):
        api = Api([*ADDED, {"filename": "README.md", "status": "modified"}])
        code, out = self.run_main(api, environment())
        self.assertEqual(code, 1)
        self.assertIn("::error::a proposal pull request adds one file", out)
        self.assertIn("Not approved as it stands", api.calls[-1][1]["body"])


class Writing(Tree):
    def test_the_plan_lands_and_the_generators_run(self):
        made = approve.Plan(["B1-R8"], "x.md", {"new/x.md": "text\n"})
        with mock.patch.object(approve.subprocess, "run") as ran:
            approve.write(self.root, made)
        self.assertEqual((self.root / "new" / "x.md").read_text(encoding="utf-8"), "text\n")
        self.assertEqual([call.args[0][1:] for call in ran.call_args_list],
                         [["scripts/gen_board.py"], ["scripts/integrity.py", "--write"]])

    def test_what_the_checkout_changed(self):
        done = mock.Mock(stdout=" M a.md\n D b.md\n?? c/d.md\n")
        with mock.patch.object(approve.subprocess, "run", return_value=done):
            self.assertEqual(approve.changed(self.root), (["a.md", "c/d.md"], ["b.md"]))

    def test_gh_takes_its_request_as_a_file(self):
        done = mock.Mock(stdout='{"ok": 1}')
        with mock.patch.object(approve.subprocess, "run", return_value=done) as ran:
            self.assertEqual(approve.gh(["graphql"], {"q": 1}), {"ok": 1})
        self.assertEqual(ran.call_args.args[0], ["gh", "api", "graphql", "--input", "-"])
        self.assertEqual(ran.call_args.kwargs["input"], '{"q": 1}')
        with mock.patch.object(approve.subprocess, "run", return_value=mock.Mock(stdout="")):
            self.assertEqual(approve.gh(["repos/x"]), {})


if __name__ == "__main__":
    unittest.main()
