#!/usr/bin/env python3
"""Every file that decides something is either measured by the coverage gate or
declared as not.

The gate reports a percentage of what `.coveragerc` points it at, and nothing
read that configuration against the directories it describes. So a script could
be added, gate a merge, and be measured by nothing — the run would say 100% and
mean it, about the other files. `submodule_pins.py` came within one line of
landing that way.

That is the same shape as a guard reading four of nine pinned repositories: the
answer is true about what it looked at and silent about the rest, and silence
reads as a pass.

There were two ways to be silent, and `.coveragerc` has since closed the first.
Under `include`, a file nothing imported was absent from the report altogether;
`what_is_blocking.py` sat in that list with a suite of eighty-three tests that no
workflow ran, and the report was 100% of the files that did run. `source` reports
such a file at 0% instead, so a suite that stops being run fails the gate rather
than disappearing from it. What is left to check here is the second way: that the
declared exceptions are declared, with reasons, and that the two lists agree.

What this asks is not that everything be covered. Several scripts have no suite
yet, deliberately, and saying so is the point — a script leaves the `UNMEASURED`
table by gaining a suite and leaving `.coveragerc`'s `omit`, and a new script
cannot avoid the question, because arriving in neither place fails here.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_coverage_reads_every_script.py
"""

from __future__ import annotations

import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

# Where this repository keeps code that decides something. `scripts/` is its own
# tooling; `shared/gates/` is the canonical copy of a gate every other repository
# carries, so a line uncovered there is uncovered in six repositories at once —
# which is the better reason of the two to measure it, and it was the one this
# file did not look at.
DIRECTORIES = ("scripts", "shared/gates")

# Scripts with no suite holding them at 100%, and why each is still out.
#
# Not a licence to skip one: an entry is a debt with a name on it. What decides
# whether that is acceptable is what the script would do wrong unnoticed, so each
# reason says what it gates rather than merely that it is small.
UNMEASURED = {
    "scripts/gen_board.py": "generates the board the integrity job diffs, so a "
    "wrong answer is caught there rather than here",
    "scripts/gen_codeowners.py": "generates a file the forge validates on push",
    "scripts/gen_roadmap_table.py": "generates a table the integrity job diffs",
    "scripts/rfc_scaffold.py": "writes a new RFC on request; gates nothing",
}

# The one `omit` entry that is a pattern rather than a file: the suites are not
# the subject of their own measurement. Named here so the reading below can tell
# a deliberate pattern from a file it failed to find.
SUITES = "scripts/test_*.py"


def _section(name: str) -> list[str]:
    """The indented values under one `.coveragerc` key, in order."""
    found: list[str] = []
    inside = False
    for raw in (ROOT / ".coveragerc").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") or (line and not raw.startswith(" ") and inside):
            inside = False
        if line.startswith(f"{name} ") or line == name or line.startswith(f"{name}="):
            inside = True
            continue
        if inside and line:
            found.append(line)
    return found


def sourced() -> set[str]:
    """The directories the gate measures."""
    return set(_section("source"))


def excused() -> set[str]:
    """The named files `omit` excuses, patterns left aside."""
    return {one for one in _section("omit") if "*" not in one}


def patterns() -> set[str]:
    """The wildcards `omit` carries."""
    return {one for one in _section("omit") if "*" in one}


def present() -> set[str]:
    """Every file in those directories that is not itself a suite."""
    return {
        f"{directory}/{path.name}"
        for directory in DIRECTORIES
        for path in (ROOT / directory).glob("*.py")
        if not path.name.startswith("test_")
    }


class CoverageReadsEveryScript(unittest.TestCase):
    def test_the_configuration_was_read(self):
        """Assert what is being read before what it says.

        A parser that quietly returned nothing would make every test below pass:
        nothing would be excused, so nothing could be excused-and-undeclared, and
        the accounting would balance at zero. That is the failure this whole file
        exists to catch, one level down.
        """
        self.assertEqual(sourced(), set(DIRECTORIES), "the source list did not parse")
        self.assertIn(
            "scripts/gen_board.py", excused(), "the omit list parsed but not as paths"
        )

    def test_the_suites_are_not_their_own_subject(self):
        """Without this pattern every `test_*.py` becomes a measured file, and a
        suite is not a thing whose own lines the gate has an opinion about."""
        self.assertIn(SUITES, patterns())

    def test_there_are_scripts_to_account_for(self):
        """The same question asked of the directories."""
        self.assertGreater(
            len(present()), 10, "the script directories did not enumerate"
        )

    def test_every_directory_holding_code_is_read(self):
        """A directory that enumerates to nothing accounts for nothing, and says
        so in exactly the voice of a directory whose files are all measured."""
        for directory in DIRECTORIES:
            with self.subTest(directory=directory):
                self.assertTrue(
                    any(one.startswith(f"{directory}/") for one in present()),
                    f"{directory} holds no file this accounts for",
                )

    def test_every_excused_script_is_declared(self):
        """The claim. A script dropped out of measurement without a reason beside
        it is the gate quietly narrowing, which is what it must never do."""
        undeclared = excused() - set(UNMEASURED)
        self.assertEqual(
            undeclared,
            set(),
            "these are omitted from .coveragerc and declared nowhere above, so "
            f"the gate says nothing about them and nobody said why: {sorted(undeclared)}",
        )

    def test_every_declared_script_is_actually_excused(self):
        """The other direction. A name here that `.coveragerc` does not omit reads
        as a debt that is still outstanding when it has in fact been paid — and
        worse, hides that the file is now being measured by the gate."""
        measured = set(UNMEASURED) - excused()
        self.assertEqual(
            measured,
            set(),
            f"declared unmeasured while .coveragerc measures them: {sorted(measured)}",
        )

    def test_nothing_is_declared_for_a_script_that_is_gone(self):
        """A deleted script leaves an entry that reads as a live debt."""
        stale = set(UNMEASURED) - present()
        self.assertEqual(
            stale, set(), f"declared unmeasured but not here: {sorted(stale)}"
        )

    def test_the_omit_list_names_only_scripts_that_exist(self):
        """An omitted file that is gone leaves an exception nothing needs, and the
        next reader cannot tell it from one that is still load-bearing."""
        missing = excused() - present()
        self.assertEqual(
            missing, set(), f"named in .coveragerc but not here: {sorted(missing)}"
        )

    def test_every_reason_says_something(self):
        """An entry with no reason records that somebody skipped it, and nothing
        about why — which is what the next reader needs to decide it is still
        acceptable. The same floor the acknowledgement register is held to."""
        thin = sorted(
            name for name, why in UNMEASURED.items() if len(why.split()) < 4
        )
        self.assertEqual(thin, [], f"these give no reason worth reading: {thin}")


if __name__ == "__main__":
    unittest.main()
