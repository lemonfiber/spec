#!/usr/bin/env python3
"""The pull request a `workflow_run` was for, and pin-only's verdict posted on its head — Q-R83, Q-R84.

`run_pull.py` finds the pull request from what the forge set on the relay's run
and reads a label's approval from its timeline; `pin_only.py --source --check`
judges it and posts the verdict. Both are driven against stand-in forges.

Stdlib unittest plus PyYAML, as the coverage job installs.
Run:  python3 scripts/test_run_pull.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pin_only
import run_pull
from test_pin_only import CI, FORK, HEAD, NEW, REPO, WORKFLOW, Forge, at, caller, labeled, paged, ran

OTHER = "9" * 40


def opened(
    number: int = 7, head: str = HEAD, source: str = FORK, branch: str = "feature/x", base: str = REPO
):
    """An open pull request as the pulls list gives it."""
    return {
        "number": number,
        "head": {"sha": head, "ref": branch, "repo": {"full_name": source} if source else None},
        "base": {"repo": {"full_name": base}},
        "user": {"login": "someone", "id": 42},
        "labels": [],
    }


class Pulls:
    """The forge as `run_pull.py` reads it: open pull requests, a timeline, permissions."""

    def __init__(self, pulls=None, timeline=None, permissions=None, broken=None, runs=None):
        self.pulls = [opened()] if pulls is None else pulls
        self.timeline = timeline or []
        self.runs = runs or []
        self.permissions = permissions or {}
        self.broken = broken
        self.asked: list[str] = []

    def __call__(self, args: list[str]):
        path = args[0]
        self.asked.append(path)
        if self.broken:
            raise subprocess.CalledProcessError(1, ["gh", "api", path], stderr=self.broken)
        if path.startswith(f"repos/{REPO}/pulls?"):
            return paged(self.pulls, path)
        if path.startswith(f"repos/{REPO}/issues/7/timeline?"):
            return paged(self.timeline, path)
        if path.startswith(f"repos/{REPO}/actions/workflows/pin-only-check.yml/runs?branch=feature%2Fx&"):
            return {"workflow_runs": paged(self.runs, path)}
        if path.endswith("/permission"):
            login = urllib.parse.unquote(path.rsplit("/", 2)[1])
            return {"permission": self.permissions.get(login)}
        raise AssertionError(f"unexpected call {args}")


def resolved(forge: Pulls, *extra: str, source: str = FORK, branch: str = "feature/x", head: str = HEAD):
    """The exit code, what was said, and the fields written to `GITHUB_OUTPUT`."""
    with tempfile.TemporaryDirectory() as folder:
        output = pathlib.Path(folder) / "output"
        output.write_text("", encoding="utf-8")
        out = io.StringIO()
        argv = ["--repo", REPO, "--source", source, f"--branch={branch}", "--head", head, *extra]
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}), contextlib.redirect_stdout(out):
            code = run_pull.main(argv, api=forge)
        fields = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    return code, out.getvalue(), fields


class FindsThePullRequest(unittest.TestCase):
    def test_the_open_pull_request_with_that_head_on_that_branch(self):
        forge = Pulls([opened(3, head=OTHER), opened(7), opened(9, source="another/core")])
        code, said, fields = resolved(forge)
        self.assertEqual(code, 0, said)
        self.assertEqual(fields["number"], "7")
        self.assertEqual(fields["found"], "true")
        self.assertEqual(fields["approved"], "false")
        self.assertEqual(
            (
                fields["author"],
                fields["author_id"],
                fields["head_repo"],
                fields["head_ref"],
                fields["head_sha"],
            ),
            ("someone", "42", FORK, "feature/x", HEAD),
        )
        self.assertIn(f"repos/{REPO}/pulls?state=open&head=someone%3Afeature%2Fx", forge.asked[0])

    def test_a_head_no_open_pull_request_has_is_nothing_to_answer(self):
        for pulls in (
            [],
            [opened(head=OTHER)],
            [opened(source=None)],
            [opened(branch="feature/y")],
            [opened(base="another/core")],
        ):
            with self.subTest(pulls):
                code, said, fields = resolved(Pulls(pulls))
                self.assertEqual(code, 0, said)
                self.assertEqual(fields, {"found": "false", "approved": "false"})
                self.assertIn("No open pull request has the head", said)

    def test_two_open_pull_requests_with_the_head_are_refused(self):
        code, said, _ = resolved(Pulls([opened(7), opened(8)]))
        self.assertEqual(code, 2, said)
        self.assertIn("#7 and #8 are open with the head", said)

    def test_a_forge_that_cannot_be_read_is_refused(self):
        code, said, _ = resolved(Pulls(broken="gh: Not Found (HTTP 404)"))
        self.assertEqual(code, 2, said)
        self.assertIn("could not be read: gh: Not Found (HTTP 404)", said)

    def test_a_list_past_every_page_is_refused(self):
        many = [opened(head=OTHER)] * (run_pull.PER_PAGE * run_pull.PAGES)
        code, said, _ = resolved(Pulls(many))
        self.assertEqual(code, 2, said)
        self.assertIn(f"runs past {run_pull.PER_PAGE * run_pull.PAGES} items", said)

    def test_arguments_not_shaped_as_the_forge_gives_them_are_refused(self):
        for given, said_of in (
            ({"source": "not a repo"}, "--source"),
            ({"head": "main"}, "--head"),
            ({"branch": ""}, "--branch"),
        ):
            with self.subTest(given):
                code, said, _ = resolved(Pulls(), **given)
                self.assertEqual(code, 2, said)
                self.assertIn(said_of, said)
        code, said = 0, io.StringIO()
        with contextlib.redirect_stdout(said):
            code = run_pull.main(
                ["--repo", "x", "--source", FORK, "--branch", "b", "--head", HEAD], api=Pulls()
            )
        self.assertEqual(code, 2)
        self.assertIn("--repo 'x' is not a repository", said.getvalue())


class ReadsTheApproval(unittest.TestCase):
    """`proposal:approved` approves the head it was added on, by a writer, and nothing after it (GOV-R41)."""

    LABEL = "proposal:approved"
    RELAY = ".github/workflows/pin-only-check.yml"
    HELD = (ran(1, OTHER), ran(3), ran(8))

    def labelled(self, timeline, permissions=None, *extra, runs=None, head=HEAD, started=None):
        pull = opened(head=head)
        pull["labels"] = [{"name": self.LABEL}]
        forge = Pulls(
            [pull], timeline, {"lessevv": "admin"} if permissions is None else permissions, runs=runs
        )
        stamp = ["--started", started or at(8)]
        given = ["--label", self.LABEL, "--relay", self.RELAY, *stamp, *extra]
        return resolved(forge, *given, head=head)

    def approved(self, *given, **named) -> str:
        code, said, fields = self.labelled(*given, runs=list(named.pop("runs", self.HELD)), **named)
        self.assertEqual(code, 0, said)
        self.assertEqual(fields["approved"], "true", said)
        return said

    def refused(self, *given, words: str = "", **named) -> str:
        code, said, fields = self.labelled(*given, runs=list(named.pop("runs", self.HELD)), **named)
        self.assertEqual(code, 0, said)
        self.assertEqual(fields["approved"], "false", said)
        self.assertIn(words, said)
        return said

    def test_a_label_a_writer_added_on_the_current_head_approves(self):
        for permission in ("admin", "write"):
            with self.subTest(permission):
                said = self.approved([labeled(8, self.LABEL)], {"lessevv": permission})
                self.assertIn(f"was last added by lessevv at {at(8)}, on {HEAD}", said)

    def test_a_push_after_the_label_is_not_approved(self):
        pushed = [ran(1, OTHER), ran(3, OTHER), ran(8, OTHER), ran(9)]
        self.refused(
            [labeled(8, self.LABEL)],
            runs=pushed,
            started=at(9),
            words=f"was added at {at(8)} on {OTHER[:8]}, and the head is now {HEAD[:8]}",
        )

    def test_a_head_pushed_moments_before_the_label_is_not_approved(self):
        self.refused(
            [labeled(8, self.LABEL)], runs=[ran(1, OTHER), ran(8)], words="less than 60 seconds before"
        )
        self.approved([labeled(8, self.LABEL)], None, "--quiet", "0", runs=[ran(1, OTHER), ran(8)])

    def test_a_run_created_before_the_label_does_not_answer_it(self):
        self.refused([labeled(8, self.LABEL)], started=at(7), words=f"was created at {at(7)}, before")

    def test_a_label_added_by_anyone_else_does_not(self):
        self.refused(
            [labeled(8, self.LABEL, by="triager")],
            {"triager": "read"},
            words="who holds none of admin, write",
        )
        self.refused([labeled(8, self.LABEL, by="ghost")], {}, words="ghost")
        self.refused(
            [labeled(8, self.LABEL)], {"lessevv": "write"}, "--roles", "admin", words="none of admin."
        )

    def test_a_label_taken_off_after_it_was_added_or_never_recorded_does_not(self):
        for timeline in (
            [labeled(1, self.LABEL), labeled(2, self.LABEL, "unlabeled")],
            [labeled(1, "ci")],
        ):
            with self.subTest(timeline):
                self.refused(timeline, words=f"does not carry `{self.LABEL}` as last added by anyone")
        self.refused([dict(labeled(8, self.LABEL), actor=None)], words="nobody the forge names")

    def test_a_pull_request_not_carrying_the_label_reads_no_timeline(self):
        forge = Pulls()
        _code, _said, fields = resolved(forge, "--label", self.LABEL, "--relay", self.RELAY)
        self.assertEqual(fields["approved"], "false")
        self.assertFalse([path for path in forge.asked if "/timeline" in path])

    def test_a_label_without_a_relay_or_a_time_the_forge_did_not_stamp_is_refused(self):
        for given in (["--label", self.LABEL], ["--label", self.LABEL, "--relay", "pin-only.yml"]):
            with self.subTest(given):
                code, said, _ = resolved(Pulls(), *given)
                self.assertEqual(code, 2, said)
                self.assertIn("is not a workflow's path", said)
        code, said, _ = self.labelled([labeled(8, self.LABEL)], started="yesterday", runs=list(self.HELD))
        self.assertEqual(code, 2, said)

    def test_no_label_asked_about_approves_nothing(self):
        _code, _said, fields = resolved(Pulls())
        self.assertEqual(fields["approved"], "false")


class WritesItsFields(unittest.TestCase):
    def test_without_github_output_the_fields_go_to_stdout(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(out):
            run_pull.written({"found": "false"})
        self.assertEqual(out.getvalue(), "found=false\n")

    def test_gh_answers_json_or_nothing(self):
        with mock.patch.object(run_pull.subprocess, "run", return_value=mock.Mock(stdout='{"a": 1}')):
            self.assertEqual(run_pull.gh(["x"]), {"a": 1})
        with mock.patch.object(run_pull.subprocess, "run", return_value=mock.Mock(stdout="")):
            self.assertIsNone(run_pull.gh(["x"]))


class Verdicts(Forge):
    """test_pin_only's forge, answering the pulls list and taking the check run posted."""

    def __init__(self, *args, pulls=None, refuse_post=False, **named):
        super().__init__(*args, **named)
        self.pulls = pulls
        self.posted: list[dict] = []
        self.refuse_post = refuse_post

    def __call__(self, args: list[str], raw: bool):
        if args[:2] == ["--method", "POST"]:
            if self.refuse_post:
                raise subprocess.CalledProcessError(
                    1, ["gh"], stderr="gh: Resource not accessible (HTTP 403)"
                )
            fields = dict(one.split("=", 1) for one in args[4::2])
            self.posted.append({"path": args[2], **fields})
            return {}
        if args[0].startswith(f"repos/{REPO}/pulls?"):
            pulls = [opened()] if self.pulls is None else self.pulls
            return paged([dict(p, labels=[{"name": n} for n in self.labels]) for p in pulls], args[0])
        return super().__call__(args, raw)


