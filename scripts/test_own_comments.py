#!/usr/bin/env python3
"""A workflow edits and removes only the comments its own token wrote.

Each sticky comment a workflow keeps on a pull request starts with a marker, an
HTML comment such as `<!-- pr-cap -->`. Anyone can write that marker into a
comment of their own, and a reply quoting the sticky comment carries it too. A
lookup by the marker alone then hands the workflow somebody else's comment: it
rewrites that comment under its author's name, deletes it as stale, or posts
nothing of its own. So a comment is the workflow's by its author, the account
its token writes as, and by its marker.

Driven as `test_milestone.py` drives a step: each step's script is read out of
the committed YAML, `gh` is a stub on a PATH prefix that records every call and
answers a comment listing by running the step's own `--jq` filter over a chosen
set of comments, and each case is judged by the calls the step made.

Stdlib unittest plus PyYAML, and `jq`, which the stub filters with.
Run:  python3 scripts/test_own_comments.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / ".github" / "workflows"

#: The account a workflow's own token writes as.
SELF = "github-actions[bot]"

GH_STUB = """#!/bin/sh
# Stand in for `gh`: record the call; answer a comment listing with the step's
# own --jq filter over $COMMENTS; answer anything else with nothing.
set -eu
printf '%s\\n' "$*" >> "$GH_LOG"
filter=""
previous=""
listing=""
for word in "$@"; do
  [ "$previous" = "--jq" ] && filter="$word"
  case "$word" in */comments) listing=yes ;; esac
  previous="$word"
done
case "$*" in
*"-X "* | *"--method "*) exit 0 ;;
esac
if [ -n "$listing" ] && [ -n "$filter" ]; then
  jq -r "$filter" "$COMMENTS"
fi
"""

#: Each step that keeps a sticky comment: workflow, job, step name, its marker,
#: and whether a lookup keeps the newest of its comments (else the oldest).
STICKY = {
    "explain": ("explain-check.yml", "explain", "Post the explainer", "<!-- explain:dco -->", True),
    "refs": ("spec-references.yml", "comment", "Upsert the sticky comment", "<!-- spec-references -->", False),
    "cap": ("pr-cap.yml", "comment", "Upsert or remove the sticky comment", "<!-- pr-cap -->", False),
}


def step(workflow: str, job: str, name: str) -> dict:
    read = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    for one in read["jobs"][job]["steps"]:
        if one.get("name") == name:
            return one
    raise AssertionError(f"no step {name!r} in {workflow} job {job!r}")


def comment(number: int, login: str, body: str) -> dict:
    return {"id": number, "user": {"login": login}, "body": body}


class Sticky(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        stub = self.bin / "gh"
        stub.write_text(GH_STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.log = self.tmp / "gh.log"

    def run_step(self, which: str, comments: list[dict], *, say: str = "the comment", needed: str = "true"):
        workflow, job, name, _, _ = STICKY[which]
        found = step(workflow, job, name)
        self.assertEqual(found["env"].get("SELF"), SELF, f"{workflow} names the account it writes as")
        (self.tmp / "comments.json").write_text(json.dumps(comments), encoding="utf-8")
        (self.tmp / "comment.md").write_text(say, encoding="utf-8")
        self.log.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.log),
            "COMMENTS": str(self.tmp / "comments.json"),
            "GITHUB_REPOSITORY": "lemonfiber/core",
            "GH_REPO": "lemonfiber/core",
            "PR": "7",
            "CHECK": "dco",
            "TITLE": "Sign-off",
            "BODY": "How to sign off.",
            "NEEDED": needed,
            "SELF": SELF,
        }
        done = subprocess.run(["bash", "-c", found["run"]], cwd=self.tmp, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return [line for line in self.log.read_text(encoding="utf-8").splitlines()
                if re.search(r"-X (PATCH|DELETE|POST)", line)]

    def test_a_strangers_comment_with_the_marker_is_never_edited(self):
        for which, (_, _, _, marker, _) in STICKY.items():
            with self.subTest(which):
                writes = self.run_step(which, [comment(11, "someone", f"{marker}\nmine now")])
                self.assertEqual(len(writes), 1, writes)
                self.assertIn("-X POST", writes[0])
                self.assertIn("issues/7/comments", writes[0])

    def test_its_own_comment_is_edited_and_the_strangers_left(self):
        for which, (_, _, _, marker, _) in STICKY.items():
            with self.subTest(which):
                writes = self.run_step(which, [
                    comment(11, "someone", f"{marker}\nmine now"),
                    comment(12, SELF, f"{marker}\nthe old one"),
                    comment(13, "someone", f"> {marker}\n> quoted in a reply"),
                ])
                self.assertEqual(len(writes), 1, writes)
                self.assertIn("-X PATCH", writes[0])
                self.assertIn("issues/comments/12", writes[0])

    def test_a_reply_quoting_the_marker_is_not_the_comment(self):
        # Its own comment wrote something else; a reply quotes the marker.
        for which, (_, _, _, marker, _) in STICKY.items():
            with self.subTest(which):
                writes = self.run_step(which, [comment(14, SELF, f"Thanks.\n> {marker}")])
                self.assertEqual([w for w in writes if "comments/14" in w], [], writes)

    def test_one_of_two_of_its_own_comments_is_chosen(self):
        for which, (_, _, _, marker, newest) in STICKY.items():
            with self.subTest(which):
                writes = self.run_step(which, [comment(21, SELF, f"{marker}\na"), comment(22, SELF, f"{marker}\nb")])
                self.assertEqual(len(writes), 1, writes)
                self.assertIn(f"issues/comments/{22 if newest else 21}", writes[0])

    def test_nothing_left_to_say_removes_only_its_own(self):
        marker = STICKY["explain"][3]
        stranger = [comment(11, "someone", f"{marker}\nmine now")]
        self.assertEqual(self.run_step("explain", stranger, needed="false"), [])
        self.assertEqual(self.run_step("cap", [comment(11, "someone", "<!-- pr-cap -->\nx")], say=""), [])
        own = self.run_step("cap", [comment(11, "someone", "<!-- pr-cap -->\nx"),
                                    comment(12, SELF, "<!-- pr-cap -->\ny")], say="")
        self.assertEqual(len(own), 1, own)
        self.assertIn("-X DELETE", own[0])
        self.assertIn("issues/comments/12", own[0])


class EveryLookup(unittest.TestCase):
    """Every lookup of a comment by what it says asks who wrote it, in every workflow."""

    def test_a_lookup_by_body_asks_for_the_author(self):
        seen = 0
        for path in sorted(WORKFLOWS.glob("*.yml")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\.body \| (startswith|contains|test)\(", line):
                    seen += 1
                    self.assertIn(".user.login == env.SELF", line, f"{path.name}:{number}")
        self.assertGreaterEqual(seen, 6, "the lookups were found")

    def test_each_step_that_looks_names_the_account_it_writes_as(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            read = yaml.safe_load(path.read_text(encoding="utf-8"))
            for job_name, job in (read.get("jobs") or {}).items():
                for one in job.get("steps") or []:
                    if "env.SELF" in str(one.get("run", "")):
                        with self.subTest(f"{path.name} {job_name} {one.get('name')}"):
                            self.assertEqual((one.get("env") or {}).get("SELF"), SELF)


if __name__ == "__main__":
    unittest.main()
