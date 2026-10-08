#!/usr/bin/env python3
"""What counts against the cap, and which repositories are over it — GOV-R58.

Stdlib unittest.
Run:  python3 scripts/test_claims.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claims  # noqa: E402

PERSON = {"author": {"login": "p", "__typename": "User"}}
GRAPHQL_BOT = {"author": {"login": "dependabot", "__typename": "Bot"}}
REST_BOT = {"user": {"login": "release-train[bot]", "type": "Bot"}}
REST_PERSON = {"user": {"login": "p", "type": "User"}}


class Claims(unittest.TestCase):
    def test_a_bot_in_either_shape(self):
        self.assertTrue(claims.is_bot(GRAPHQL_BOT))
        self.assertTrue(claims.is_bot(REST_BOT))
        self.assertFalse(claims.is_bot(PERSON))
        self.assertFalse(claims.is_bot(REST_PERSON))
        self.assertFalse(claims.is_bot({"author": None}))

    def test_bots_are_not_counted(self):
        self.assertEqual(claims.counted([PERSON, GRAPHQL_BOT, REST_PERSON, REST_BOT]), 2)

    def test_only_a_repository_past_the_cap_is_over_it(self):
        prs = {"core": [PERSON] * (claims.CAP + 1) + [GRAPHQL_BOT],
               "web": [PERSON] * claims.CAP + [GRAPHQL_BOT] * 3}
        self.assertEqual(claims.over_cap(prs), {"core": claims.CAP + 1})


if __name__ == "__main__":
    unittest.main()