def judged(forge: Verdicts, *extra: str) -> tuple[int, str]:
    out = io.StringIO()
    argv = [
        "--repo",
        REPO,
        "--head",
        HEAD,
        "--source",
        FORK,
        "--branch",
        "feature/x",
        "--relay",
        pin_only_relay(),
    ]
    with contextlib.redirect_stdout(out):
        code = pin_only.main([*argv, *extra], api=forge)
    return code, out.getvalue()


def pin_only_relay() -> str:
    return ".github/workflows/pin-only.yml"


class PostsTheVerdict(unittest.TestCase):
    CHECK = ("--check", "pin-only / pin-only", "--details", "https://example.test/run/1")

    def test_a_pass_is_posted_as_a_success_on_the_head(self):
        forge = Verdicts({CI: (caller(), caller(gates=NEW))})
        code, said = judged(forge, *self.CHECK)
        self.assertEqual(code, 0, said)
        [posted] = forge.posted
        self.assertEqual(posted["path"], f"repos/{REPO}/check-runs")
        self.assertEqual(
            (posted["name"], posted["head_sha"], posted["status"], posted["conclusion"]),
            ("pin-only / pin-only", HEAD, "completed", "success"),
        )
        self.assertEqual(posted["details_url"], "https://example.test/run/1")
        self.assertIn("change only spec's pins", posted["output[summary]"])
        self.assertIn(f"Posted `pin-only / pin-only` as success on {HEAD}.", said)

    def test_a_refusal_is_posted_as_a_failure_and_the_run_still_passes(self):
        forge = Verdicts({CI: (caller(), caller() + "  extra:\n    runs-on: x\n")})
        code, said = judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(code, 0, said)
        [posted] = forge.posted
        self.assertEqual(posted["conclusion"], "failure")
        self.assertEqual(posted["output[title]"], "A change to the checks, not approved")
        self.assertIn(f"{CI} changes more than spec's pins", posted["output[summary]"])
        self.assertNotIn("::error::", posted["output[summary]"])
        self.assertNotIn("details_url", posted)

    def test_a_forge_that_cannot_be_read_is_posted_as_a_failure(self):
        forge = Verdicts({CI: (caller(), caller())})
        forge.truncated.add("root1")
        judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(forge.posted[0]["conclusion"], "failure")

    def test_two_open_pull_requests_with_the_head_are_posted_as_a_failure(self):
        forge = Verdicts({CI: (caller(), caller())}, pulls=[opened(7), opened(8)])
        _code, _said = judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(forge.posted[0]["conclusion"], "failure")
        self.assertIn("#7 and #8 are open with the head", forge.posted[0]["output[summary]"])

    def test_no_open_pull_request_with_the_head_posts_nothing(self):
        forge = Verdicts({CI: (caller(), caller())}, pulls=[])
        code, said = judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(code, 0, said)
        self.assertEqual(forge.posted, [])
        code, said = judged(Verdicts({}, pulls=[]))
        self.assertEqual(code, 0, said)

    def test_a_list_of_pull_requests_past_every_page_is_a_failure(self):
        forge = Verdicts({}, pulls=[opened(head="9" * 40)] * (run_pull.PER_PAGE * run_pull.PAGES))
        code, said = judged(forge)
        self.assertEqual(code, 2, said)

    def test_a_verdict_the_forge_will_not_take_fails_the_run(self):
        forge = Verdicts({CI: (caller(), caller())}, refuse_post=True)
        code, said = judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(code, 2, said)
        self.assertIn("could not be posted as `pin-only / pin-only`", said)
        self.assertIn("HTTP 403", said)

    def test_the_approval_is_read_against_the_relay_s_runs_found_this_way(self):
        forge = Verdicts({CI: (caller(), caller() + "  extra:\n    runs-on: x\n")})
        forge.labels = [pin_only.APPROVED]
        forge.timeline = [labeled(8)]
        forge.runs = [ran(1), ran(8)]
        _code, said = judged(forge, "--check", "pin-only / pin-only")
        self.assertEqual(forge.posted[0]["conclusion"], "success", said)

    def test_a_source_without_a_branch_or_not_a_repository_is_refused(self):
        for extra in (["--source", FORK], ["--source", "nope", "--branch", "b"]):
            with self.subTest(extra):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = pin_only.main(
                        ["--repo", REPO, "--head", HEAD, "--relay", pin_only_relay(), *extra],
                        api=Verdicts({}),
                    )
                self.assertEqual(code, 2, out.getvalue())
                self.assertIn("names no branch", out.getvalue())


