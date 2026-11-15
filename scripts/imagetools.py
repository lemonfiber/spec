"""How spec's scripts ask `docker buildx imagetools inspect` what a registry holds.

A registry holds no such reference only where it says so: not found, manifest
unknown or name unknown. Any other failure is a registry that did not answer, a
rate limit, a server error or the network among them. It is asked again, waiting
longer each time, and once every attempt has failed the reference could not be
checked, which no gate reports as unpublished.
"""

from __future__ import annotations

import re
import subprocess
import time

#: How often a registry that did not answer is asked in all, how long the first wait
#: before asking again is, and what each wait is multiplied by for the next.
ATTEMPTS = 4
FIRST_WAIT_S = 5
BACKOFF = 3

#: What a registry says where it holds no such image, tag or digest.
ABSENT = re.compile(r"not found|manifest unknown|name unknown", re.IGNORECASE)


class Absent(Exception):
    """The registry says it holds no such reference; the message is the last line it said."""


class Unanswered(Exception):
    """The registry did not say whether it holds a reference, however often it was asked."""


def manifest(reference: str) -> str:
    """The index descriptor the registry answers for `reference`, as the JSON it printed."""
    wait = FIRST_WAIT_S
    for attempt in range(1, ATTEMPTS + 1):
        asked = subprocess.run(
            ["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{json .Manifest}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if asked.returncode == 0:
            return asked.stdout
        said = (asked.stderr.strip() or asked.stdout.strip()).splitlines()
        last = said[-1] if said else f"exit {asked.returncode}"
        if ABSENT.search(" ".join(said)):
            raise Absent(last)
        if attempt < ATTEMPTS:
            time.sleep(wait)
            wait *= BACKOFF
    raise Unanswered(f"{reference} could not be checked: its registry did not answer in {ATTEMPTS} attempts ({last})")
