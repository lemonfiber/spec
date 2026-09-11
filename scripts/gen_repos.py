#!/usr/bin/env python3
"""Rewrite the repository table, and the sentence counting it, from the registry.

The table was prose maintained beside the pages it indexed, and it drifted the
way that always ends: `lemonfiber-companion` got a page under `30-repos/` and a
row in nothing, while the sentence below the table went on saying "Those eleven
are every repository in the org" through the day a twelfth was created.

Both are read from `30-repos/repos.toml` now, so neither can disagree with it or
with the other. The count is written as a word because that is how the sentence
reads; the generator does the conversion rather than asking anyone to.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

REGISTRY = pathlib.Path("30-repos/repos.toml")
README = pathlib.Path("30-repos/README.md")

#: Counting words, for a sentence that says "Those twelve" rather than "Those 12".
#: Stops at twenty because an org past twenty repositories has a different
#: problem, and a wrong word is better than a silently unwritten one — `count`
#: raises rather than falling back to a digit nobody reviewed.
WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
    17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
}

#: The diagram, found by its fence. `flowchart TD` is in the opening line so a
#: second mermaid block elsewhere in the file is not mistaken for this one.
DIAGRAM = re.compile(r"^```mermaid\nflowchart TD\n.*?^```", re.MULTILINE | re.DOTALL)

#: The subgraph every implementation repository sits in. Named here because the
#: edges refer to it as though it were a repository — `.github` is inherited by
#: all of them at once, and an arrow per repository would say the same thing
#: twelve times and obscure the nine that carry information.
IMPL = "impl"

#: The table, found by its header the way the roadmap's is: the header row and
#: every consecutive line under it that starts with a pipe.
TABLE = re.compile(r"^\| Repo \| Spec \| Language \|.*(?:\n\|.*)*", re.MULTILINE)

#: The sentence that counts the table. The word is the only part that moves.
SENTENCE = re.compile(r"\bThose (\w+) are every repository in the org\b")


def repos() -> list[dict]:
    return tomllib.loads(REGISTRY.read_text(encoding="utf-8"))["repo"]


def word(n: int) -> str:
    if n not in WORDS:
        raise SystemExit(
            f"::error::{n} repositories, which is past the counting words this "
            f"generator knows. Add it to WORDS in {__file__}."
        )
    return WORDS[n]


def cell(entry: dict) -> str:
    """The spec column: one markdown link per page, or the page itself saying so."""
    pages = entry["spec"]
    if not pages:
        # A repository with no page of its own is described by this table and
        # nowhere else, so the cell points at the table rather than going blank
        # and reading like an omission.
        return "this page"
    # The label is the path as written, not its basename: `../README.md` says it
    # leaves this directory, and `README.md` would not.
    return " · ".join(f"[{page}]({page})" for page in pages)


def table() -> list[str]:
    out = ["| Repo | Spec | Language | What's specific about it |",
           "|------|------|----------|--------------------------|"]
    for entry in repos():
        out.append(
            f"| `{entry['name']}` | {cell(entry)} | {entry['lang']} | {entry['note']} |"
        )
    return out


def diagram() -> str:
    entries = repos()
    by_name = {e["name"]: e for e in entries}
    out = ["```mermaid", "flowchart TD"]

    for entry in entries:
        if entry["group"] == "root":
            out.append(f'    {entry["node"]}["{entry["label"]}"]')

    out.append("")
    out.append(f"    subgraph {IMPL}[Implementation]")
    for entry in entries:
        if entry["group"] == IMPL:
            out.append(f'        {entry["node"]}["{entry["label"]}"]')
    out.append("    end")
    out.append("")

    for edge in tomllib.loads(REGISTRY.read_text(encoding="utf-8"))["edge"]:
        arrow = "-.->" if edge.get("dotted") else "-->"
        # An edge may name the subgraph rather than a repository; that is the
        # one target with no registry entry, and it is deliberate.
        ends = [
            end if end == IMPL else by_name[end]["node"]
            for end in (edge["from"], edge["to"])
        ]
        out.append(f"    {ends[0]} {arrow}|{edge['label']}| {ends[1]}")

    out.append("```")
    return "\n".join(out)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    if not DIAGRAM.search(text):
        raise SystemExit(f"::error::no repository diagram found in {README}")
    if not TABLE.search(text):
        raise SystemExit(f"::error::no repository table found in {README}")
    if not SENTENCE.search(text):
        raise SystemExit(f"::error::no counting sentence found in {README}")

    count = len(repos())
    text = DIAGRAM.sub(lambda _: diagram(), text, count=1)
    text = TABLE.sub("\n".join(table()), text, count=1)
    text = SENTENCE.sub(f"Those {word(count)} are every repository in the org", text)
    README.write_text(text, encoding="utf-8")
    print(f"30-repos: diagram, table and count regenerated from {count} registry entries")


if __name__ == "__main__":
    main()