class WhoPosts(unittest.TestCase):
    """`check-source`: this run's token by default, or the release App (Q-R84)."""

    def setUp(self):
        self.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.steps = self.workflow["jobs"]["pin-only"]["steps"]

    def test_this_run_s_token_posts_unless_the_caller_names_the_app(self):
        call = self.workflow[True]["workflow_call"]
        self.assertEqual(call["inputs"]["check-source"]["default"], "actions")
        self.assertIs(call["secrets"]["RELEASE_APP_KEY"]["required"], False)
        [mint] = [s for s in self.steps if s.get("id") == "app"]
        self.assertEqual(mint["if"], "inputs.check-source == 'app'")
        self.assertEqual(mint["with"]["permission-checks"], "write")
        self.assertEqual(mint["with"]["repositories"], "${{ github.event.repository.name }}")
        written = [k for k, v in mint["with"].items() if k.startswith("permission-") and v != "read"]
        self.assertEqual(written, ["permission-checks"])
        self.assertEqual(self.steps[-1]["env"]["GH_TOKEN"], "${{ steps.app.outputs.token || github.token }}")

    def test_any_caller_but_the_verdict_fails(self):
        script = self.steps[0]["run"]
        for event, code in (("workflow_run", 0), ("pull_request_target", 1), ("pull_request", 1), ("push", 1)):
            with self.subTest(event):
                done = subprocess.run(
                    ["bash", "-c", script], env={"EVENT": event, "PATH": "/usr/bin:/bin"}, capture_output=True
                )
                self.assertEqual(done.returncode, code, done.stdout)

    def test_only_actions_or_app_is_a_source(self):
        script = self.steps[1]["run"]
        for source, code in (("actions", 0), ("app", 0), ("", 1), ("App", 1), ("token", 1)):
            with self.subTest(source):
                done = subprocess.run(
                    ["bash", "-c", script],
                    env={"SOURCE": source, "PATH": "/usr/bin:/bin"},
                    capture_output=True,
                )
                self.assertEqual(done.returncode, code, done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
