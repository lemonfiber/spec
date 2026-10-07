#!/usr/bin/env python3
"""The board snapshot holds what the frontpage renders, in the documented shape —
OPS-R80.

Built on the same fixture as the report's suite: real git repositories in a
temporary directory, a spec tree with two manifests, and two repositories a
version is satisfied in. To that it adds what only the board reads: a feature
with its frontmatter and its requirements, an area heading, a document of
another namespace with a superseded row, the repository map, the core's
changelog, the open pull requests and the `rfc` issues. Then each field is read
back, a repository that cannot be read is named while the rest is written, the
content hash ignores the time, and an input that cannot be read stops the run.

Stdlib unittest.
Run:  python3 scripts/test_board.py
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import board  # noqa: E402
from test_goals import Train  # noqa: E402

FEATURE = """---
id: A1
title: First run
kind: feature
area: A
audience: operator
status: accepted
maturity: building
labels: [ux]
---

# A1 — First run

| ID | Requirement |
|----|-------------|
| **A1-R1** | The tool MUST start. |
| **A1-R2** | The tool SHOULD greet. |
| **A1-R3** | The tool MAY wave. |
| **A1-R4** | It is quiet. |
| **A1-R5** | *Withdrawn: nobody asked for it. The number is not reused.* |
| **A1-R9** | The tool MUST stop. |
"""

DRAFT = """---
id: A2
title: Second run
kind: feature
area: A
audience: both
status: draft
maturity: planned
---

| ID | Requirement |
|----|-------------|
| **A2-R1** | The tool MUST remember. |
"""

DOC = """# Rules

| ID | Requirement |
|----|-------------|
| **GOV-R1** | *Superseded by [GOV-R2](rules.md): the rule moved. The number is not reused.* |
| **GOV-R2** | A rule MUST be kept. |
"""

REPOS = """[[repo]]
name = "spec"
group = "root"
spec = ["../README.md"]
lang = "Markdown"
note = "canonical"

[[repo]]
name = "core"
group = "impl"
spec = ["core.md"]
lang = "Rust"
note = "the binary"

