#!/usr/bin/env python3
"""A bump's rolling pull request is touched only where it is the bump's own — OPS-R87.

The cases worth the most are the three a branch-name lookup got wrong: a fork's
pull request on a branch of the same name, a pull request somebody other than
the app opened, and a head that is not the commit the bump just made. Each is
shown editing nothing and arming nothing.

The script's half is driven through a fake forge. The workflow's half is the
step's literal shell, read out of the committed YAML through a parser and run
against a stub `gh` on a PATH prefix, so what runs here is what runs there.

Stdlib unittest plus PyYAML.
Run:  python3 scripts/test_rolling_pull_request.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rolling_pull_request as rolling  # noqa: E402

WORKFLOW = HERE.parent / ".github" / "workflows" / "rolling-pull-request.yml"
STEP = "Open the pull request, or edit the bump's own"

REPO = "lemonfiber/sdk-php"
BRANCH = "chore/the-client-takes-the-contract"
HEAD = "a" * 40
OTHER = "b" * 40
BOT = "lemonfiber-release-train[bot]"


def pull(number=7, repo=REPO, ref=BRANCH, sha=HEAD, login=BOT, base="main", armed=None):
    return {
        "number": number,
        "node_id": f"PR_{number}",
        "user": {"login": login} if login else None,
        "base": {"ref": base},
        "head": {"ref": ref, "sha": sha, "repo": {"full_name": repo} if repo else None},
        "auto_merge": armed,
    }


class Forge:
    """Answers each call from what the case set up, and records every one."""

    def __init__(self, open_pulls=(), at=HEAD, created=None, graphql=None, fails=None):
        self.open_pulls = list(open_pulls)
        self.at = at
        self.created = created if created is not None else pull(number=9)
        self.graphql_answer = graphql if graphql is not None else {"data": {}}
        self.fails = fails
        self.asked: list[tuple[str, str, dict | None]] = []

    def __call__(self, method, path, payload=None):
        self.asked.append((method, path, payload))
        if self.fails and self.fails in path:
            raise subprocess.CalledProcessError(1, "gh", stderr="HTTP 502")
        if method == "GET" and "/git/ref/heads/" in path:
            return {"object": {"sha": self.at}}
        if method == "GET" and "/pulls?" in path:
            return self.open_pulls
        if method == "POST" and path.endswith("/pulls"):
            return self.created
        if method == "POST" and path == "graphql":
            return self.graphql_answer
        return {}

    def writes(self):
        return [one for one in self.asked if one[0] != "GET"]

    def mutations(self):
        return [one[2] for one in self.asked if one[1] == "graphql"]


def run(forge, *extra, body="the body\n", title="chore(contract): take lemonfiber abcdef12"):
    argv = ["--repo", REPO, "--branch", BRANCH, "--head", HEAD, "--author", BOT, f"--title={title}", *extra]
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(body)), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rolling.main(argv, api=forge)
    return code, out.getvalue(), err.getvalue()


class TheForkCase(unittest.TestCase):
    """A fork's pull request on a branch of the same name is never the bump's."""

    def test_the_listing_asks_for_the_branch_of_this_repository(self):
        forge = Forge([pull()])
        run(forge)
        listed = [path for method, path, _ in forge.asked if "/pulls?" in path]
        self.assertEqual(len(listed), 1)
        self.assertIn("head=lemonfiber%3Achore%2Fthe-client-takes-the-contract", listed[0])
        self.assertIn("state=open", listed[0])

    def test_a_forks_pull_request_listed_anyway_is_left_alone_and_the_bumps_is_opened(self):
        fork = pull(number=41, repo="mallory/sdk-php", login="mallory")
        forge = Forge([fork])
        code, out, err = run(forge, "--auto-merge")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), "9")
        self.assertNotIn(("PATCH", f"repos/{REPO}/pulls/41"), [(m, p) for m, p, _ in forge.asked])
        self.assertTrue(all(one["variables"]["id"] != "PR_41" for one in forge.mutations()))
        self.assertIn("#41 is from mallory/sdk-php", err)

    def test_a_fork_whose_app_opened_it_is_still_not_the_bumps(self):
        # The author alone is not enough: the head has to be this repository's.
        fork = pull(number=41, repo="mallory/sdk-php")
        forge = Forge([fork, pull()])
        code, _, err = run(forge, "--auto-merge")
        self.assertEqual(code, 0, err)
        self.assertEqual([p for m, p, _ in forge.writes() if m == "PATCH"], [f"repos/{REPO}/pulls/7"])
        self.assertEqual([one["variables"]["id"] for one in forge.mutations()], ["PR_7"])

    def test_a_pull_request_from_a_deleted_repository_is_left_alone(self):
        forge = Forge([pull(number=41, repo=None)])
        code, _, err = run(forge)
        self.assertEqual(code, 0, err)
        self.assertIn("a deleted repository", err)

    def test_another_branch_in_this_repository_is_not_the_bumps(self):
        forge = Forge([pull(number=41, ref="chore/something-else")])
        code, out, _ = run(forge)
        self.assertEqual((code, out.strip()), (0, "9"))


class TheWrongAuthor(unittest.TestCase):
    """A pull request on the branch that the app did not open is refused."""

    def test_a_persons_pull_request_on_the_branch_is_refused_and_nothing_is_written(self):
        forge = Forge([pull(login="somebody")])
        code, out, err = run(forge, "--auto-merge")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(forge.writes(), [])
        self.assertIn("opened by somebody, not lemonfiber-release-train[bot]", err)
        self.assertIn("nothing was edited", err)

    def test_an_author_nobody_knows_is_refused(self):
        forge = Forge([pull(login=None)])
        code, _, err = run(forge)
        self.assertEqual(code, 1)
        self.assertIn("nobody known", err)
        self.assertEqual(forge.writes(), [])

    def test_a_pull_request_just_opened_by_somebody_else_is_neither_labelled_nor_armed(self):
        forge = Forge(created=pull(number=9, login="somebody"))
        code, _, err = run(forge, "--labels=dependencies", "--auto-merge")
        self.assertEqual(code, 1)
        self.assertEqual([m for m, _, _ in forge.writes()], ["POST"])
        self.assertIn("neither labelled nor armed", err)


class TheShaMismatch(unittest.TestCase):
    """Only the commit the bump just made is ever what is armed to merge."""

    def test_the_bumps_pull_request_at_another_commit_is_refused(self):
        forge = Forge([pull(sha=OTHER)])
        code, _, err = run(forge, "--auto-merge")
        self.assertEqual(code, 1)
        self.assertEqual(forge.writes(), [])
        self.assertIn(f"#7 is at {OTHER}, not {HEAD}", err)

    def test_a_branch_somebody_moved_is_refused_before_anything_is_listed(self):
        forge = Forge([pull()], at=OTHER)
        code, _, err = run(forge, "--auto-merge")
        self.assertEqual(code, 1)
        self.assertEqual(len(forge.asked), 1)
        self.assertIn(f"{BRANCH} is at {OTHER}", err)

    def test_a_pull_request_just_opened_at_another_commit_is_not_armed(self):
        forge = Forge(created=pull(number=9, sha=OTHER))
        code, _, _ = run(forge, "--auto-merge")
        self.assertEqual(code, 1)
        self.assertEqual(forge.mutations(), [])

    def test_auto_merge_is_armed_at_the_commit_and_nowhere_else(self):
        forge = Forge([pull()])
        run(forge, "--auto-merge")
        (armed,) = forge.mutations()
        self.assertIn("enablePullRequestAutoMerge", armed["query"])
        self.assertIn("expectedHeadOid", armed["query"])
        self.assertEqual(armed["variables"], {"id": "PR_7", "method": "SQUASH", "head": HEAD})


class TheBumpsOwn(unittest.TestCase):
    def test_the_bumps_pull_request_is_retitled_and_its_body_replaced(self):
        forge = Forge([pull()])
        code, out, _ = run(forge, body="new body\n", title="chore: the new one")
        self.assertEqual((code, out.strip()), (0, "7"))
        self.assertEqual(forge.writes(), [("PATCH", f"repos/{REPO}/pulls/7",
                                           {"title": "chore: the new one", "body": "new body\n"})])

    def test_none_open_opens_one_from_the_branch_into_main_and_labels_it(self):
        forge = Forge()
        code, out, _ = run(forge, "--labels= dependencies, ,ci ")
        self.assertEqual((code, out.strip()), (0, "9"))
        self.assertEqual(forge.writes(), [
            ("POST", f"repos/{REPO}/pulls",
             {"title": "chore(contract): take lemonfiber abcdef12", "head": BRANCH, "base": "main",
              "body": "the body\n"}),
            ("POST", f"repos/{REPO}/issues/9/labels", {"labels": ["dependencies", "ci"]}),
        ])

    def test_no_labels_asks_for_none(self):
        forge = Forge()
        run(forge)
        self.assertFalse([p for _, p, _ in forge.asked if p.endswith("/labels")])

    def test_a_run_not_asked_to_arm_leaves_an_armed_pull_request_armed(self):
        # A maintainer's arming is theirs: not asking to arm is not asking to
        # disarm, so nothing touches auto-merge at all.
        forge = Forge([pull(armed={"merge_method": "squash"})])
        code, _, _ = run(forge)
        self.assertEqual(code, 0)
        self.assertEqual(forge.mutations(), [])
        self.assertEqual([m for m, _, _ in forge.writes()], ["PATCH"])

    def test_nothing_armed_and_nothing_asked_calls_nothing(self):
        forge = Forge([pull()])
        run(forge)
        self.assertEqual(forge.mutations(), [])

    def test_two_of_the_bumps_open_on_the_branch_is_refused(self):
        forge = Forge([pull(), pull(number=8, base="release/0.1")])
        code, _, err = run(forge)
        self.assertEqual(code, 1)
        self.assertEqual(forge.writes(), [])
        self.assertIn("#7, #8", err)

    def test_one_into_another_branch_is_refused(self):
        forge = Forge([pull(base="release/0.1")])
        code, _, err = run(forge)
        self.assertEqual(code, 1)
        self.assertIn("merges into release/0.1, not main", err)

    def test_a_branch_is_escaped_in_the_url(self):
        forge = Forge()
        with contextlib.redirect_stderr(io.StringIO()):
            rolling.rolled(REPO, "chore/a.b_c-d", HEAD, BOT, "t", "b", [], False, forge)
        self.assertEqual(forge.asked[0][1], f"repos/{REPO}/git/ref/heads/chore/a.b_c-d")


class WhenTheForgeFails(unittest.TestCase):
    def test_a_refused_call_is_could_not_rather_than_refused(self):
        forge = Forge([pull()], fails="/pulls/7")
        code, _, err = run(forge)
        self.assertEqual(code, 2)
        self.assertIn("HTTP 502", err)

    def test_a_mutation_answered_with_errors_fails(self):
        forge = Forge([pull()], graphql={"errors": [{"message": "auto-merge is not allowed"}]})
        code, _, err = run(forge, "--auto-merge")
        self.assertEqual(code, 2)
        self.assertIn("auto-merge is not allowed", err)

    def test_an_answer_of_the_wrong_shape_fails(self):
        forge = Forge([{"number": 7}])
        code, _, _ = run(forge)
        self.assertEqual(code, 2)

    def test_a_body_that_cannot_be_read_fails(self):
        class Unreadable(io.StringIO):
            def read(self, *_):
                raise OSError("standard input is closed")

        err = io.StringIO()
        with mock.patch("sys.stdin", Unreadable()), contextlib.redirect_stderr(err):
            code = rolling.main(["--repo", REPO, "--branch", BRANCH, "--head", HEAD, "--author", BOT,
                                 "--title=t"], api=Forge())
        self.assertEqual(code, 2)
        self.assertIn("standard input is closed", err.getvalue())


class MalformedArguments(unittest.TestCase):
    def refused(self, **changed):
        given = {"--repo": REPO, "--branch": BRANCH, "--head": HEAD, "--author": BOT, "--title": "t"}
        given.update(changed)
        argv = [f"{flag}={value}" for flag, value in given.items()]
        forge = Forge()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = rolling.main(argv, api=forge)
        self.assertEqual(code, 2)
        self.assertEqual(forge.asked, [])
        return err.getvalue()

    def test_each_malformed_argument_is_refused_before_the_forge_is_asked(self):
        self.assertIn("not owner/name", self.refused(**{"--repo": "../../orgs/x"}))
        self.assertIn("not a bump's branch", self.refused(**{"--branch": "main"}))
        self.assertIn("not a bump's branch", self.refused(**{"--branch": "-x"}))
        self.assertIn("not a bump's branch", self.refused(**{"--branch": "a/../b"}))
        self.assertIn("not a commit", self.refused(**{"--head": "HEAD"}))
        self.assertIn("--author is empty", self.refused(**{"--author": " "}))
        self.assertIn("--title is empty", self.refused(**{"--title": ""}))


GH_STUB = """#!/bin/sh
set -eu
printf '%s %s\\n' "$3" "$4" >> "${GH_LOG}"
if [ "${5:-}" = "--input" ]; then cat >> "${GH_LOG}"; printf '\\n' >> "${GH_LOG}"; fi
case "$3 $4" in
"GET "*/git/ref/heads/*) printf '%s' "${GH_REF}" ;;
"GET "*/pulls\\?*) printf '%s' "${GH_PULLS}" ;;
"POST "*/pulls) printf '%s' "${GH_CREATED}" ;;
"POST graphql") printf '{"data":{}}' ;;
"POST "*/labels) printf '[]' ;;
esac
"""


class WithAStubbedGh(unittest.TestCase):
    """`gh` itself, and the workflow's own step, against a stub on PATH."""

    def setUp(self):
        self.scratch = pathlib.Path(tempfile.mkdtemp())
        stub = self.scratch / "bin" / "gh"
        stub.parent.mkdir()
        stub.write_text(GH_STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.log = self.scratch / "gh.log"
        self.env = {
            **os.environ,
            "PATH": f"{stub.parent}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.log),
            "GH_REF": json.dumps({"object": {"sha": HEAD}}),
            "GH_PULLS": json.dumps([]),
            "GH_CREATED": json.dumps(pull(number=9)),
        }

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.scratch)], check=True)

    def test_gh_sends_the_payload_on_its_input_and_reads_the_answer(self):
        saved = dict(os.environ)
        os.environ.update(self.env)
        try:
            created = rolling.gh("POST", f"repos/{REPO}/pulls", {"title": "t"})
            patched = rolling.gh("PATCH", f"repos/{REPO}/pulls/9", {"title": "t"})
            ref = rolling.gh("GET", f"repos/{REPO}/git/ref/heads/{BRANCH}")
        finally:
            os.environ.clear()
            os.environ.update(saved)
        self.assertEqual(created["number"], 9)
        self.assertEqual(patched, {})
        self.assertEqual(ref["object"]["sha"], HEAD)
        self.assertIn('{"title": "t"}', self.log.read_text(encoding="utf-8"))

    def step(self):
        described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        for one in described["jobs"]["open"]["steps"]:
            if one.get("name") == STEP:
                return one
        raise AssertionError(f"no step named {STEP!r}")

    def run_step(self, **inputs):
        work = self.scratch / "work"
        (work / ".spec-tooling").mkdir(parents=True)
        (work / ".spec-tooling" / "scripts").symlink_to(HERE)
        output, summary = self.scratch / "output", self.scratch / "summary"
        env = {**self.env, "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary),
               "GH_TOKEN": "x", "REPO": REPO, "AUTHOR": BOT, "BRANCH": BRANCH, "HEAD_SHA": HEAD,
               "TITLE": "chore: t", "BODY": "the body", "LABELS": "", "AUTO_MERGE": "false", **inputs}
        done = subprocess.run(["bash", "-c", self.step()["run"]], cwd=work, env=env,
                              capture_output=True, text=True, check=False)
        written = output.read_text(encoding="utf-8") if output.exists() else ""
        return done, written, work

    def test_the_step_opens_labels_and_arms_and_says_the_number(self):
        done, written, _ = self.run_step(LABELS="dependencies,ci", AUTO_MERGE="true")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(written, "number=9\n")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn(f"POST repos/{REPO}/issues/9/labels", log)
        self.assertIn('{"labels": ["dependencies", "ci"]}', log)
        self.assertIn("enablePullRequestAutoMerge", log)

    def test_the_step_refuses_a_fork_style_listing_of_somebody_elses_pull_request(self):
        # What `gh pr list --head` used to hand back: the branch name matched, the
        # pull request somebody else's. The step fails and writes nothing.
        self.env["GH_PULLS"] = json.dumps([pull(login="mallory")])
        done, written, _ = self.run_step(AUTO_MERGE="true")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(written, "")
        log = self.log.read_text(encoding="utf-8")
        self.assertNotIn("PATCH", log)
        self.assertNotIn("graphql", log)

    def test_what_a_caller_passes_is_never_read_as_shell(self):
        title = 'chore: $(touch pwned) `touch pwned` "; touch pwned; "'
        done, _, work = self.run_step(TITLE=title, BODY="$(touch pwned)", LABELS="$(touch pwned)")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((work / "pwned").exists())
        self.assertIn(json.dumps(title)[1:-1], self.log.read_text(encoding="utf-8"))


