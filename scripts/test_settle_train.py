#!/usr/bin/env python3
"""The release train merges its pull request only once every check on the head is green — OPS-R87.

Driven through a fake forge: each case says what the head's check runs and
commit statuses are, and what the train then merged, said or left alone.

Stdlib unittest.
Run:  python3 scripts/test_settle_train.py
"""

from __future__ import annotations

import datetime
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settle_train as train  # noqa: E402

REPO = "lemonfiber/sdk-rust"
HEAD = "a" * 40
NOW = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.UTC)
FRESH = "2026-11-20T11:00:00Z"
OLD = "2026-11-20T05:00:00Z"


def run(name, status="completed", conclusion="success", started="2026-11-20T11:10:00Z", ident=1):
    return {"name": name, "status": status, "conclusion": conclusion, "started_at": started, "id": ident}


def status(context, state="success", updated="2026-11-20T11:20:00Z", ident=1):
    return {"context": context, "state": state, "updated_at": updated, "id": ident}


class Forge:
    """One repository's one labelled pull request, and every call made to it."""

    def __init__(self, runs, statuses=(), committed=FRESH, comments=(), marked=True, unreadable=False):
        self.marked = marked
        self.unreadable = unreadable
        self.runs = list(runs)
        self.statuses = list(statuses)
        self.committed = committed
        self.comments = [dict(one) for one in comments]
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method, path, payload):
        self.calls.append((method, path, payload))
        bare = path.split("?", 1)[0]
        if bare == "search/issues":
            found = [{"repository_url": f"https://api.github.com/repos/{REPO}", "number": 45}]
            return {"items": found if self.marked else []}
        if bare == f"repos/{REPO}/pulls/45":
            return {
                "head": {"sha": HEAD},
                "title": "chore(contract): take lemonfiber 5a2ca238",
                "body": "body",
            }
        if bare.endswith("/check-runs"):
            return {"check_runs": self.runs}
        if bare.endswith("/statuses"):
            if self.unreadable:
                raise subprocess.CalledProcessError(
                    1, "gh", stderr="HTTP 403: Resource not accessible by integration"
                )
            return self.statuses
        if bare == f"repos/{REPO}/commits/{HEAD}":
            return {"commit": {"committer": {"date": self.committed}}}
        if bare.endswith("/comments") and method == "GET":
            return self.comments
        return {}

    def merged(self):
        return [
            payload for method, path, payload in self.calls if method == "PUT" and path.endswith("/merge")
        ]

    def written(self):
        return [
            (method, payload["body"])
            for method, path, payload in self.calls
            if "comments" in path and method != "GET"
        ]


def settle(forge):
    return train.main(["--owner", "lemonfiber", "--author", "lemonfiber-release-train"], api=forge, now=NOW)


class Merging(unittest.TestCase):
    def test_a_head_whose_every_check_is_green_merges_at_that_head(self):
        forge = Forge(
            [run("gates"), run("coverage", conclusion="skipped"), run("CodeQL", conclusion="neutral")],
            [status("pin-only / pin-only")],
        )
        self.assertEqual(settle(forge), 0)
        self.assertEqual(
            forge.merged(),
            [
                {
                    "merge_method": "squash",
                    "sha": HEAD,
                    "commit_title": "chore(contract): take lemonfiber 5a2ca238 (#45)",
                    "commit_message": "body",
                }
            ],
        )

    def test_a_check_nothing_requires_still_running_is_waited_for(self):
        forge = Forge([run("gates"), run("mutation testing", status="in_progress", conclusion=None)])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        self.assertEqual(forge.written(), [])

    def test_a_pending_status_is_waited_for(self):
        forge = Forge([run("gates")], [status("sonar", state="pending")])
        settle(forge)
        self.assertEqual(forge.merged(), [])

    def test_a_cancelled_run_its_rerun_passed_does_not_hold(self):
        forge = Forge(
            [
                run("gates / gates", conclusion="cancelled", started="2026-11-20T11:00:00Z", ident=1),
                run("gates / gates", started="2026-11-20T11:05:00Z", ident=2),
            ]
        )
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)

    def test_a_status_set_green_after_it_was_red_does_not_hold(self):
        forge = Forge(
            [run("gates")],
            [
                status("pin-only / pin-only", state="failure", updated="2026-11-20T11:01:00Z", ident=1),
                status("pin-only / pin-only", updated="2026-11-20T11:02:00Z", ident=2),
            ],
        )
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)


class Holding(unittest.TestCase):
    def test_a_red_check_holds_it_and_says_which(self):
        forge = Forge([run("gates"), run("download-torrent", conclusion="failure")])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(method, body)] = forge.written()
        self.assertEqual(method, "POST")
        self.assertTrue(body.startswith(train.MARKER))
        self.assertIn("download-torrent ended failure", body)

    def test_a_head_unsettled_past_the_bound_is_held_and_says_why(self):
        forge = Forge([run("plugin / live", status="queued", conclusion=None)], committed=OLD)
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("plugin / live is queued", body)
        self.assertIn("older than", body)

    def test_the_reason_is_edited_in_place_not_said_again(self):
        old = {"id": 9, "body": f"{train.MARKER}\nsomething earlier"}
        forge = Forge([run("gates", conclusion="failure")], comments=[old])
        settle(forge)
        self.assertEqual([method for method, _ in forge.written()], ["PATCH"])

    def test_an_unchanged_reason_writes_nothing(self):
        forge = Forge([run("gates", conclusion="failure")])
        settle(forge)
        [(_, body)] = forge.written()
        again = Forge([run("gates", conclusion="failure")], comments=[{"id": 9, "body": body}])
        settle(again)
        self.assertEqual(again.written(), [])


class Unread(unittest.TestCase):
    def test_a_head_whose_statuses_cannot_be_read_is_held_and_the_run_fails(self):
        forge = Forge([run("gates")], unreadable=True)
        self.assertEqual(settle(forge), 1)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("could not be read", body)
        self.assertIn("403", body)


class Idle(unittest.TestCase):
    def test_a_look_that_finds_nothing_marked_is_one_search(self):
        forge = Forge([run("gates")], marked=False)
        self.assertEqual(settle(forge), 0)
        self.assertEqual([path.split("?", 1)[0] for _, path, _ in forge.calls], ["search/issues"])


class Arguments(unittest.TestCase):
    def test_a_name_github_does_not_give_is_refused_before_any_call(self):
        forge = Forge([])
        self.assertEqual(train.main(["--owner", "lemon fiber", "--author", "x"], api=forge, now=NOW), 2)
        self.assertEqual(forge.calls, [])


if __name__ == "__main__":
    unittest.main()
