#!/usr/bin/env python3
"""The release train merges its own pull request only once every check on the head is green — OPS-R96.

Driven through a fake forge: each case says what the pull request, its head and
its checks are, and what the train then merged, said or left alone. The cases
worth the most are the ones that would merge with nothing judged: a head no
check has reported on yet, a required check that never started, a workflow
that starts late, and a pull request that is not the train's own.

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
BOT = "lemonfiber-release-train[bot]"
NOW = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.UTC)
PUSHED = "2026-11-20T11:00:00Z"
OLD = "2026-11-20T05:00:00Z"
ARGS = ["--owner", "lemonfiber", "--author", "lemonfiber-release-train", "--repo", REPO, "--number", "45"]
DENIED = subprocess.CalledProcessError(1, "gh", stderr="HTTP 403: Resource not accessible by integration")


TRAIN = "lemonfiber-release-train"


def run(
    name,
    status="completed",
    conclusion="success",
    started="2026-11-20T11:10:00Z",
    ident=1,
    app="github-actions",
):
    done = "2026-11-20T11:20:00Z" if status == "completed" else None
    return {
        "app": {"slug": app},
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started,
        "completed_at": done,
        "id": ident,
    }


def recorded(started="2026-11-20T11:01:00Z", app=TRAIN):
    return run(train.RECORD, started=started, ident=99, app=app)


def commit(sha=HEAD, author=BOT, committer="web-flow", verified=True):
    return {
        "sha": sha,
        "author": {"login": author},
        "committer": {"login": committer},
        "commit": {"verification": {"verified": verified}},
    }


def status(context, state="success", updated="2026-11-20T11:20:00Z", ident=1):
    return {"context": context, "state": state, "updated_at": updated, "id": ident}


def pull(**changes):
    made = {
        "number": 45,
        "state": "open",
        "merged_at": None,
        "draft": False,
        "title": "chore(contract): take lemonfiber 5a2ca238",
        "body": "body",
        "user": {"login": BOT, "type": "Bot"},
        "labels": [{"name": train.LABEL}],
        "head": {"sha": HEAD, "repo": {"full_name": REPO}},
        "base": {"ref": "main", "repo": {"full_name": REPO, "default_branch": "main"}},
    }
    made.update(changes)
    return made


class Forge:
    """One repository's one labelled pull request, and every call made to it."""

    def __init__(
        self,
        runs,
        statuses=(),
        *,
        required=("gates / gates",),
        pushed=PUSHED,
        comments=(),
        the_pull=None,
        commits=None,
        record=True,
        labeller=BOT,
        moved=(),
        unreadable=(),
    ):
        self.runs = list(runs) + ([recorded()] if record is True else [record] if record else [])
        self.statuses = list(statuses)
        self.required = list(required)
        self.pushed = pushed
        self.comments = [dict(one) for one in comments]
        self.pull = the_pull or pull()
        self.commits = [commit()] if commits is None else list(commits)
        self.labeller = labeller
        self.moved = list(moved)
        self.unreadable = set(unreadable)
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method, path, payload):
        self.calls.append((method, path, payload))
        bare = path.split("?", 1)[0]
        for part in self.unreadable:
            if bare.endswith(part):
                raise DENIED
        if bare == f"repos/{REPO}/pulls/45":
            return self.pull
        if bare.endswith("/required_status_checks"):
            return {"contexts": self.required, "checks": [{"context": one} for one in self.required]}
        if bare.endswith("/check-runs"):
            return {"check_runs": self.runs}
        if bare.endswith("/statuses"):
            return self.statuses
        if bare == f"repos/{REPO}/commits/{HEAD}":
            return {"commit": {"committer": {"date": self.pushed}}}
        if bare.startswith(f"repos/{REPO}/compare/"):
            return {"total_commits": len(self.commits), "commits": self.commits}
        if bare.endswith("/timeline"):
            return [
                {"event": "labeled", "label": {"name": train.LABEL}, "actor": {"login": self.labeller}},
                *self.moved,
            ]
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
    return train.main(ARGS, api=forge, now=NOW)


class Merging(unittest.TestCase):
    def test_a_head_whose_every_check_is_green_merges_at_that_head(self):
        forge = Forge(
            [
                run("gates / gates"),
                run("coverage", conclusion="skipped"),
                run("CodeQL", conclusion="neutral"),
            ],
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
            [run("gates / gates")],
            [
                status("pin-only / pin-only", state="failure", updated="2026-11-20T11:01:00Z", ident=1),
                status("pin-only / pin-only", updated="2026-11-20T11:02:00Z", ident=2),
            ],
        )
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)


class Waiting(unittest.TestCase):
    def assert_waits(self, forge):
        self.assertEqual(settle(forge), 0)
        self.assertEqual(forge.merged(), [])
        self.assertEqual(forge.written(), [])

    def test_a_head_no_check_has_reported_on_is_waited_for(self):
        self.assert_waits(Forge([], required=()))

    def test_a_required_check_that_has_not_reported_is_waited_for(self):
        self.assert_waits(Forge([run("lint")]))

    def test_a_check_nothing_requires_still_running_is_waited_for(self):
        self.assert_waits(
            Forge([run("gates / gates"), run("mutation testing", status="in_progress", conclusion=None)])
        )

    def test_a_pending_status_is_waited_for(self):
        self.assert_waits(Forge([run("gates / gates")], [status("sonar", state="pending")]))

    def test_a_head_pushed_within_the_quiet_time_is_waited_for(self):
        self.assert_waits(
            Forge([run("gates / gates", started="2026-11-20T11:55:00Z")], pushed="2026-11-20T11:55:00Z")
        )

    def test_a_check_that_finished_within_the_quiet_time_is_waited_for(self):
        late = run("gates / gates", started="2026-11-20T11:50:00Z")
        late["completed_at"] = "2026-11-20T11:58:00Z"
        self.assert_waits(Forge([late]))