class TheWorkflow(unittest.TestCase):
    """What the reusable workflow is, read through a parser."""

    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.described = yaml.safe_load(self.text)
        self.steps = self.described["jobs"]["open"]["steps"]

    def test_no_run_block_holds_an_expression(self):
        for one in self.steps:
            self.assertNotIn("${{", one.get("run", ""), one.get("name"))

    def test_every_input_reaches_the_step_through_its_environment(self):
        inputs = self.described[True]["workflow_call"]["inputs"]
        env = next(one for one in self.steps if one.get("name") == STEP)["env"]
        passed = " ".join(str(value) for value in env.values())
        for name in inputs:
            self.assertIn(f"inputs.{name}", passed, name)

    def test_the_author_is_the_app_that_minted_the_token(self):
        env = next(one for one in self.steps if one.get("name") == STEP)["env"]
        self.assertEqual(env["AUTHOR"], "${{ steps.token.outputs.app-slug }}[bot]")
        self.assertEqual(env["GH_TOKEN"], "${{ steps.token.outputs.token }}")

    def test_the_token_is_for_the_calling_repository_alone(self):
        mint = next(one for one in self.steps if one.get("id") == "token")
        self.assertEqual(mint["with"]["repositories"], "${{ steps.here.outputs.name }}")
        self.assertEqual(mint["with"]["private-key"], "${{ secrets.RELEASE_APP_KEY }}")

    def test_the_script_is_the_one_at_the_pinned_commit(self):
        checkout = next(one for one in self.steps if one.get("with", {}).get("path") == ".spec-tooling")
        self.assertEqual(checkout["with"]["ref"], "${{ job.workflow_sha }}")
        self.assertFalse(checkout["with"]["persist-credentials"])

    def test_the_one_secret_is_declared_by_name(self):
        self.assertEqual(list(self.described[True]["workflow_call"]["secrets"]), ["RELEASE_APP_KEY"])


if __name__ == "__main__":
    unittest.main()
