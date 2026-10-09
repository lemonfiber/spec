#!/usr/bin/env python3
"""The fan-out's own shell, shown doing it — OPS-R48, Q-R66.

`test_fan_out_pins.py` covers the rewrite. The half that decides *what happens to
a repository* is shell inside `fan-out-pins.yml`: clone it, measure it, branch,
commit, push, open the pull request, and decide whether the run failed. None of
that is Python and none of it was exercised by anything.

This drives that step as CI drives it. The script is read out of the committed
YAML through a YAML parser, so what runs here is the literal text that runs
there — an edit to the workflow that breaks the loop fails this rather than
being found by a tag six weeks later. `gh` is replaced on a PATH prefix by a stub
that clones a fixture, answers whether a pull request already exists, records
the ones it is asked to open, and answers the API calls the bump's commit is made
with. `git` is the real one, except for `push`, which is intercepted and logged:
the step makes its commit through the API so GitHub signs it, and a push is
exactly what it must never do.

The case worth the most is the last one. The step says every repository is
visited even after one of them fails, because stopping at the first would leave
the rest of the organisation red for a reason having nothing to do with them.
That is a claim about a loop, and a loop is exactly the thing that quietly stops
being true.

Stdlib unittest plus PyYAML (the parser is the point — a hand-rolled reader would
be testing a different string than CI runs).
Run:  python3 scripts/test_fan_out_workflow.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import fan_out_pins
import yaml

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / ".github" / "workflows" / "fan-out-pins.yml"
JOB = "fan-out-pins"
STEP = "Open the bump wherever one is owed"
REACH = "Who holds a pin, and which of them the app can reach"
#: The `id` of the mint whose token opens the bumps; the other mint only lists.
WRITER = "token"

#: Stands in for `gh`, answered by what was asked:
#:
#: `repo clone`  — lays down a checkout seeded from GH_FIXTURE, unless the
#:                 repository is named in GH_CLONE_FAILS.
#: `pr list`     — prints GH_OPEN, the open pull requests as `number branch`
#:                 lines, unless GH_LIST_FAILS is set.
#: `pr create`   — records the call and prints the new pull request's address,
#:                 unless the repository is named in GH_CREATE_FAILS.
#: `pr edit`     — records the call, unless GH_EDIT_FAILS is set.
#: `pr close`    — records the call.
#: `run list`    — prints GH_RUNS, the unfinished runs' ids.
#: `run cancel`  — records the call.
#: `api graphql` — the commit: records the request on GH_COMMITS and prints a
#:                 new commit, unless GH_COMMIT_FAILS is set.
#: `api …/git/ref/heads/…` — whether a branch exists: yes only for the branches
#:                 named in GH_REFS_EXIST.
#: `api …/git/refs…` — a branch made, moved or removed: recorded on GH_REFS,
#:                 refused when GH_REF_FAILS is set.
#: `api`         — otherwise prints GH_INSTALLED as the installation's
#:                 repositories, one per line, unless GH_API_FAILS is set.
#:
#: A `--body-file` given to `pr create` or `pr edit` is appended to GH_BODIES.
GH_STUB = """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "${GH_LOG}"

short=""; body=""; prev=""
for word in "$@"; do
  case "$prev" in
  --repo) short=${word#*/} ;;
  --body-file) body=$word ;;
  esac
  prev=$word
done
if [ -n "$body" ] && [ -n "${GH_BODIES:-}" ]; then cat "$body" >> "${GH_BODIES}"; fi

case "$1 $2" in
"repo clone")
  named=$3
  short=${named#*/}
  at=$4
  case " ${GH_CLONE_FAILS:-} " in *" $short "*) exit 1 ;; esac
  mkdir -p "$at"
  cp -R "${GH_FIXTURE}/." "$at/"
  git -C "$at" init -q -b main
  git -C "$at" config user.email t@example.com
  git -C "$at" config user.name T
  git -C "$at" add -A
  git -C "$at" commit -qm "as it stands"
  exit 0
  ;;
