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
from unittest import mock

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
    suite=1,
):
    done = "2026-11-20T11:20:00Z" if status == "completed" else None
    return {
        "app": {"slug": app},
        "check_suite": {"id": suite},
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started,
        "completed_at": done,
        "id": ident,
    }


def recorded(started="2026-11-20T11:01:00Z", app=TRAIN):
    return run(train.RECORD, started=started, ident=99, app=app, suite=99)


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
        rules=(),
        workflows=None,
    ):
        self.rules = list(rules)
        self.workflows = {1: 7} if workflows is None else dict(workflows)
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
        if bare == f"repos/{REPO}/actions/runs":
            suite = int(path.split("check_suite_id=", 1)[1].split("&", 1)[0])
            known = self.workflows.get(suite)
            return {"workflow_runs": [{"workflow_id": known}] if known else []}
        if bare.startswith(f"repos/{REPO}/rules/branches/"):
            return [
                {"type": "pull_request", "parameters": {}},
                *(
                    {
                        "type": "required_status_checks",
                        "parameters": {"required_status_checks": [{"context": one}]},
                    }
                    for one in self.rules
                ),
            ]
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

    def test_a_red_status_holds_it_and_says_which(self):
        forge = Forge([run("gates / gates")], [status("sonar / gate", state="failure")])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("sonar / gate is failure", body)

    def test_a_marker_comment_somebody_else_wrote_is_neither_edited_nor_taken_for_the_train_s(self):
        planted = {"id": 5, "user": {"login": "someone"}, "body": f"{train.MARKER}\nplanted"}
        forge = Forge([run("gates / gates", conclusion="failure")], comments=[planted])
        settle(forge)
        [(method, body)] = forge.written()
        self.assertEqual(method, "POST")
        self.assertIn("gates / gates ended failure", body)

    def test_a_head_unsettled_past_the_bound_is_held_and_says_why(self):
        forge = Forge([run("plugin / live", status="queued", conclusion=None)], pushed=OLD)
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("plugin / live is queued", body)
        self.assertIn("older than", body)

    def test_the_reason_is_edited_in_place_not_said_again(self):
        old = {"id": 9, "user": {"login": BOT}, "body": f"{train.MARKER}\nsomething earlier"}
        forge = Forge([run("gates / gates", conclusion="failure")], comments=[old])
        settle(forge)
        self.assertEqual([method for method, _ in forge.written()], ["PATCH"])

    def test_an_unchanged_reason_writes_nothing(self):
        forge = Forge([run("gates / gates", conclusion="failure")])
        settle(forge)
        [(_, body)] = forge.written()
        again = Forge(
            [run("gates / gates", conclusion="failure")],
            comments=[{"id": 9, "user": {"login": BOT}, "body": body}],
        )
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

    def test_a_branch_whose_protection_and_rulesets_both_cannot_be_read_is_held_and_the_look_fails(self):
        self.assert_held_and_red(
            Forge([run("gates / gates")], unreadable={"/required_status_checks", "/rules/branches/main"}),
            "protection",
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


class OneCheckAtATime(unittest.TestCase):
    def test_a_red_job_is_not_hidden_by_a_green_one_of_the_same_name_in_another_workflow(self):
        forge = Forge(
            [
                run("gates / gates"),
                run("build", conclusion="failure", started="2026-11-20T11:02:00Z", ident=2, suite=2),
                run("build", started="2026-11-20T11:03:00Z", ident=3, suite=3),
            ],
            workflows={1: 7, 2: 20, 3: 30},
        )
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("build ended failure", body)

    def test_a_later_run_of_the_same_workflow_supersedes_an_earlier_one(self):
        forge = Forge(
            [
                run(
                    "gates / gates", conclusion="cancelled", started="2026-11-20T11:02:00Z", ident=2, suite=2
                ),
                run("gates / gates", started="2026-11-20T11:03:00Z", ident=3, suite=3),
            ],
            workflows={2: 7, 3: 7},
        )
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)

    def test_a_rerun_queued_with_no_start_yet_is_waited_for_over_the_green_run_before_it(self):
        queued = run("gates / gates", status="queued", conclusion=None, started=None, ident=4)
        forge = Forge([run("gates / gates"), queued])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        self.assertEqual(forge.written(), [])

    def test_a_cancelled_run_nothing_later_superseded_is_red(self):
        forge = Forge([run("gates / gates", conclusion="cancelled")])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        [(_, body)] = forge.written()
        self.assertIn("gates / gates ended cancelled", body)

    def test_a_suite_whose_workflow_cannot_be_found_is_a_check_of_its_own(self):
        forge = Forge(
            [
                run("build", conclusion="failure", started="2026-11-20T11:02:00Z", ident=2, suite=2),
                run("build", started="2026-11-20T11:03:00Z", ident=3, suite=3),
                run("gates / gates"),
            ],
            workflows={1: 7, 3: 30},
        )
        settle(forge)
        self.assertEqual(forge.merged(), [])

    def test_another_app_s_check_of_the_same_name_is_its_own_check(self):
        forge = Forge(
            [
                run(
                    "scan",
                    conclusion="failure",
                    started="2026-11-20T11:02:00Z",
                    ident=2,
                    app="sonarcloud",
                    suite=5,
                ),
                run("scan", started="2026-11-20T11:03:00Z", ident=3, suite=1),
                run("gates / gates"),
            ]
        )
        settle(forge)
        self.assertEqual(forge.merged(), [])


