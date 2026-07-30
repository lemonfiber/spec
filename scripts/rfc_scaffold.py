#!/usr/bin/env python3
"""Scaffold a Draft feature stub from an approved RFC issue and open its spec PR.

Run only by the maintainer-gated ``rfc-scaffold`` workflow (GOV-R41). The issue's
fields arrive as environment variables and are untrusted (GOV-R43): they are never
interpolated into a shell; the destination path is built solely from the validated
area, the generated id, and the integer issue number (no field ever forms a path);
the proposal text is quoted verbatim inside fenced blocks so it cannot inject
markdown; and the PR is opened via ``gh api --input`` so no field is ever a command
argument. The stub is always ``status: draft`` — never Accepted (GOV-R42).
"""
import os
import re
import glob
import json
import subprocess
import sys
import pathlib

AREA_DIR = {
    "A": "a-getting-started", "B": "b-running", "C": "c-trust", "D": "d-content",
    "E": "e-maintenance", "F": "f-extensibility", "G": "g-ux", "H": "h-glue",
    "I": "i-remote-access", "J": "j-runtime", "K": "k-observability",
}
AREA_NAME = {
    "A": "Getting started", "B": "Running it", "C": "Trust & correctness",
    "D": "Content & household", "E": "Maintenance", "F": "Extensibility",
    "G": "Cross-cutting UX", "H": "Ecosystem glue", "I": "Remote access & identity",
    "J": "Runtime & platform", "K": "Observability",
}


def field(body, label):
    match = re.search(
        rf"^###\s+{re.escape(label)}\s*\n+(.*?)(?=\n###\s|\Z)", body, re.S | re.M
    )
    return match.group(1).strip() if match else ""


def next_id(area):
    nums = []
    for path in glob.glob(f"10-functional/features/{AREA_DIR[area]}/*.md"):
        m = re.match(r"[a-k](\d+)-", pathlib.Path(path).stem)
        if m:
            nums.append(int(m.group(1)))
    return f"{area}{max(nums) + 1 if nums else 1}"


def fence(text):
    return "```text\n" + (text or "(none provided)").replace("```", "` ` `") + "\n```"


def run(*args):
    subprocess.run(list(args), check=True)


def main():
    env = os.environ
    body, num = env["ISSUE_BODY"], env["ISSUE_NUMBER"]
    url, repo = env["ISSUE_URL"], env["REPO"]
    if not re.fullmatch(r"\d+", num):
        print("::error::issue number is not numeric")
        return 1
    num = str(int(num))  # normalise through int so it can never be a path fragment
    area = (field(body, "Area")[:1] or "").upper()
    if area not in AREA_DIR:
        print(f"::error::RFC area is not one of A-K (got '{field(body, 'Area')}')")
        return 1

    fid = next_id(area)
    ptitle = (field(body, "Proposal title") or env.get("ISSUE_TITLE", "RFC")).replace("\n", " ")
    yaml_title = "'" + ptitle.replace("'", "''") + "'"
    path = f"10-functional/features/{AREA_DIR[area]}/{fid.lower()}-rfc{num}.md"

    stub = f"""---
id: {fid}
title: {yaml_title}
kind: feature
area: {area}
audience: operator
status: draft
tracks: v2
---

# {fid} — RFC draft (from #{num})

**Status:** Draft · **Audience:** Operator · **Area:** {area} — {AREA_NAME[area]}

---

> Scaffolded from RFC [#{num}]({url}) on maintainer approval. This is a **Draft** —
> not binding, not citable — for a maintainer to refine into a proper feature
> before it is Accepted. The proposal is quoted verbatim below.

## Purpose

The problem this proposal addresses:

{fence(field(body, "The problem"))}

## Behaviour

The proposed behaviour, as submitted:

{fence(field(body, "Proposed behaviour"))}

### Rationale & alternatives

{fence(field(body, "Rationale & alternatives"))}

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **{fid}-R1** | The behaviour proposed in RFC [#{num}]({url}) MUST be specified as testable acceptance criteria before this feature is marked Accepted. |

## Related

- RFC [#{num}]({url}) — the proposal this drafts
"""
    pathlib.Path(path).write_text(stub, encoding="utf-8")

    branch = f"rfc/{num}"
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "switch", "-c", branch)
    run("git", "add", path)
    run("git", "commit", "-s", "-m", f"docs(rfc): scaffold Draft {fid} from RFC #{num}",
        "-m", f"Auto-scaffolded on maintainer approval of #{num}. Draft, not binding.")
    run("git", "push", "-u", "origin", branch)

    pr = {
        "title": f"RFC #{num}: Draft {fid} — {ptitle}"[:120],
        "head": branch,
        "base": "main",
        "body": (
            f"Scaffolded from RFC #{num} on maintainer approval (GOV-R42).\n\n"
            f"Draft {fid} for review — refine into a proper feature before it is "
            f"Accepted.\n\nCloses #{num} on merge.\n\nSpec: GOV-R42"
        ),
    }
    pathlib.Path("/tmp/rfc_pr.json").write_text(json.dumps(pr), encoding="utf-8")
    run("gh", "api", f"repos/{repo}/pulls", "--input", "/tmp/rfc_pr.json")
    print(f"scaffolded {path} on {branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