"pr list")
  [ -z "${GH_LIST_FAILS:-}" ] || exit 1
  printf '%b' "${GH_OPEN:-}"
  exit 0
  ;;
"pr create")
  case " ${GH_CREATE_FAILS:-} " in *" ${short} "*) exit 1 ;; esac
  printf 'created %s\\n' "${short:-?}" >> "${GH_CREATED}"
  printf 'https://github.com/lemonfiber/%s/pull/7\\n' "${short}"
  exit 0
  ;;
"pr edit")
  [ -z "${GH_EDIT_FAILS:-}" ] || exit 1
  exit 0
  ;;
"run list")
  printf '%b' "${GH_RUNS:-}"
  exit 0
  ;;
"api graphql")
  cat >> "${GH_COMMITS}"
  printf '\n' >> "${GH_COMMITS}"
  [ -z "${GH_COMMIT_FAILS:-}" ] || exit 1
  printf '0123456789abcdef0123456789abcdef01234567\n'
  exit 0
  ;;
"api "*)
  case "$*" in
  *git/ref/heads/*)
    branch=${2##*/git/ref/heads/}
    case " ${GH_REFS_EXIST:-} " in *" $branch "*) exit 0 ;; esac
    exit 1
    ;;
  *git/refs*)
    printf '%s\n' "$*" >> "${GH_REFS}"
    [ -z "${GH_REF_FAILS:-}" ] || exit 1
    exit 0
    ;;
  esac
  [ -z "${GH_API_FAILS:-}" ] || exit 1
  printf '%s' "${GH_INSTALLED:-}"
  exit 0
  ;;
esac
exit 0
"""

#: Stands in for `git`, passing everything through to the real one except a
#: push. The step pushes to a URL it builds rather than to `origin`, so there is
#: no local remote a test could point at; intercepting is the only way to run the
#: step's own text without reaching the network.
GIT_STUB = """#!/bin/sh
set -eu
for word in "$@"; do
  if [ "$word" = "push" ]; then
    printf '%s\\n' "$*" >> "${GIT_PUSH_LOG}"
    if [ -n "${GIT_PUSH_FAILS:-}" ]; then
      case " ${GIT_PUSH_FAILS} " in *" any "*) exit 1 ;; esac
    fi
    exit 0
  fi
done
exec "${REAL_GIT}" "$@"
"""


def the_step(named: str = STEP) -> str:
    """The step's shell, read out of the committed workflow."""
    return a_step(named)["run"]


def a_step(named: str) -> dict:
    described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    for step in described["jobs"][JOB]["steps"]:
        if step.get("name") == named:
            return step

    raise AssertionError(f"no step named {named!r} in {WORKFLOW}")


def the_mints() -> list[dict]:
    """Every app token the job asks for, in the order it asks."""
    described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    return [
        one
        for one in described["jobs"][JOB]["steps"]
        if str(one.get("uses", "")).startswith("actions/create-github-app-token")
    ]


def a_pin(workflow: str, sha: str) -> str:
    return (
        "jobs:\n  one:\n    uses: "
        f"lemonfiber/spec/.github/workflows/{workflow}@{sha} # v1.0.1\n"
    )


