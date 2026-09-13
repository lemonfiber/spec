#!/usr/bin/env python3
"""Every comment that writes the lifecycle out writes all of it — OPS-R32.

A manifest's `status` line is documented three times, each as the same shape: the
value, then a comment listing the states a version moves through. They are for a
reader rather than for a parser, which is exactly why they drift — nothing had
ever read them, and `70-operations/versions/README.md` had been missing
`in_progress` for long enough that the tooling and the contract disagreed about
what a manifest may say.

This reads the chain out of that comment wherever the shape appears and holds it
to `patterns.STATES`. Structural rather than prose-matching: what is matched is a
`status = "..."` assignment followed by an arrow-joined chain, not a sentence
about releases. `OPS-R32` states the same lifecycle in prose and is deliberately
not matched — it says which transitions are required and which are optional,
which is a different claim from "here is every state", and a rule that conflated
the two would refuse the requirement for being precise.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_release_states.py
"""

from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from patterns import IN_FLIGHT, STATES

ROOT = pathlib.Path(__file__).resolve().parent.parent

# A documented manifest status: the assignment, then the chain a reader is given.
DOCUMENTED = re.compile(r'^status\s*=\s*"[a-z_]+"\s*#\s*([a-z_]+(?:\s*→\s*[a-z_]+)+)', re.MULTILINE)


def chains() -> list[tuple[str, tuple[str, ...]]]:
    """Every written-out lifecycle under `70-operations`, against its file."""
    found: list[tuple[str, tuple[str, ...]]] = []
    for path in sorted((ROOT / "70-operations").rglob("*")):
        if path.suffix not in (".md", ".toml"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for chain in DOCUMENTED.findall(text):
            found.append(
                (str(path.relative_to(ROOT)), tuple(s.strip() for s in chain.split("→")))
            )
    return found


class TheLifecycleIsWrittenOnce(unittest.TestCase):
    def test_the_chains_were_found(self):
        """Assert the reading before what it says.

        A pattern that matched nothing would pass every test below by having
        nothing to disagree with — the shape this whole file exists to catch,
        one level down.
        """
        self.assertGreaterEqual(
            len(chains()), 3, "no documented lifecycle was found to check"
        )

    def test_every_documented_chain_is_every_state_in_order(self):
        for where, chain in chains():
            with self.subTest(where=where):
                self.assertEqual(
                    chain,
                    STATES,
                    f"{where} writes the lifecycle out and does not match "
                    "patterns.STATES — a reader following it will write a status "
                    "the tooling refuses, or skip one it accepts",
                )

    def test_the_states_in_flight_are_states(self):
        """The subset is a subset.

        `IN_FLIGHT` is the answer to "is this the version being worked on", and it
        is three of these six. A typo there would not fail anywhere else: a state
        nothing matches simply never selects a manifest, and the gates go quiet
        rather than wrong.
        """
        self.assertEqual(tuple(s for s in STATES if s in IN_FLIGHT), IN_FLIGHT)


if __name__ == "__main__":
    unittest.main()