class Holding(unittest.TestCase):
    def test_a_red_check_holds_it_and_says_which(self):
        forge = Forge([run("gates / gates"), run("download-torrent", conclusion="failure")])
        self.assertEqual(settle(forge), 0)
        self.assertEqual(forge.merged(), [])
        [(method, body)] = forge.written()
        self.assertEqual(method, "POST")
        self.assertTrue(body.startswith(train.MARKER))
        self.assertIn("download-torrent ended failure", body)

    def test_a_head_unsettled_past_the_bound_is_held_and_says_why(self):
        forge = Forge([run("plugin / live", status="queued", conclusion=None)], pushed=OLD)
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("plugin / live is queued", body)
        self.assertIn("older than", body)

    def test_the_reason_is_edited_in_place_not_said_again(self):
        old = {"id": 9, "body": f"{train.MARKER}\nsomething earlier"}
        forge = Forge([run("gates / gates", conclusion="failure")], comments=[old])
        settle(forge)
        self.assertEqual([method for method, _ in forge.written()], ["PATCH"])

    def test_an_unchanged_reason_writes_nothing(self):
        forge = Forge([run("gates / gates", conclusion="failure")])
        settle(forge)
        [(_, body)] = forge.written()
        again = Forge([run("gates / gates", conclusion="failure")], comments=[{"id": 9, "body": body}])
        settle(again)
        self.assertEqual(again.written(), [])


class Unreadable(unittest.TestCase):
    def assert_held_and_red(self, forge, said):
        self.assertEqual(settle(forge), 1)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn(said, body)

    def test_a_head_whose_statuses_cannot_be_read_is_held_and_the_look_fails(self):
        self.assert_held_and_red(Forge([run("gates / gates")], unreadable={"/statuses"}), "403")

    def test_a_branch_whose_protection_cannot_be_read_is_held_and_the_look_fails(self):
        self.assert_held_and_red(
            Forge([run("gates / gates")], unreadable={"/required_status_checks"}), "protection"
        )


class NotTheTrains(unittest.TestCase):
    def assert_held(self, forge, said):
        self.assertEqual(settle(forge), 1)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn(said, body)

    def green(self, **changes):
        return Forge([run("gates / gates")], **changes)

    def test_one_a_person_opened(self):
        self.assert_held(
            self.green(the_pull=pull(user={"login": "someone", "type": "User"})), "opened by someone"
        )

    def test_one_from_a_fork(self):
        self.assert_held(
            self.green(the_pull=pull(head={"sha": HEAD, "repo": {"full_name": "someone/sdk-rust"}})), "own"
        )

    def test_a_draft(self):
        self.assert_held(self.green(the_pull=pull(draft=True)), "draft")

    def test_one_into_another_branch(self):
        self.assert_held(
            self.green(
                the_pull=pull(base={"ref": "next", "repo": {"full_name": REPO, "default_branch": "main"}})
            ),
            "default branch",
        )

    def test_a_foreign_commit_under_the_train_s_own(self):
        self.assert_held(self.green(commits=[commit("b" * 40, author="someone"), commit()]), "not authored")

    def test_a_commit_a_person_committed(self):
        self.assert_held(self.green(commits=[commit(committer="someone")]), "not committed")

    def test_an_unverified_commit(self):
        self.assert_held(self.green(commits=[commit(verified=False)]), "not a verified commit")

    def test_a_range_it_cannot_read_whole(self):
        self.assert_held(self.green(commits=[]), "could not all be read")

    def test_a_browser_commit_claiming_the_bot_as_author_with_no_record_of_the_train_pushing_it(self):
        self.assert_held(self.green(record=None), "recorded no push")

    def test_a_record_another_app_put_on_the_head(self):
        self.assert_held(self.green(record=recorded(app="github-actions")), "recorded no push")

    def test_a_push_by_somebody_else_after_the_train_s(self):
        moved = {
            "event": "head_ref_force_pushed",
            "actor": {"login": "someone"},
            "created_at": "2026-11-20T11:30:00Z",
        }
        self.assert_held(self.green(moved=[moved]), "someone moved its branch")

    def test_a_push_by_somebody_else_before_the_train_s_own_does_not_hold(self):
        moved = {
            "event": "head_ref_force_pushed",
            "actor": {"login": "someone"},
            "created_at": "2026-11-20T10:00:00Z",
        }
        forge = self.green(moved=[moved])
        self.assertEqual(settle(forge), 0)
        self.assertEqual(len(forge.merged()), 1)

    def test_a_label_a_person_put_on(self):
        self.assert_held(self.green(labeller="someone"), "put on it by someone")


class Arguments(unittest.TestCase):
    def test_anything_github_would_not_give_here_is_refused_before_any_call(self):
        for changed in (
            {"--owner": "lemon fiber"},
            {"--repo": "someone-else/sdk-rust"},
            {"--repo": "lemonfiber/../x y"},
            {"--number": "45; rm"},
            {"--number": "0"},
        ):
            argv = list(ARGS)
            for flag, value in changed.items():
                argv[argv.index(flag) + 1] = value
            forge = Forge([])
            self.assertEqual(train.main(argv, api=forge, now=NOW), 2, changed)
            self.assertEqual(forge.calls, [], changed)


if __name__ == "__main__":
    unittest.main()
