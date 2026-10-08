#!/usr/bin/env python3
"""Write the RFC form's area options from the catalogue's page.

The form asks which feature area a proposal belongs to, and `rfc_convert.py`
refuses a letter the catalogue does not head a section for. A list typed into
the form is a list that misses the next area, so the options are the catalogue's
areas, in letter order, as `A — Getting started`.

Run:  python3 scripts/gen_rfc_areas.py
"""

from __future__ import annotations

import pathlib
import re
import sys

from catalogue import FEATURES_README
from catalogue import areas as area_names

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "rfc.yml"

#: The area dropdown's options, found by the field's id rather than a marker.
OPTIONS = re.compile(r"(^    id: area\n(?:    .*\n)*?      options:\n)((?:        - .*\n)+)", re.MULTILINE)


class Refused(Exception):
    """The form or the catalogue is not in the shape this writes."""


def options(names: dict[str, str]) -> str:
    """The dropdown's option lines, one per area, in letter order."""
    if not names:
        raise Refused(f"{FEATURES_README} heads no area section")
    return "".join(f'        - "{letter} — {name}"\n' for letter, name in sorted(names.items()))


def written(form: str, names: dict[str, str]) -> str:
    """The form with its area options replaced."""
    found = OPTIONS.search(form)
    if found is None:
        raise Refused(f"{FORM.relative_to(ROOT)} has no `area` dropdown with options")
    return form[: found.start(2)] + options(names) + form[found.end(2) :]


def main() -> int:
    try:
        names = area_names((ROOT / FEATURES_README).read_text(encoding="utf-8"))
        FORM.write_text(written(FORM.read_text(encoding="utf-8"), names), encoding="utf-8")
    except Refused as refused:
        print(f"gen_rfc_areas: {refused}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
