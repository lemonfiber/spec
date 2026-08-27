#!/usr/bin/env python3
"""Every script here is either measured by the coverage gate or declared as not.

The gate reports a percentage of the files `.coveragerc` names, and nothing read
that list against the directory it describes. So a script could be added, gate a
merge, and be measured by nothing — the run would say 100% and mean it, about the
other files. `submodule_pins.py` came within one line of landing that way.

That is the same shape as a guard reading four of nine pinned repositories: the
answer is true about what it looked at and silent about the rest, and silence
reads as a pass.

What this asks is not that everything be covered. Several scripts here have no
suite yet, deliberately, and saying so is the point — a script leaves this file's
`UNMEASURED` table by gaining a suite and an entry in `.coveragerc`, and a new
script cannot avoid the question, because arriving in neither place fails here.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_coverage_reads_every_script.py
"""

from __future__ import annotations

import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

# Scripts with no suite holding them at 100%, and why each is still out.
#
# Not a licence to skip one: an entry is a debt with a name on it. What decides
# whether that is acceptable is what the script would do wrong unnoticed, so each
# reason says what it gates rather than merely that it is small.
UNMEASURED = {
    "check_frontmatter.py": "gates a merge; wants a suite",
    "check_order.py": "gates a merge; wants a suite",
    "commit_lint.py": "gates a merge; wants a suite",
    "dco_check.py": "gates a merge; wants a suite",
    "spec_refs.py": "gates a merge; wants a suite",
    "gen_board.py": "generates the board the integrity job diffs, so a wrong "
    "answer is caught there rather than here",
    "gen_codeowners.py": "generates a file the forge validates on push",
    "gen_roadmap_table.py": "generates a table the integrity job diffs",
    "metafm.py": "read by the generators above, and exercised through them",
    "rfc_scaffold.py": "writes a new RFC on request; gates nothing",
}


def measured() -> set[str]:
    """The files `.coveragerc` names under `include`, by basename."""
    found: set[str] = set()
    inside = False
    for raw in (ROOT / ".coveragerc").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            inside = False
        if line.startswith("include"):
            inside = True
            continue
        if inside and line.startswith("scripts/"):
            found.add(line.removeprefix("scripts/"))
    return found


def present() -> set[str]:
    """Every script here that is not itself a suite."""
    return {
        path.name
        for path in SCRIPTS.glob("*.py")
        if not path.name.startswith("test_")
    }


class CoverageReadsEveryScript(unittest.TestCase):
    def test_the_include_list_was_read(self):
        """Assert what is being read before what it says.

        A parser that quietly returned nothing would make every test below pass:
        no file would be measured, so none could be measured-and-missing, and the
        accounting would balance at zero. That is the failure this whole file
        exists to catch, one level down.
        """
        self.assertGreater(
            len(measured()), 5, "the .coveragerc include list did not parse"
        )
        self.assertIn(
            "gate.py", measured(), "the include list parsed but not as paths"
        )

    def test_there_are_scripts_to_account_for(self):
        """The same question asked of the directory."""
        self.assertGreater(
            len(present()), 10, "the scripts directory did not enumerate"
        )

    def test_every_script_is_measured_or_declared(self):
        """The claim. A new script arriving in neither place fails here."""
        unaccounted = present() - measured() - set(UNMEASURED)
        self.assertEqual(
            unaccounted,
            set(),
            "these scripts are neither in .coveragerc's include list nor "
            "declared unmeasured above, so the gate says nothing about them: "
            f"{sorted(unaccounted)}",
        )

    def test_nothing_is_declared_unmeasured_and_measured(self):
        """A script cannot be both, and being in both hides which is true."""
        both = set(UNMEASURED) & measured()
        self.assertEqual(
            both,
            set(),
            f"declared unmeasured while .coveragerc measures them: {sorted(both)}",
        )

    def test_nothing_is_declared_for_a_script_that_is_gone(self):
        """A deleted script leaves an entry that reads as a live debt."""
        stale = set(UNMEASURED) - present()
        self.assertEqual(
            stale, set(), f"declared unmeasured but not here: {sorted(stale)}"
        )

    def test_the_include_list_names_only_scripts_that_exist(self):
        """A measured file that is gone leaves the gate reading one file fewer
        than it reports, and coverage.py does not complain about it."""
        missing = measured() - present()
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