class Required(unittest.TestCase):
    def test_a_context_only_a_ruleset_requires_is_waited_for(self):
        forge = Forge([run("gates / gates")], rules=["lint"])
        settle(forge)
        self.assertEqual(forge.merged(), [])
        self.assertEqual(forge.written(), [])

    def test_a_branch_with_no_classic_protection_is_read_from_its_rulesets(self):
        forge = Forge([run("lint")], rules=["lint"], unreadable={"/required_status_checks"})
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)

    def test_a_branch_whose_rulesets_cannot_be_read_is_read_from_its_protection(self):
        forge = Forge([run("gates / gates")], unreadable={"/rules/branches/main"})
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)


class Paging(unittest.TestCase):
    def test_a_range_longer_than_a_page_is_read_to_its_end(self):
        many = [commit(f"{n:040x}") for n in range(train.PER_PAGE)]

        class Long(Forge):
            def __call__(self, method, path, payload):
                if "/compare/" in path:
                    self.calls.append((method, path, payload))
                    first = path.endswith("&page=1")
                    return {"total_commits": train.PER_PAGE + 1, "commits": many if first else [commit()]}
                return super().__call__(method, path, payload)

        forge = Long([run("gates / gates")])
        settle(forge)
        self.assertEqual(len(forge.merged()), 1)

    def test_a_listing_longer_than_a_page_is_read_to_its_end(self):
        pages = {1: [{"n": n} for n in range(train.PER_PAGE)], 2: [{"n": "last"}]}
        read = train.paged(lambda method, path, payload: pages[int(path.rsplit("page=", 1)[1])], "x", None)
        self.assertEqual(len(read), train.PER_PAGE + 1)


class TheForge(unittest.TestCase):
    def test_gh_sends_the_payload_on_its_input_and_reads_the_answer(self):
        answered = subprocess.CompletedProcess([], 0, stdout='{"merged": true}', stderr="")
        with mock.patch.object(train.subprocess, "run", return_value=answered) as ran:
            self.assertEqual(train.gh("PUT", "repos/x/y/pulls/1/merge", {"sha": HEAD}), {"merged": True})
        self.assertEqual(ran.call_args.args[0][-2:], ["--input", "-"])
        self.assertEqual(ran.call_args.kwargs["input"], '{"sha": "' + HEAD + '"}')
        quiet = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(train.subprocess, "run", return_value=quiet) as ran:
            self.assertEqual(train.gh("GET", "repos/x/y"), {})
        self.assertIsNone(ran.call_args.kwargs["input"])

    def test_a_merge_the_forge_refuses_fails_the_look(self):
        class Refusing(Forge):
            def __call__(self, method, path, payload):
                if method == "PUT":
                    raise DENIED
                return super().__call__(method, path, payload)

        self.assertEqual(settle(Refusing([run("gates / gates")])), 1)

    def test_a_pull_request_whose_ownership_cannot_be_read_is_held(self):
        forge = Forge([run("gates / gates")], unreadable={"/timeline"})
        self.assertEqual(settle(forge), 1)
        self.assertEqual(forge.merged(), [])


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