[[ungoverned]]
name = "plugin-x"
note = "a plugin"
"""

RELEASE = {"version": "0.1.0", "tag": "v0.1.0", "released_on": "2026-01-01",
           "delivers": "The first run",
           "groups": [{"title": "New", "entries": [
               {"summary": "It starts", "requirements": ["A1-R1"], "reference": "#1"},
               {"summary": "It stops", "requirements": ["A1-R9"]}]}]}


def run_main(argv):
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["board.py", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = board.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Board(Train):
    def setUp(self):
        super().setUp()
        features = pathlib.Path("10-functional/features")
        (features / "a-start").mkdir(parents=True)
        (features / "README.md").write_text("# Features\n\n## A — Getting started\n",
                                            encoding="utf-8")
        (features / "a-start" / "a1-first-run.md").write_text(FEATURE, encoding="utf-8")
        (features / "a-start" / "a2-second-run.md").write_text(DRAFT, encoding="utf-8")
        pathlib.Path("50-governance").mkdir()
        pathlib.Path("50-governance/rules.md").write_text(DOC, encoding="utf-8")
        pathlib.Path(".claude").mkdir()
        pathlib.Path(".claude/notes.md").write_text(DOC.replace("GOV", "Q"), encoding="utf-8")
        pathlib.Path("30-repos").mkdir()
        pathlib.Path("30-repos/repos.toml").write_text(REPOS, encoding="utf-8")
        self.repo("lemonfiber", "Spec: GOV-R12")
        pathlib.Path("lemonfiber/reference/changelog").mkdir(parents=True)
        self.commit("lemonfiber", "reference/changelog/0.1.0.json", json.dumps(RELEASE))
        self.commit("lemonfiber", "reference/changelog/0.0.9.json",
                    json.dumps({"version": "0.0.9", "groups": None}))
        self.commit("lemonfiber", "reference/changelog/README.md", "not a release")
        self.commit("core", "status.toml",
                    '[[requirement]]\nid = "A1-R1"\nstate = "done"\nevidence = ["README"]\n'
                    'landed = "abc1234"\n')

    def checkouts(self):
        return [*super().checkouts(), "--checkout", "lemonfiber=lemonfiber"]

    def snapshot(self, *extra):
        code, said = run_main([*self.checkouts(), "--json", "board.json", *extra])
        self.assertEqual(code, 0, said)
        return json.loads(pathlib.Path("board.json").read_text(encoding="utf-8")), said


class TheShape(Board):
    def test_every_documented_field_is_there(self):
        data, said = self.snapshot()
        self.assertEqual(said, "")
        self.assertEqual(data["format"], board.FORMAT)
        self.assertEqual(list(data), ["format", "generated_at", "ref", "sources", "unread",
                                      "areas", "features", "requirements", "versions",
                                      "trackers", "pulls", "repos", "releases", "proposals"])
        self.assertEqual(data["unread"], [])
        self.assertEqual(set(data["sources"]), {"spec", "core", "app", "lemonfiber"})

    def test_areas_are_named_by_the_catalogue(self):
        data, _ = self.snapshot()
        self.assertEqual(data["areas"],
                         [{"id": "A", "name": "Getting started", "directory": "a-start"}])

    def test_features_are_the_boards_rows(self):
        data, _ = self.snapshot()
        first = data["features"][0]
        self.assertEqual((first["id"], first["maturity"], first["labels"]),
                         ("A1", "building", ["ux"]))
        self.assertEqual([v["version"] for v in first["versions"]], ["0.1.0", "0.2.0"])

    def test_every_requirement_with_its_text_and_status(self):
        data, _ = self.snapshot()
        found = {r["id"]: r for r in data["requirements"]}
        self.assertEqual(found["A1-R1"]["text"], "The tool MUST start.")
        self.assertEqual(found["A1-R1"]["owner"], "A1")
        self.assertEqual(found["A1-R1"]["namespace"], "feature")
        self.assertEqual(found["A1-R1"]["versions"], ["0.2.0"])
        self.assertEqual([found[i]["keyword"] for i in ("A1-R1", "A1-R2", "A1-R3", "A1-R4")],
                         ["MUST", "SHOULD", "MAY", None])
        self.assertEqual(found["A1-R5"]["status"], "withdrawn")
        self.assertIsNone(found["A1-R5"]["replaced_by"])
        self.assertEqual(found["A2-R1"]["status"], "draft")
        self.assertEqual(found["GOV-R1"]["status"], "superseded")
        self.assertEqual(found["GOV-R1"]["replaced_by"], "GOV-R2")
        self.assertEqual(found["GOV-R1"]["owner"], "50-governance/rules.md")
        self.assertEqual(found["GOV-R2"]["namespace"], "GOV")
        self.assertEqual(found["GOV-R2"]["status"], "accepted")
        self.assertNotIn("Q-R2", found, "a tree this repository did not write is not read")

    def test_versions_carry_each_goal_and_its_verdict(self):
        data, _ = self.snapshot()
        planned = data["versions"][1]
        self.assertEqual((planned["version"], planned["status"]), ("0.2.0", "planned"))
        self.assertEqual(planned["satisfied_in"], ["core", "app"])
        self.assertEqual(planned["prereleases"], [])
        verdicts = {g["id"]: g["verdict"] for g in planned["goals"]}
        self.assertEqual(verdicts["A1-R1"], "met")

    def test_trackers_hold_their_rows(self):
        data, _ = self.snapshot()
        core = next(t for t in data["trackers"] if t["repo"] == "core")
        self.assertEqual(core, {"repo": "core", "present": True, "rows": [
            {"id": "A1-R1", "state": "done", "evidence": ["README"], "landed": "abc1234"}]})

    def test_every_repository_with_its_tracker(self):
        data, _ = self.snapshot()
        self.assertEqual([(r["name"], r["group"], r["tracker"]) for r in data["repos"]],
                         [("spec", "root", None), ("core", "impl", "present"),
                          ("plugin-x", "ungoverned", None)])
        self.assertEqual(data["repos"][1]["pages"], ["core.md"])

    def test_releases_from_the_changelog_in_version_order(self):
        data, _ = self.snapshot()
        self.assertEqual([r["version"] for r in data["releases"]], ["0.0.9", "0.1.0"])
        self.assertEqual(data["releases"][0]["groups"], [])
        entries = data["releases"][1]["groups"][0]["entries"]
        self.assertEqual(entries[0], {"summary": "It starts", "requirements": ["A1-R1"],
                                      "reference": "#1"})
        self.assertIsNone(entries[1]["reference"])

    def test_no_core_checkout_means_no_releases(self):
        code, said = run_main([*Train.checkouts(self), "--json", "board.json"])
        self.assertEqual(code, 0, said)
        data = json.loads(pathlib.Path("board.json").read_text(encoding="utf-8"))
        self.assertEqual(data["releases"], [])


class PullsAndProposals(Board):
    def test_pull_requests_with_what_they_cite(self):
        prs = {"app": [
            {"number": 7, "url": "https://x/7", "title": "feat: greet", "isDraft": True,
             "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-02T00:00:00Z",
             "headRefName": "feat/greet", "author": {"login": "someone", "__typename": "User"},
             "body": "Spec: A1-R2", "commits": [{"message": "feat: x\n\nSpec: A1-R10, A1-R3"}]},
            {"number": 8, "url": "https://x/8", "author": {"login": "dependabot",
                                                          "__typename": "Bot"},
             "body": None, "commits": None}]}
        pathlib.Path("prs.json").write_text(json.dumps(prs), encoding="utf-8")
        data, _ = self.snapshot("--prs", "prs.json")
        first, second = data["pulls"]
        self.assertEqual(first["cites"], ["A1-R2", "A1-R3", "A1-R10"])
        self.assertEqual((first["author"], first["bot"], first["draft"], first["head"]),
                         ("someone", False, True, "feat/greet"))
        self.assertEqual(first["created_at"], "2026-01-01T00:00:00Z")
        self.assertEqual((second["author"], second["bot"], second["cites"]),
                         ("dependabot", True, []))

    def test_pull_requests_are_counted_per_repository(self):
        prs = {"core": [{"number": 1, "url": "https://x/1", "body": ""}]}
        pathlib.Path("prs.json").write_text(json.dumps(prs), encoding="utf-8")
        data, _ = self.snapshot("--prs", "prs.json")
        self.assertEqual([r["open_pulls"] for r in data["repos"]], [0, 1, 0])
        self.assertIsNone(data["pulls"][0]["author"])

    def test_the_pre_approval_feed(self):
        issues = [{"number": 4, "title": "RFC: a thing", "html_url": "https://x/i/4"},
                  {"number": 5, "title": "a pull request", "html_url": "https://x/p/5",
                   "pull_request": {}}]
        pathlib.Path("issues.json").write_text(json.dumps(issues), encoding="utf-8")
        data, _ = self.snapshot("--issues", "issues.json")
        self.assertEqual(data["proposals"], [
            {"kind": "feature", "id": "A2", "title": "Second run", "url": None},
            {"kind": "requirement", "id": "A2-R1", "title": "The tool MUST remember.",
             "url": None},
            {"kind": "rfc", "id": 4, "title": "RFC: a thing", "url": "https://x/i/4"}])


class WhatCouldNotBeRead(Board):
    def test_a_repository_it_cannot_read_is_named_and_the_rest_written(self):
        self.git("app", "rm", "-q", "status.toml")
        self.git("app", "commit", "-q", "-m", "chore: gone", "-m", "Spec: GOV-R12")
        data, said = self.snapshot()
        self.assertIn("::warning::app was not read", said)
        self.assertEqual([u["repo"] for u in data["unread"]], ["app"])
        app = next(t for t in data["trackers"] if t["repo"] == "app")
        self.assertEqual(app, {"repo": "app", "present": False, "rows": []})
        self.assertEqual(len(data["requirements"]), 9, "the rest is still written")

    def test_a_repository_in_the_map_it_cannot_read(self):
        self.commit("core", "status.toml", "[[requirement]\n")
        data, _ = self.snapshot()
        self.assertEqual(data["repos"][1]["tracker"], "unread")

    def test_the_core_unread_gives_no_releases(self):
        code, said = run_main([*self.checkouts(), "--json", "board.json", "--ref", "nowhere"])
        self.assertEqual(code, 0, said)
        data = json.loads(pathlib.Path("board.json").read_text(encoding="utf-8"))
        self.assertEqual(data["releases"], [])

    def test_a_changelog_entry_that_is_not_json(self):
        self.commit("lemonfiber", "reference/changelog/0.2.0.json", "{")
        code, said = run_main([*self.checkouts(), "--json", "board.json"])
        self.assertEqual(code, 2)
        self.assertIn("reference/changelog/0.2.0.json is not JSON", said)

    def test_an_issues_file_that_is_not_json(self):
        pathlib.Path("issues.json").write_text("[", encoding="utf-8")
        code, said = run_main([*self.checkouts(), "--json", "board.json",
                               "--issues", "issues.json"])
        self.assertEqual(code, 2)
        self.assertIn("::error::", said)
        self.assertFalse(pathlib.Path("board.json").exists())


class TheHash(Board):
    def test_the_hash_ignores_when_it_was_written(self):
        data, _ = self.snapshot("--hash", "board.sha256")
        written = pathlib.Path("board.sha256").read_text(encoding="utf-8").strip()
        self.assertEqual(written, board.content_hash(data))
        self.assertEqual(board.content_hash({**data, "generated_at": "1970-01-01T00:00:00Z"}),
                         written)
        self.assertNotEqual(board.content_hash({**data, "ref": "elsewhere"}), written)

    def test_changed_against_what_was_published(self):
        self.snapshot("--hash", "board.sha256")
        same = pathlib.Path("board.sha256").read_text(encoding="utf-8")
        pathlib.Path("published.sha256").write_text(same, encoding="utf-8")
        self.snapshot("--previous", "published.sha256", "--changed", "changed.txt")
        self.assertEqual(pathlib.Path("changed.txt").read_text(encoding="utf-8"), "false\n",
                         "a run over the same sources asks for no rebuild")
        pathlib.Path("published.sha256").write_text("0" * 64 + "\n", encoding="utf-8")
        self.snapshot("--previous", "published.sha256", "--changed", "changed.txt")
        self.assertEqual(pathlib.Path("changed.txt").read_text(encoding="utf-8"), "true\n")

    def test_nothing_published_before_is_a_change(self):
        self.snapshot("--previous", "absent.sha256", "--changed", "changed.txt")
        self.assertEqual(pathlib.Path("changed.txt").read_text(encoding="utf-8"), "true\n")
        self.snapshot("--changed", "changed.txt")
        self.assertEqual(pathlib.Path("changed.txt").read_text(encoding="utf-8"), "true\n")
        self.assertTrue(board.changed(None, "x"))
        self.assertFalse(board.changed("x\n", "x"))


if __name__ == "__main__":
    unittest.main()
