#!/usr/bin/env python3
"""Coverage tests for check_superseded_runs.py — a pull request pushed again
cancels the run it supersedes, and a push to `main` or a tag is never cancelled
(Q-R75).

It runs inside the hygiene gate's shared-files job against whichever repository
called it, so a refusal here is a red check in every repository at once and a
pass it should not give is a pool of runners held by runs nobody reads. Both
directions are tested, each refusal by the words a maintainer would read.

Stdlib unittest, no dependencies. The canonical block is the real
`shared/concurrency.yml`; the repository it is compared against is built in a
temporary directory.
Run:  python3 scripts/test_superseded_runs.py
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_superseded_runs as superseded  # noqa: E402

GROUP = (
    "${{ github.workflow }}-${{ github.event_name == 'pull_request' "
    "&& github.ref || github.run_id }}"
)

BLOCK = f"""concurrency:
  group: {GROUP}
  cancel-in-progress: true
"""

JOBS = """jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo checked
"""


def workflow(on: str, concurrency: str = BLOCK, name: str = "check", jobs: str = JOBS) -> str:
    """A workflow file, with the parts this check reads in the places it reads them."""
    return f"name: {name}\n{on}\npermissions:\n  contents: read\n{concurrency}{jobs}"


class Repository(unittest.TestCase):
    """A spec checkout with the real block, and a repository with workflows."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.canonical = self.tmp / "spec"
        (self.canonical / "shared").mkdir(parents=True)
        shutil.copy(HERE.parent / superseded.HOME, self.canonical / "shared")
        self.repo = self.tmp / "repo"
        (self.repo / ".github" / "workflows").mkdir(parents=True)

    def write(self, name: str, text: str) -> None:
        (self.repo / ".github" / "workflows" / name).write_text(text, encoding="utf-8")

    def check(self, name: str = "cli") -> tuple[list[str], str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            said = superseded.superseded(self.repo, self.canonical, name)
        return said, out.getvalue()

    def refused(self, *words: str) -> list[str]:
        said, _ = self.check()
        self.assertTrue(said, "nothing was refused")
        for word in words:
            self.assertIn(word, "\n".join(said))
        return said


class Passing(Repository):
    """What must go through. A refusal here is every repository red at once."""

    def test_the_real_block_reads_as_the_group_every_repository_is_held_to(self):
        group, refusal = superseded.home(HERE.parent)
        self.assertEqual(refusal, [])
        self.assertEqual(group, GROUP)

    def test_a_pull_request_workflow_carrying_the_block(self):
        self.write("ci.yml", workflow("on: [pull_request]"))
        self.assertEqual(self.check(), ([], ""))

    def test_the_block_written_with_its_values_quoted(self):
        quoted = f"concurrency:\n  group: \"{GROUP}\"\n  cancel-in-progress: 'true'\n"
        self.write("ci.yml", workflow("on: pull_request", quoted))
        self.assertEqual(self.check()[0], [])

    def test_the_events_written_as_a_mapping_under_a_quoted_key(self):
        on = '"on":\n  pull_request:\n    types: [opened, synchronize]\n  push:\n    branches: [main]'
        self.write("ci.yml", workflow(on))
        self.assertEqual(self.check()[0], [])

    def test_the_events_written_as_a_list(self):
        on = "on:\n  - pull_request\n  - push  # and main"
        self.write("ci.yml", workflow(on))
        self.assertEqual(self.check()[0], [])

    def test_a_workflow_no_pull_request_runs_needs_no_group(self):
        self.write("stale.yml", workflow("on:\n  schedule:\n    - cron: '0 0 * * *'", ""))
        self.assertEqual(self.check()[0], [])

    def test_a_group_that_waits_rather_than_cancels_on_a_schedule(self):
        # One at a time is what `pins` and `sdk-bump` want, and a queued schedule
        # replaced by the next one is no push and no tag.
        self.write("pins.yml", workflow(
            "on: [schedule, workflow_dispatch]",
            "concurrency:\n  group: pins\n  cancel-in-progress: false\n"))
        self.write("bump.yml", workflow("on: workflow_dispatch", "concurrency: bump\n", name="bump"))
        self.assertEqual(self.check()[0], [])

    def test_a_reusable_workflow_called_from_elsewhere_carries_none(self):
        self.write("gate.yml", workflow("on:\n  workflow_call:", ""))
        self.assertEqual(self.check()[0], [])

    def test_a_reusable_workflow_run_directly_beside_the_canceller(self):
        self.write("hygiene.yml", workflow("on:\n  workflow_call:\n  pull_request:", "", name="hygiene"))
        self.write(superseded.CANCELLER, workflow(
            "on:\n  pull_request:\n    types: [synchronize]", name="cancel-superseded"))
        self.assertEqual(self.check()[0], [])

    def test_a_job_group_that_waits_outside_a_pull_request(self):
        jobs = JOBS + "    concurrency:\n      group: deploy\n      cancel-in-progress: false\n"
        self.write("deploy.yml", workflow("on:\n  push:\n    branches: [main]", "", jobs=jobs))
        self.assertEqual(self.check()[0], [])

    def test_two_workflows_with_no_name_are_told_apart_by_their_paths(self):
        nameless = "on: [pull_request]\n" + BLOCK + JOBS
        self.write("a.yml", nameless)
        self.write("b.yaml", "---\n" + nameless)
        self.assertEqual(self.check()[0], [])

    def test_a_file_that_is_not_a_workflow_is_not_read(self):
        self.write("README.md", "on: [pull_request]\n")
        self.assertEqual(self.check()[0], [])

    def test_a_repository_with_no_workflows(self):
        shutil.rmtree(self.repo / ".github")
        self.assertEqual(self.check()[0], [])


class Refusing(Repository):
    """What must not go through, each named by the file and the fix."""

    def test_a_pull_request_workflow_with_no_group(self):
        self.write("ci.yml", workflow("on: [pull_request]", ""))
        said = self.refused(".github/workflows/ci.yml runs on a pull request", "shared/concurrency.yml")
        self.assertIn(BLOCK.strip(), said[0])

    def test_a_pull_request_group_that_does_not_cancel(self):
        waits = BLOCK.replace("true", "false")
        self.write("ci.yml", workflow("on: pull_request", waits))
        self.refused("ci.yml runs on a pull request")

    def test_a_group_keyed_on_the_pull_request_number(self):
        # It cancels the right runs, and it is not the block: one form, so one
        # reading of it, everywhere.
        self.write("ci.yml", workflow("on: [pull_request]", BLOCK.replace(
            "github.event_name == 'pull_request' && github.ref || github.run_id",
            "github.event.pull_request.number")))
        self.refused("ci.yml runs on a pull request")

    def test_a_group_keyed_on_the_ref_alone_cancels_a_push_to_main(self):
        self.write("deploy.yml", workflow(
            "on:\n  push:\n    branches: [main]",
            "concurrency:\n  group: pages-${{ github.ref }}\n  cancel-in-progress: true\n"))
        self.refused("deploy.yml cancels by the group 'pages-${{ github.ref }}'", "protected branch or a tag")

    def test_a_cancel_decided_by_an_expression_still_cancels(self):
        self.write("deploy.yml", workflow(
            "on: push",
            "concurrency:\n  group: pages\n  cancel-in-progress: ${{ github.event_name == 'push' }}\n"))
        self.refused("deploy.yml cancels by the group 'pages'")

    def test_a_reusable_workflow_that_cancels(self):
        self.write("gate.yml", workflow("on:\n  workflow_call:"))
        self.refused("gate.yml is a reusable workflow with a group that cancels", "caller's own group")

    def test_a_reusable_workflow_run_directly_with_no_canceller(self):
        self.write("hygiene.yml", workflow("on:\n  workflow_call:\n  pull_request:", ""))
        self.refused("hygiene.yml is a reusable workflow a pull request also runs directly",
                     superseded.CANCELLER)

    def test_a_canceller_no_pull_request_runs_cancels_nothing(self):
        self.write("hygiene.yml", workflow("on:\n  workflow_call:\n  pull_request:", "", name="hygiene"))
        self.write(superseded.CANCELLER, workflow("on: workflow_dispatch", "", name="cancel-superseded"))
        self.refused("hygiene.yml is a reusable workflow a pull request also runs directly")

    def test_a_job_group_that_cancels(self):
        jobs = JOBS + "    concurrency:\n      group: x-${{ github.ref }}\n      cancel-in-progress: true\n"
        self.write("deploy.yml", workflow("on: push", "", jobs=jobs))
        self.refused("deploy.yml job 'check' has a group of its own")

    def test_any_job_group_in_a_workflow_a_pull_request_runs(self):
        # A job waiting in a group is replaced by the next to arrive, so a
        # push's deploy can be cancelled by a group that says it cancels nothing.
        jobs = JOBS + "    concurrency: pages\n"
        self.write("docs.yml", workflow("on: [pull_request, push]", jobs=jobs))
        self.refused("docs.yml job 'check' has a group of its own")

    def test_two_workflows_sharing_a_name_cancel_each_other(self):
        self.write("a.yml", workflow("on: [pull_request]", name="ci"))
        self.write("b.yml", workflow("on: [pull_request]", name="'ci'"))
        self.refused(".github/workflows/a.yml and .github/workflows/b.yml are both named 'ci'")


class Unreadable(Repository):
    """A shape the reader does not know is refused, never passed."""

    def refuses(self, text: str, why: str) -> None:
        self.write("odd.yml", text)
        self.refused("odd.yml could not be read here", why, "refused rather than passed")

    def test_events_as_a_flow_mapping(self):
        self.refuses(workflow("on: {pull_request: {}}"), "flow mapping")

    def test_events_as_a_list_that_runs_onto_the_next_line(self):
        self.refuses(workflow("on: [pull_request,\n  push]"), "does not close on its line")

    def test_a_group_as_a_flow_mapping(self):
        self.refuses(workflow("on: pull_request", "concurrency: {group: x}\n"), "flow mapping")

    def test_a_list_at_the_top_level(self):
        self.refuses("on:\n- pull_request\n" + JOBS, "a list item at the top level")

    def test_a_line_indented_less_than_its_block(self):
        self.refuses("on:\n    pull_request:\n  push:\n" + JOBS, "indented less than the block")

    def test_a_line_that_is_not_a_key(self):
        self.refuses("on: pull_request\n? complex\n" + JOBS, "not a key this reader knows")

    def test_a_colon_with_nothing_after_it_but_more_text(self):
        self.refuses("on: pull_request\nname:ci\n" + JOBS, "not a key this reader knows")

    def test_a_quote_that_never_closes(self):
        self.refuses(workflow("on: pull_request", 'concurrency:\n  group: "open\n'), "unclosed quote")


class TheHome(Repository):
    """The block every workflow is held to has to be there and has to cancel."""

    def test_a_home_that_is_not_there(self):
        (self.canonical / superseded.HOME).unlink()
        said, _ = self.check()
        self.assertEqual(len(said), 1)
        self.assertIn("shared/concurrency.yml is not here", said[0])

    def test_a_home_that_cannot_be_read(self):
        (self.canonical / superseded.HOME).write_text("concurrency: {group: x}\n", encoding="utf-8")
        said, _ = self.check()
        self.assertIn("shared/concurrency.yml could not be read", said[0])

    def test_a_home_whose_group_cancels_nothing(self):
        (self.canonical / superseded.HOME).write_text(BLOCK.replace("true", "false"), encoding="utf-8")
        said, _ = self.check()
        self.assertIn("holds no group that cancels", said[0])

    def test_a_home_with_no_block_at_all(self):
        (self.canonical / superseded.HOME).write_text("# nothing\n", encoding="utf-8")
        said, _ = self.check()
        self.assertIn("holds no group that cancels", said[0])


class Reported(Repository):
    """A repository still being brought into line is told, and not failed."""

    NAME = min(superseded.REPORTED)

    def test_its_findings_are_warnings(self):
        self.write("ci.yml", workflow("on: [pull_request]", ""))
        said, out = self.check(self.NAME)
        self.assertEqual(said, [])
        self.assertIn(f"::warning::{self.NAME} is reported here rather than refused", out)
        self.assertIn("ci.yml runs on a pull request", out)

    def test_one_carrying_the_group_everywhere_is_told_to_leave_the_list(self):
        self.write("ci.yml", workflow("on: [pull_request]"))
        said, out = self.check(self.NAME)
        self.assertEqual(said, [])
        self.assertIn("Take it out of REPORTED", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
