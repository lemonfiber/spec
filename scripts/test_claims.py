#!/usr/bin/env python3
"""Whether a bot opened a pull request, as the board marks it.

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
BOT = {"author": {"login": "dependabot", "__typename": "Bot"}}


class Claims(unittest.TestCase):
    def test_a_bot_is_known_by_its_author(self):
        self.assertTrue(claims.is_bot(BOT))
        self.assertFalse(claims.is_bot(PERSON))
        self.assertFalse(claims.is_bot({"author": None}))
        self.assertFalse(claims.is_bot({}))


if __name__ == "__main__":
    unittest.main()
