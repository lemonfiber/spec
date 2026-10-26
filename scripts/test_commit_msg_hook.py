#!/usr/bin/env python3
"""The commit-msg hook refuses what CI refuses, and nothing more (Q-R57).

The hook is shell, so it is driven as shell: a message file in, an exit status
out. It holds a conventional subject, a sign-off and a `Spec:` citation, each
the one CI reads, and lets through what CI lets through: a refusal no gate
makes teaches somebody to pass `--no-verify`, which switches off every check it
runs. A hook people bypass enforces nothing (`Q-R57`, `OPS-R51`).

Driven against the canonical copy under `shared/hooks/`. The copy this repository
carries in `.githooks/` is held to it byte for byte by `check_shared_files.py`,
which is where that comparison belongs.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_commit_msg_hook.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "shared" / "hooks" / "commit-msg"

def message(extra: str = "") -> str:
    """A message every check of the hook is content with.

    Conventional subject, a citation and a sign-off, so whatever a case is about
    is the only thing that can be wrong with it.
    """
    return (
        "feat: a thing\n\nWhy this happened.\n\n"
        f"{extra}\n"
        "Spec: GOV-R12\n"
        "Signed-off-by: A Person <a@example.com>\n"
    )


def refused(text: str) -> tuple[int, str]:
    """The hook run against this message: its exit status and what it said."""
    with tempfile.TemporaryDirectory() as where:
        path = pathlib.Path(where) / "COMMIT_EDITMSG"
        path.write_text(text, encoding="utf-8")
        done = subprocess.run(
            ["sh", str(HOOK), str(path)], capture_output=True, text=True
        )
    return done.returncode, done.stdout + done.stderr


class WhatItLetsThrough(unittest.TestCase):
    def test_an_ordinary_message(self) -> None:
        code, said = refused(message())
        self.assertEqual(code, 0, said)

    def test_a_co_author(self) -> None:
        code, said = refused(message("Co-authored-by: Wessel Verheij <info@nightworks.io>"))
        self.assertEqual(code, 0, said)


class WhatItRefuses(unittest.TestCase):
    def test_every_check_at_once(self) -> None:
        # A `set -eu` script gains a way to exit early every time something is
        # added to it, so one message breaking all three is refused for all three.
        code, said = refused("a subject with no type\n\nWhy.\n")
        self.assertEqual(code, 1, said)
        self.assertIn("not conventional", said)
        self.assertIn("no sign-off", said)
        self.assertIn("no specification citation", said)


#: The contributing document's table of what a commit message has to carry.
#: A row names a requirement in bold and the check that enforces it in backticks.
RULE_ROW = re.compile(
    r"^\| [^|]*\(\*\*([A-Z0-9-]+)\*\*\) \| [^|]+ \| `([a-z-]+)` \|$", re.MULTILINE
)

#: The heading that section opens with.
COMMIT_SECTION = "## What a commit message has to carry"

#: One edit to an acceptable message for each check, taking that rule away and
#: nothing else. The keys are what the document is held to naming.
BREAKS = {
    "commitlint": lambda text: text.replace("feat: a thing", "a thing"),
    "dco": lambda text: re.sub(r"^Signed-off-by:.*\n", "", text, flags=re.MULTILINE),
    "spec-check": lambda text: re.sub(r"^Spec:.*\n", "", text, flags=re.MULTILINE),
}


class TheDocumentAndTheHookAgree(unittest.TestCase):
    """The rules, stated in one place and enforced in another.

    The contributing document names every rule the hook refuses for, so a
    contributor reads them before the hook refuses them, and a document naming a
    rule that has moved is worse than one naming none, so the two are compared.
    """

    def stated(self) -> dict[str, str]:
        """{check: requirement} as the contributing document states it.

        Read from the commit message's section alone. The page's table of what a
        pull request carries is shaped the same, and its check reads the body,
        which no commit hook sees.
        """
        text = (ROOT / "50-governance" / "contributing.md").read_text(encoding="utf-8")
        _, _, section = text.partition(COMMIT_SECTION)
        found = RULE_ROW.findall(section.split("\n### ", 1)[0])
        return {check: rule for rule, check in found}

    def test_the_table_was_actually_read(self) -> None:
        """What is being read, before what it says.

        A pattern that matched nothing would make the comparison below pass
        against a document that states no rule at all, which is the state this
        exists to end.
        """
        self.assertIn(
            "dco",
            self.stated(),
            "50-governance/contributing.md no longer holds the table of commit "
            "rules where this reads it, so the rules are stated nowhere and "
            "nothing compared them against the hook",
        )

    def test_it_names_every_check_the_hook_runs(self) -> None:
        self.assertEqual(
            sorted(self.stated()),
            sorted(BREAKS),
            "the document and the hook disagree about what a commit message has "
            "to carry; a rule the hook refuses for and no document states is the "
            "round trip this table exists to save",
        )

    def test_each_rule_it_states_is_one_the_hook_refuses_for(self) -> None:
        for check, requirement in sorted(self.stated().items()):
            with self.subTest(check=check, requirement=requirement):
                code, said = refused(BREAKS[check](message()))
                self.assertEqual(
                    code, 1,
                    f"the document says {check} enforces {requirement}, and the "
                    f"hook accepts a message that would fail it: {said}",
                )

if __name__ == "__main__":
    unittest.main()
