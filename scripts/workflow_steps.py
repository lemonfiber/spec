"""A workflow's steps as its tests read them: one step's `run`, the Python it runs from a
heredoc, and a directory of its own for each test."""

from __future__ import annotations

import pathlib
import shutil
import tempfile
import textwrap
import unittest

import yaml


def step(workflow: pathlib.Path, job: str, named: str) -> str:
    """The `run` of the step called `named` in `job` of `workflow`."""
    steps = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"][job]["steps"]
    return next(one for one in steps if one.get("name") == named)["run"]


def embedded(workflow: pathlib.Path, job: str, named: str) -> str:
    """The Python that step runs from its heredoc."""
    run = step(workflow, job, named)
    return textwrap.dedent(run.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0])


class Scratch(unittest.TestCase):
    """A directory of its own for each test."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
