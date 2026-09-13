#!/usr/bin/env python3
"""Coverage tests for check_binding_order.py — OPS-R11, Q-R66.

The gate is shown refusing each thing it exists to refuse, against a spec tree
built in a temporary directory: an accepted feature requiring a draft, one
requiring a feature the spec has moved on from, and one requiring a feature that
is not here at all.

It is also shown refusing a tree it did not read. That is the failure this gate
actually had: `FEATURES` is a relative path, so from any directory but the
checkout root `rglob` yielded nothing, `status` was empty, and the gate printed
*binding order ok: 0 accepted features, none resting on a draft* and exited 0. A
gate that has read nothing and a gate that has read everything and found it in
order say the same sentence, and the first one is worth nothing.

`relates:` is checked too — that it is *not* acted on. It is the field the gate
deliberately ignores, and an ignore nobody tests is an ignore somebody removes.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_binding_order.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_binding_order as gate

FEATURE = """---
id: {fid}
title: A feature
kind: feature
status: {status}
{extra}---

# {fid} — a feature
"""


def tree(features: list[tuple[str, str, str]]) -> pathlib.Path:
    """A spec checkout holding exactly these features."""
    root = pathlib.Path(tempfile.mkdtemp())
    where = root / gate.FEATURES / "x-area"
    where.mkdir(parents=True)
    for fid, status, extra in features:
        (where / f"{fid.lower()}.md").write_text(
            FEATURE.format(fid=fid, status=status, extra=extra), encoding="utf-8"
        )
    return root


def run(root: pathlib.Path) -> tuple[int, str]:
    """The gate against this tree, as an exit code and everything it said."""
    said = io.StringIO()
    argv = sys.argv
    sys.argv = ["check_binding_order.py", "--root", str(root)]
    try:
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
            gate.main()
    except SystemExit as stopped:
        code = stopped.code
        if isinstance(code, str):
            said.write(code)
            return 1, said.getvalue()
        return int(code or 0), said.getvalue()
    finally:
        sys.argv = argv
    return 0, said.getvalue()


# Every tree below carries the feature the gate checks it read, so that a failure
# here is about the claim under test rather than about the tree.
KNOWN = (gate.KNOWN, "accepted", "")


class ReadingTheTree(unittest.TestCase):
    def test_a_tree_it_did_not_read_is_refused_rather_than_passed(self):
        root = pathlib.Path(tempfile.mkdtemp())
        code, said = run(root)
        self.assertEqual(code, 1)
        self.assertIn("read the wrong tree", said)

    def test_a_tree_holding_only_other_features_is_refused_too(self):
        code, said = run(tree([("Z9", "accepted", "")]))
        self.assertEqual(code, 1)
        self.assertIn(gate.KNOWN, said)

    def test_a_tree_it_did_read_says_how_many_it_found(self):
        code, said = run(tree([KNOWN, ("X2", "accepted", "")]))
        self.assertEqual(code, 0)
        self.assertIn("2 accepted features", said)


class WhatItRefuses(unittest.TestCase):
    def test_an_accepted_feature_requiring_a_draft(self):
        code, said = run(tree([KNOWN, ("X2", "accepted", "requires: [X3]\n"), ("X3", "draft", "")]))
        self.assertEqual(code, 1)
        self.assertIn("X2 is accepted and requires X3, which is draft", said)

    def test_an_accepted_feature_requiring_one_the_spec_moved_on_from(self):
        for status in ("superseded", "withdrawn"):
            with self.subTest(status=status):
                code, said = run(
                    tree([KNOWN, ("X2", "accepted", "requires: [X3]\n"), ("X3", status, "")])
                )
                self.assertEqual(code, 1)
                self.assertIn(f"which is {status}", said)

    def test_an_accepted_feature_requiring_one_that_is_not_here(self):
        code, said = run(tree([KNOWN, ("X2", "accepted", "requires: [X9]\n")]))
        self.assertEqual(code, 1)
        self.assertIn("which is not a feature here", said)

    def test_every_unmet_requirement_is_named_in_one_run(self):
        code, said = run(
            tree(
                [
                    KNOWN,
                    ("X2", "accepted", "requires: [X3, X4]\n"),
                    ("X3", "draft", ""),
                    ("X4", "withdrawn", ""),
                ]
            )
        )
        self.assertEqual(code, 1)
        self.assertIn("requires X3", said)
        self.assertIn("requires X4", said)
        self.assertIn("2 feature(s)", said)


class WhatItLeavesAlone(unittest.TestCase):
    def test_an_accepted_feature_may_rest_on_an_accepted_one(self):
        # The ordinary case, and the one a gate is most likely to get wrong in the
        # direction nobody notices: a rule that refuses everything is as useless as
        # one that refuses nothing, and only this says which of the two this is.
        code, said = run(tree([KNOWN, ("X2", "accepted", "requires: [X3]\n"), ("X3", "accepted", "")]))
        self.assertEqual(code, 0)
        self.assertIn("none resting on a draft", said)

    def test_a_draft_feature_may_rest_on_anything(self):
        code, _ = run(tree([KNOWN, ("X2", "draft", "requires: [X3]\n"), ("X3", "draft", "")]))
        self.assertEqual(code, 0)

    def test_relates_is_read_by_nobody(self):
        code, _ = run(tree([KNOWN, ("X2", "accepted", "relates: [X3]\n"), ("X3", "draft", "")]))
        self.assertEqual(code, 0)

    def test_an_empty_requires_is_not_a_requirement(self):
        code, _ = run(tree([KNOWN, ("X2", "accepted", "requires: []\n")]))
        self.assertEqual(code, 0)

    def test_a_file_with_no_id_or_status_is_skipped_rather_than_guessed_at(self):
        root = tree([KNOWN])
        (root / gate.FEATURES / "x-area" / "readme.md").write_text(
            "# Not a feature\n", encoding="utf-8"
        )
        code, said = run(root)
        self.assertEqual(code, 0)
        self.assertIn("1 accepted features", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