class TheLoop(unittest.TestCase):
    """What the step does to each repository it is given."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.spec = self.root / "spec"
        (self.spec / "scripts").mkdir(parents=True)
        for name in ("fan_out_pins.py", "workflow_pins.py", "signed_pin_commit.py"):
            shutil.copy(HERE / name, self.spec / "scripts" / name)

        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "T")

        self.first = self.commit("one", "dco.yml")
        # The pin check's two limits, as the fan-out reads them from here.
        self.settled = self.commit('STALE_DAYS: "30"\nSTALE_COMMITS: "75"\n', "hygiene.yml")
        self.head = self.commit("two", "dco.yml")

        # Cut where CI cuts it. The step resolves `TAG` to a revision and the
        # script reads the revision from that tag, so a harness whose spec holds
        # no tags drives a run CI never has — and used to pass anyway, because
        # the script fell back to `HEAD` and `HEAD` happened to be right here.
        self.git("tag", "-a", "-m", "v1.0.9", "v1.0.9")

        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("gh", GH_STUB), ("git", GIT_STUB)):
            where = self.bin / name
            where.write_text(body, encoding="utf-8")
            where.chmod(0o755)

        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        (self.fixture / ".github" / "workflows").mkdir(parents=True)

        self.log = self.root / "gh.log"
        self.created = self.root / "created.log"
        self.pushes = self.root / "pushes.log"
        self.summary = self.root / "summary.md"
        self.bodies = self.root / "bodies.md"
        self.commits = self.root / "commits.log"
        self.refs = self.root / "refs.log"
        for where in (self.log, self.created, self.pushes, self.summary, self.bodies,
                      self.commits, self.refs):
            where.touch()

    def git(self, *args):
        subprocess.run(
            ["git", "-C", str(self.spec), *args], check=True, capture_output=True
        )

    def commit(self, said: str, workflow: str) -> str:
        where = self.spec / ".github" / "workflows" / workflow
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(said, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", workflow)
        got = subprocess.run(
            ["git", "-C", str(self.spec), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return got.stdout.strip()

    def pinning(self, text: str):
        (self.fixture / ".github" / "workflows" / "ci.yml").write_text(
            text, encoding="utf-8"
        )

    def run_step(self, named: str = "alpha", **extra) -> subprocess.CompletedProcess:
        where = shutil.which("git")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "REAL_GIT": where,
            "GH_TOKEN": "t",
            "OWNER": "lemonfiber",
            "TAG": "v1.0.9",
            "COMMIT": self.head,
            "NAMED": named,
            "SPEC": str(self.spec),
            "GH_FIXTURE": str(self.fixture),
            "GH_LOG": str(self.log),
            "GH_CREATED": str(self.created),
            "GIT_PUSH_LOG": str(self.pushes),
            "GH_BODIES": str(self.bodies),
            "GH_COMMITS": str(self.commits),
            "GH_REFS": str(self.refs),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            **extra,
        }

        return subprocess.run(
            ["bash", "-c", the_step()], capture_output=True, text=True, env=env
        )

    # --- what it does -----------------------------------------------------

    def test_a_stale_pin_gets_a_pull_request(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step()

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertIn("created alpha", self.created.read_text(encoding="utf-8"))
        self.assertIn("opened:  alpha", self.summary.read_text(encoding="utf-8"))

    def test_the_bump_is_committed_through_the_api_and_never_pushed(self):
        # Every consumer's `main` takes signed commits only, and GitHub signs a
        # commit it makes for the app. A commit made here and pushed is one no
        # repository could merge, which is what the first rolling run did.
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step()

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.pushes.read_text(encoding="utf-8"), "")
        made = self.commits.read_text(encoding="utf-8")
        self.assertIn('"branchName": "ci/take-the-shared-workflows-staging"', made)
        self.assertIn('"repositoryNameWithOwner": "lemonfiber/alpha"', made)
        self.assertIn(
            '"headline": "ci(workflows): take the shared workflows at v1.0.9"', made
        )
        self.assertIn('"path": ".github/workflows/ci.yml"', made)

    def test_the_kept_branch_is_moved_to_the_commit_never_reset_to_main(self):
        # The bump is made on a staging branch placed at `main`, and the kept
        # branch is then moved to it, forced: a pull request whose head briefly
        # held no commits of its own would be closed by GitHub (OPS-R85).
        self.pinning(a_pin("dco.yml", self.first))

        self.run_step(GH_REFS_EXIST="ci/take-the-shared-workflows")

        moves = self.refs.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(moves), 3, moves)
        self.assertIn("--method POST repos/lemonfiber/alpha/git/refs", moves[0])
        self.assertIn("ref=refs/heads/ci/take-the-shared-workflows-staging", moves[0])
        self.assertIn(
            "--method PATCH repos/lemonfiber/alpha/git/refs/heads/ci/take-the-shared-workflows ",
            moves[1] + " ",
        )
        self.assertIn("sha=0123456789abcdef0123456789abcdef01234567 -F force=true", moves[1])
        self.assertIn(
            "--method DELETE repos/lemonfiber/alpha/git/refs/heads/ci/take-the-shared-workflows-staging",
            moves[2],
        )

    def test_a_repository_with_nothing_stale_gets_nothing(self):
        # `hygiene.yml` has not moved since the pin, so there is nothing owed
        # and a pull request would be an empty one.
        self.pinning(a_pin("hygiene.yml", self.settled))

        ran = self.run_step()

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")
        self.assertIn("current: alpha", self.summary.read_text(encoding="utf-8"))

    def test_an_open_bump_is_moved_and_retitled_rather_than_opened_beside(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_OPEN="5 ci/take-the-shared-workflows\\n9 feature/other\\n")

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn(
            "pr edit 5 --repo lemonfiber/alpha --title ci(workflows): take the shared workflows at v1.0.9",
            log,
        )
        self.assertNotIn("pr close", log)
        self.assertIn("moved:   alpha", self.summary.read_text(encoding="utf-8"))

    def test_the_bump_is_titled_and_ended_as_its_squash_commit_needs(self):
        # A conventional title, and a body ending with the citation and a
        # sign-off, so `squash-message` holds nothing against it (GOV-R62).
        self.pinning(a_pin("dco.yml", self.first))

        self.run_step()

        self.assertIn(
            "--title ci(workflows): take the shared workflows at v1.0.9",
            self.log.read_text(encoding="utf-8"),
        )
        body = self.bodies.read_text(encoding="utf-8").rstrip()
        self.assertIn("\n\nSpec: OPS-R48, OPS-R85\n\n", body)
        self.assertTrue(body.endswith(
            "Signed-off-by: lemonfiber-release-train[bot] "
            "<lemonfiber-release-train[bot]@users.noreply.github.com>"))

    def test_only_the_app_s_own_pull_requests_from_this_repository_are_its(self):
        # A fork's pull request whose branch is named like the bump must not be
        # retitled, closed or have its runs cancelled: the listing keeps only
        # what the app opened from the repository's own branches.
        self.pinning(a_pin("dco.yml", self.first))

        self.run_step()

        log = self.log.read_text(encoding="utf-8")
        listed = log[log.index("pr list"):]
        self.assertIn("isCrossRepository", listed)
        self.assertIn("select(.isCrossRepository | not)", listed)
        self.assertIn('select(.author.login == "app/lemonfiber-release-train")', listed)

    def test_a_bump_opened_per_number_is_closed_pointing_at_the_one_kept(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(
            GH_OPEN="3 ci/take-the-shared-workflows-at-v1.0.8\\n4 feature/x\\n",
            GH_RUNS="111\\n112\\n",
        )

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("pr close 3 --repo lemonfiber/alpha --delete-branch --comment Replaced by #7", log)
        self.assertNotIn("pr close 4", log)
        self.assertIn("run list --repo lemonfiber/alpha --branch ci/take-the-shared-workflows-at-v1.0.8", log)
        self.assertIn("run cancel 111 --repo lemonfiber/alpha", log)
        self.assertIn("run cancel 112 --repo lemonfiber/alpha", log)
        self.assertIn("closed alpha#3", ran.stdout)

    def test_a_current_repository_closes_the_bump_it_no_longer_needs(self):
        # `main` took every pin some other way, so the open bump proposes
        # nothing, and a per-number one is closed saying so.
        self.pinning(a_pin("hygiene.yml", self.settled))

        ran = self.run_step(
            GH_OPEN="5 ci/take-the-shared-workflows\\n3 ci/take-the-shared-workflows-at-v1.0.8\\n"
        )

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("pr close 5 --repo lemonfiber/alpha --delete-branch", log)
        self.assertIn("pr close 3 --repo lemonfiber/alpha --delete-branch --comment `main` already holds", log)
        self.assertEqual(self.pushes.read_text(encoding="utf-8"), "")
        self.assertIn("current: alpha", self.summary.read_text(encoding="utf-8"))

    # --- what it refuses --------------------------------------------------

    def test_a_repository_that_could_not_be_cloned_fails_the_run(self):
        # Not silently skipped. A repository nobody could ask about is not a
        # repository that is current.
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_CLONE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("could not be cloned", ran.stdout)
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))
        self.assertIn("no bump was opened in: alpha", ran.stdout)

    def test_a_bump_that_could_not_be_committed_fails_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_COMMIT_FAILS="1")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("would not take the bump: the commit was not made", ran.stdout)
        self.assertEqual(self.created.read_text(encoding="utf-8"), "")
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))

    def test_open_pull_requests_that_could_not_be_listed_fail_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_LIST_FAILS="1")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("open pull requests could not be listed", ran.stdout)
        self.assertEqual(self.pushes.read_text(encoding="utf-8"), "")

    def test_a_bump_that_would_not_take_its_new_title_fails_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_OPEN="5 ci/take-the-shared-workflows\\n", GH_EDIT_FAILS="1")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("would not take the new title", ran.stdout)
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))

    def test_a_pull_request_that_would_not_open_fails_the_run(self):
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(GH_CREATE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)
        self.assertIn("would not take the pull request", ran.stdout)
        self.assertIn("refused: alpha", self.summary.read_text(encoding="utf-8"))

    # --- the claim the loop makes about itself ----------------------------

    def test_one_repository_failing_does_not_cost_the_others_their_bump(self):
        # The step says so in its own comment, and this is the only thing that
        # holds it to it. A `set -e`, or a `break` added while tidying, would
        # leave the rest of the organisation red for a reason of somebody
        # else's — which is the state the fan-out exists to end.
        self.pinning(a_pin("dco.yml", self.first))

        ran = self.run_step(named="alpha\nbeta\ngamma", GH_CLONE_FAILS="alpha")

        self.assertEqual(ran.returncode, 1)

        created = self.created.read_text(encoding="utf-8")
        self.assertIn("created beta", created)
        self.assertIn("created gamma", created)

        said = self.summary.read_text(encoding="utf-8")
        self.assertIn("opened:  beta gamma", said)
        self.assertIn("refused: alpha", said)


class WhoItCanReach(unittest.TestCase):
    """The step that decides which repositories the write token is minted for."""

    MAP = '[[repo]]\nname = "spec"\n\n[[repo]]\nname = "alpha"\n\n[[repo]]\nname = "unmade"\n\n[[repo]]\nname = "beta"\n'

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

        self.spec = self.root / "spec"
        (self.spec / "scripts").mkdir(parents=True)
        for name in ("fan_out_pins.py", "workflow_pins.py", "signed_pin_commit.py"):
            shutil.copy(HERE / name, self.spec / "scripts" / name)
        (self.spec / "30-repos").mkdir()
        (self.spec / "30-repos" / "repos.toml").write_text(self.MAP, encoding="utf-8")

        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "gh").write_text(GH_STUB, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)

        self.log = self.root / "gh.log"
        self.output = self.root / "output"
        self.summary = self.root / "summary.md"
        for where in (self.log, self.output, self.summary):
            where.touch()

    def run_step(self, **extra) -> subprocess.CompletedProcess:
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_TOKEN": "t",
            "GH_LOG": str(self.log),
            "RUNNER_TEMP": str(self.root),
            "GITHUB_OUTPUT": str(self.output),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            **extra,
        }

        return subprocess.run(
            ["bash", "-c", the_step(REACH)],
            capture_output=True,
            text=True,
            env=env,
            cwd=self.spec,
        )

    def test_a_repository_not_in_the_installation_is_skipped_and_named(self):
        ran = self.run_step(GH_INSTALLED="alpha\nbeta\nspec\n")

        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertIn("::warning::unmade is on the map and not in the app's installation", ran.stdout)
        self.assertIn("- unmade\n", self.summary.read_text(encoding="utf-8"))

        written = self.output.read_text(encoding="utf-8")
        self.assertIn(f"{fan_out_pins.REACHABLE}<<", written)
        self.assertIn("\nalpha\nbeta\n", written)
        self.assertNotIn("unmade", written)

    def test_it_asks_the_installation_and_reads_every_page(self):
        self.run_step(GH_INSTALLED="alpha\n")

        asked = self.log.read_text(encoding="utf-8")
        self.assertIn("/installation/repositories", asked)
        self.assertIn("--paginate", asked)

    def test_a_listing_that_fails_stops_the_run_before_any_mint(self):
        # Not read as an installation holding nothing. Under `pipefail` a failed
        # producer is easy to lose; the listing is captured and its exit tested.
        ran = self.run_step(GH_API_FAILS="1")

        self.assertNotEqual(ran.returncode, 0)
        self.assertIn("could not be listed", ran.stdout)
        # Stopped at the listing, not carried on to report an empty one.
        self.assertNotIn("listed no repositories", ran.stdout)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")

    def test_an_installation_holding_none_of_the_map_fails_the_run(self):
        ran = self.run_step(GH_INSTALLED="somebody-elses\n")

        self.assertNotEqual(ran.returncode, 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "")


class TheStepIsTheOneThatRuns(unittest.TestCase):
    """Read from the committed YAML, so this cannot drift from CI."""

    def test_the_step_is_found_by_name_in_the_workflow(self):
        self.assertIn("gh pr create", the_step())

    def test_the_workflow_declares_the_environment_the_step_reads(self):
        # A variable the step reads and the workflow does not pass is an empty
        # string under `set -u`… except that the step sets `-u` and would fail
        # loudly. This catches the rename before the tag does.
        described = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        step = next(
            one
            for one in described["jobs"][JOB]["steps"]
            if one.get("name") == STEP
        )

        for named in ("GH_TOKEN", "OWNER", "TAG", "COMMIT", "NAMED", "SPEC"):
            self.assertIn(named, step["env"])

    def test_the_token_asks_for_permission_to_write_a_workflow_file(self):
        # Every change this workflow makes is to a file under
        # `.github/workflows/`, and GitHub refuses that push from an app without
        # `workflows`, whatever else the token may do. Asked for by name so a
        # token that cannot do it fails at the mint — on 2026-09-22 one that was
        # not asked got as far as twelve rejected pushes, reported as twelve
        # repositories refusing a branch.
        minted = next(one for one in the_mints() if one.get("id") == WRITER)

        for asked in ("contents", "pull-requests", "workflows", "actions"):
            self.assertEqual(minted["with"][f"permission-{asked}"], "write")

    def test_the_write_token_is_minted_for_the_reachable_list_and_no_other(self):
        # The name is the script's constant, so the output it writes and the
        # output read here cannot be spelled two ways.
        minted = next(one for one in the_mints() if one.get("id") == WRITER)
        reached = a_step(REACH)

        self.assertEqual(
            minted["with"]["repositories"],
            f"${{{{ steps.{reached['id']}.outputs.{fan_out_pins.REACHABLE} }}}}",
        )

    def test_the_listing_token_reads_metadata_and_nothing_else(self):
        # It is the one token here scoped to the whole installation, which is
        # only tolerable because it can do nothing but read the list.
        listing = next(one for one in the_mints() if one.get("id") != WRITER)
        asked = {key: value for key, value in listing["with"].items() if key.startswith("permission-")}

        self.assertEqual(asked, {"permission-metadata": "read"})
        self.assertNotIn("repositories", listing["with"])
        self.assertEqual(
            a_step(REACH)["env"]["GH_TOKEN"],
            f"${{{{ steps.{listing['id']}.outputs.token }}}}",
        )

    def test_the_job_mints_two_tokens_and_no_third(self):
        # A third would be a token this file's two tests above say nothing about.
        self.assertEqual(len(the_mints()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
