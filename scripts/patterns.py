"""What every gate in this directory is looking for, written once.

These scripts read the same things out of the same prose: a requirement defined
in a table, a requirement cited somewhere, an ADR filename, a `Spec:` trailer.
Each had written its own pattern for it — the definition four times, the citation
four times, the trailer four times in two spellings — and two of them had already
drifted apart.

That matters more here than it would elsewhere, because these scripts are the
gates. Two of them reading *nearly* the same pattern is how one comes to accept
what the other refuses, and neither is wrong on its own terms. `status_lint`
building a ceiling from citations while `integrity` checked definitions is
exactly that, and it composed correctly only by accident.

Importing across scripts works under the invocation CI uses: CPython puts a
script's own directory on `sys.path`, so `python3 .spec-canonical/scripts/x.py`
finds this from any working directory.
"""

import re

# A requirement, defined: the table row that brings it into being.
REQ_DEF = re.compile(r"^\|\s*\*\*([A-Z]+\d*-R\d+)\*\*\s*\|", re.MULTILINE)

# The same row, keeping the text as well, for the gates that read what it says.
REQ_DEF_ROW = re.compile(r"^\|\s*\*\*([A-Z]+\d*-R\d+)\*\*\s*\|([^|]*)\|", re.MULTILINE)

# A requirement, cited: a mention of one anywhere in prose.
CITE = re.compile(r"\b([A-Z]+\d*-R\d+)\b")

# A citation of either kind, for the gates that check both.
#
# The requirement half is `CITE`'s, deliberately. One of the two copies this
# replaces bounded the prefix at four characters and the number at four digits,
# which is true of every identifier today and is a rule nobody wrote down.
CITE_ANY = re.compile(r"\b([A-Z]+\d*-R\d+|ADR-\d{3,4})\b")

# A range of requirements, as a tracker writes one: `B1-R2..R7`.
RANGE = re.compile(r"\b([A-Z]+\d*)-R(\d+)\.\.(?:[A-Z]+\d*-)?R?(\d+)\b")

# An ADR, by its filename.
ADR_FILE = re.compile(r"^0*(\d{3,4})-.*\.md$")

# An ADR, cited.
ADR_CITE = re.compile(r"\bADR-(\d{3,4})\b")

# What a tracker row names where the work landed without a trailer to cite it.
#
# A commit cannot gain a `Spec:` trailer after it is merged, so a goal finished by
# somebody who wrote one trailer for a change closing several requirements has no
# way to be cited afterwards — and a later commit citing it without advancing it is
# exactly the unauditable claim the gate exists to refuse. This is the way out, and
# it is deliberately a **commit** rather than a pull request: a sha can be checked
# against the repository itself, offline, and `git show` is the audit.
LANDED = re.compile(r"landed in `([0-9a-f]{7,40})`")

# The trailer a commit or a pull request cites the specification with.
SPEC_TRAILER = re.compile(r"^[ \t]*Spec:[ \t]*(\S.*)$", re.MULTILINE | re.IGNORECASE)

# A version, as the manifests and the tracker write one.
VERSION = re.compile(r"^\d+\.\d+\.\d+$")

# A git ref that is safe to hand to a command is deliberately *not* here.
# `commit_lint` and `dco_check` each validate their arguments against one before
# reaching a subprocess, and the analysis that checks such a call cannot follow a
# pattern imported from elsewhere — so importing it reported both guarded calls
# as unguarded. A validation is worth keeping where the thing it validates is.
