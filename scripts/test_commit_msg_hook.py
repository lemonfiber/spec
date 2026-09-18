#!/usr/bin/env python3
"""The commit-msg hook refuses what CI refuses, and nothing more (GOV-R46, Q-R57).

Two things are held here, and the second is the one that decays quietly.

**It refuses the trailer, and lets the three near-misses through.** The hook is
shell, so it is driven as shell: a message file in, an exit status out. What is
worth driving is not that it catches the obvious case — that is one grep — but
that it does not catch prose, a trailer quoted one indent in, or a co-author who
is a person. Each of those is a false refusal, and a false refusal teaches
somebody to pass `--no-verify`, which switches off the other three checks with
it. A hook people bypass enforces nothing (`Q-R57`, `OPS-R51`).

**Its list of assistants is `attribution_check.py`'s.** A POSIX shell cannot read
a Python tuple and this hook has to run where `python3` does not, so the names
are spelled in both places. The two directions of drift are not the same fault: a
name in the check and not in the hook is a trailer CI refuses after a push that
the hook would have caught before one — an annoyance; a name in the hook and not
in the check is a hook refusing something no gate does, which `Q-R57` forbids
outright. Nothing else compares the two lists, so this does.

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
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import attribution_check as CHECK

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "shared" / "hooks" / "commit-msg"

# What the hook says when it refuses for this reason. Matched rather than the
# exit status alone: the hook has four checks and every one of them exits 1, so a
# message refused for a missing sign-off would otherwise read as a pass here.
SAID = "credits a tool"


def message(extra: str = "") -> str:
    """A message the hook's other three checks are content with.

    Conventional subject, a citation and a sign-off, so whatever a case is about
    is the only thing that can be wrong with it.
    """
    return (
        "feat: a thing\n\nWhy this happened.\n\n"
        f"{extra}\n"
        "Spec: GOV-R46\n"
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


class WhatItRefuses(unittest.TestCase):
    def test_a_co_author_trailer_naming_an_assistant(self) -> None:
        code, said = refused(message("Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"))
        self.assertEqual(code, 1, said)
        self.assertIn(SAID, said)

    def test_the_trailer_whatever_its_casing(self) -> None:
        # Git treats the trailer name case-insensitively and so do the tools that
        # write it, so a hook matching one spelling catches one tool.
        for spelling in ("Co-authored-by", "Co-Authored-By", "co-authored-by"):
            with self.subTest(spelling=spelling):
                code, said = refused(message(f"{spelling}: Copilot <copilot@github.com>"))
                self.assertEqual(code, 1, said)
                self.assertIn(SAID, said)

    def test_every_assistant_the_check_names(self) -> None:
        # The list is the point of the file above; this is the list being used.
        for name in CHECK.ASSISTANTS:
            with self.subTest(name=name):
                code, said = refused(message(f"Co-authored-by: {name} <x@example.com>"))
                self.assertEqual(code, 1, said)
                self.assertIn(SAID, said)


class WhatItMustLetThrough(unittest.TestCase):
    """The three ways a hook like this gets switched off."""

    def test_a_co_author_who_is_a_person(self) -> None:
        code, said = refused(message("Co-authored-by: Wessel Verheij <info@nightworks.io>"))
        self.assertEqual(code, 0, said)

    def test_prose_naming_what_is_forbidden(self) -> None:
        code, said = refused(message("This removes the Claude trailer from every commit."))
        self.assertEqual(code, 0, said)

    def test_a_trailer_quoted_one_indent_in(self) -> None:
        # How a message shows somebody the line to remove. A trailer git will
        # read starts the line; a quoted one does not.
        code, said = refused(message("  Co-authored-by: Claude <noreply@anthropic.com>"))
        self.assertEqual(code, 0, said)

    def test_an_ordinary_message(self) -> None:
        code, said = refused(message())
        self.assertEqual(code, 0, said)

    def test_it_still_refuses_what_it_always_refused(self) -> None:
        # The check added last must not be the only one left running: a `set -eu`
        # script gains a way to exit early every time something is added to it.
        code, said = refused("a subject with no type\n\nSpec: GOV-R46\n")
        self.assertEqual(code, 1, said)
        self.assertIn("not conventional", said)
        self.assertIn("no sign-off", said)
        self.assertNotIn(SAID, said)


class TheTwoListsAgree(unittest.TestCase):
    """The duplication, checked rather than merely confessed to."""

    def named(self) -> list[str]:
        """The assistants the hook spells, read out of the hook itself."""
        found = re.search(
            r'^assistants="([^"]+)"$', HOOK.read_text(encoding="utf-8"), re.MULTILINE
        )
        if found is None:
            self.fail("the hook no longer spells its list where this reads it")
        return found.group(1).split("|")

    def test_the_hook_names_exactly_what_the_check_names(self) -> None:
        self.assertEqual(
            self.named(),
            list(CHECK.ASSISTANTS),
            "the hook and attribution_check.py disagree about who counts as a tool; "
            "a name in one and not the other is either a trailer the hook waves "
            "through or a refusal no gate in CI would make (Q-R57)",
        )

    def test_the_list_was_actually_read(self) -> None:
        """Assert what is being read before what it says.

        A regex that quietly matched nothing would make the comparison above pass
        against an empty hook — which is the failure this file exists to catch,
        one level down.
        """
        self.assertIn("claude", self.named())
        self.assertGreater(len(self.named()), 5)



#: The contributing document's table of what a commit message has to carry.
#: A row names a requirement in bold and the check that enforces it in backticks.
RULE_ROW = re.compile(
    r"^\| [^|]*\(\*\*([A-Z0-9-]+)\*\*\) \| [^|]+ \| `([a-z-]+)` \|$", re.MULTILINE
)

#: One edit to an acceptable message for each check, taking that rule away and
#: nothing else. The keys are what the document is held to naming.
BREAKS = {
    "commitlint": lambda text: text.replace("feat: a thing", "a thing"),
    "dco": lambda text: re.sub(r"^Signed-off-by:.*\n", "", text, flags=re.MULTILINE),
    "spec-check": lambda text: re.sub(r"^Spec:.*\n", "", text, flags=re.MULTILINE),
    "attribution": lambda text: text + "Co-authored-by: Claude <x@example.com>\n",
}


class TheDocumentAndTheHookAgree(unittest.TestCase):
    """The four rules, stated in one place and enforced in another.

    Before this, no document stated all four. Three did not mention the
    conventional subject, none of them mentioned `GOV-R46`, and the only artefact
    naming the whole set was this hook — which a contributor reads after it has
    refused them. The document now names them, and a document naming a rule that
    has moved is worse than one naming none, so the two are compared.
    """

    def stated(self) -> dict[str, str]:
        """{check: requirement} as the contributing document states it."""
        found = RULE_ROW.findall(
            (ROOT / "50-governance" / "contributing.md").read_text(encoding="utf-8")
        )
        return {check: rule for rule, check in found}

    def test_the_table_was_actually_read(self) -> None:
        """What is being read, before what it says.

        A pattern that matched nothing would make the comparison below pass
        against a document that states no rule at all, which is the state this
        exists to end.
        """
        self.assertIn(
            "attribution",
            self.stated(),
            "50-governance/contributing.md no longer holds the table of commit "
            "rules where this reads it, so the four rules are stated nowhere and "
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
