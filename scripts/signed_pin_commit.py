#!/usr/bin/env python3
"""A pin bump committed as the App, so GitHub signs it — OPS-R85.

Every consumer's `main` takes signed commits only. A commit made with `git` in
the fan-out's runner and pushed is unsigned, so the bump it carries is one no
repository can merge. A commit GitHub makes through `createCommitOnBranch` for
the App is signed by GitHub, so the fan-out makes its commit that way.

The rolling branch is never reset to `main` in place. A pull request whose head
briefly holds no commits of its own is closed by GitHub, and the fan-out keeps
one pull request per repository for every number. So the commit is made on a
staging branch placed at `main`, and the rolling branch is then moved to it in
one step, forced, the staging branch removed after.

The files are the ones the fan-out rewrote in its clone, read from the working
tree: changed files are added with their new contents, removed files deleted.

    signed_pin_commit.py --repo <clone> --slug <owner/repo> --branch <name> \\
        --message <file>

Prints the new commit on success. On failure it names the step that refused
and exits 1, and the fan-out counts the repository as refused.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys

#: What a staging branch is called beside the branch it stages for.
STAGING = "-staging"

#: The shapes a repository's name and a branch's take. Each is held before it
#: reaches a command, so neither can be read there as an option or a path out
#: of the API's repository and branch namespaces.
SLUG = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._][A-Za-z0-9._-]*\Z")
BRANCH = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*\Z")

MUTATION = (
    "mutation($input: CreateCommitOnBranchInput!) "
    "{ createCommitOnBranch(input: $input) { commit { oid } } }"
)


def gh(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True, check=False
    )


def git(repo: pathlib.Path, *args: str) -> str:
    """One git command run in the clone. The clone is the working directory,
    never an argument, so nothing the caller named is read as an option."""
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def place(slug: str, branch: str, sha: str) -> str:
    """Point `branch` at `sha`, made where it is missing and forced where it is
    not. Empty on success, otherwise what GitHub said."""
    if gh("api", f"repos/{slug}/git/ref/heads/{branch}").returncode == 0:
        done = gh(
            "api", "--method", "PATCH", f"repos/{slug}/git/refs/heads/{branch}",
            "-f", f"sha={sha}", "-F", "force=true",
        )
    else:
        done = gh(
            "api", "--method", "POST", f"repos/{slug}/git/refs",
            "-f", f"ref=refs/heads/{branch}", "-f", f"sha={sha}",
        )
    return "" if done.returncode == 0 else (done.stderr.strip() or "refused")


def request(repo: pathlib.Path, slug: str, branch: str, base: str, message: str) -> dict:
    """The `createCommitOnBranch` call for what the clone's working tree changed."""
    headline, _, body = message.strip().partition("\n")
    changed = git(repo, "diff", "--name-only", "--diff-filter=d").split()
    gone = git(repo, "diff", "--name-only", "--diff-filter=D").split()
    return {
        "query": MUTATION,
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": slug, "branchName": branch},
                "expectedHeadOid": base,
                "message": {"headline": headline, "body": body.strip()},
                "fileChanges": {
                    "additions": [
                        {
                            "path": path,
                            "contents": base64.b64encode((repo / path).read_bytes()).decode(),
                        }
                        for path in changed
                    ],
                    "deletions": [{"path": path} for path in gone],
                },
            }
        },
    }


def commit(repo: pathlib.Path, slug: str, branch: str, message: str) -> tuple[str, str]:
    """The new commit on `branch`, or what refused it, as `(oid, refusal)`."""
    base = git(repo, "rev-parse", "HEAD").strip()
    staging = f"{branch}{STAGING}"

    if why := place(slug, staging, base):
        return "", f"{staging} could not be placed at {base}: {why}"

    made = gh(
        "api", "graphql", "--input", "-", "--jq", ".data.createCommitOnBranch.commit.oid",
        stdin=json.dumps(request(repo, slug, staging, base, message)),
    )
    oid = made.stdout.strip()
    if made.returncode != 0 or len(oid) != 40:
        return "", f"the commit was not made: {made.stderr.strip() or oid or 'no answer'}"

    if why := place(slug, branch, oid):
        return "", f"{branch} could not be moved to {oid}: {why}"

    # Left behind, a staging branch is clutter and nothing worse, so its
    # removal failing is said and does not refuse the bump.
    if gh("api", "--method", "DELETE", f"repos/{slug}/git/refs/heads/{staging}").returncode != 0:
        print(f"::warning::{slug}'s {staging} could not be removed", file=sys.stderr)
    return oid, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=pathlib.Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--message", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    if not SLUG.match(args.slug) or not BRANCH.match(args.branch) or ".." in args.branch:
        print(f"refused: {args.slug!r} is not a repository or {args.branch!r} is not a branch",
              file=sys.stderr)
        return 1
    if not args.repo.is_dir():
        print(f"refused: {args.repo} is not a clone", file=sys.stderr)
        return 1

    oid, refusal = commit(
        args.repo, args.slug, args.branch, args.message.read_text(encoding="utf-8")
    )
    if refusal:
        print(refusal, file=sys.stderr)
        return 1
    print(oid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
