# lemonfiber/spec tasks. `just` to list.
default:
    @just --list

# Run every check CI runs, and turn the hooks on if they are not already —
# this is the command run before a push, which is when the hook matters.
ci: hooks integrity shared lint typos links

# Turn on the repository's own git hooks. Once per clone.
hooks:
    git config core.hooksPath .githooks
    @echo "hooks on: .githooks/pre-push"

# Read the scripts that do the reading. They are the gates, here and in every
# repo that calls the reusable workflows.
lint:
    # `shared/gates/` too: it is Python that decides whether a merge may
    # happen in six repositories, and it was linted in none of them.
    uvx ruff@0.16.4 check scripts/ shared/gates/

# `just blocked lemonfiber/spec` for one repo, `just blocked lemonfiber --org`
# for every repo in the organisation. Both take pull request numbers too.
#
# Say what a pull request is blocked on, including checks that never reported.
blocked target *flags:
    python3 scripts/what_is_blocking.py {{target}} {{flags}}

# The lint configs and brand assets here match the canonical copies in shared/.
shared:
    python3 scripts/check_shared_files.py --canonical . --repo lemonfiber/spec

# Verify identifiers resolve, no dups, links unbroken.
integrity:
    python3 scripts/integrity.py

# Validate feature frontmatter against the schema.
check-meta:
    python3 scripts/check_frontmatter.py

# The question OPS-R54 asks at release, runnable long before the tag. The tracker
# is the binary repository's IMPLEMENTATION-STATUS.md, from a clone under
# checkouts/ the way execute-version arranges one.
no-stubs version status="checkouts/lemonfiber/IMPLEMENTATION-STATUS.md":
    python3 scripts/check_no_stubs.py --version {{version}} --status {{status}}

# Regenerate the feature board (index.json + BOARD.md) from frontmatter + manifests.
board:
    python3 scripts/gen_board.py

# Regenerate the repository table, diagram and count from 30-repos/repos.toml.
repos:
    python3 scripts/gen_repos.py

# Rewrite every count this repository states about itself from what it holds.
counts:
    python3 scripts/integrity.py --write

# Spell check.
typos:
    typos

# Link check.
links:
    lychee --no-progress .

# Build the redirect site that stands where the book stood.
docs:
    rm -rf redirect && python3 scripts/gen_redirects.py redirect

# Self-test the governance gate against a sample citation.
check-gate text:
    echo "{{text}}" > /tmp/_g.txt && python3 scripts/spec_check.py --spec-dir . --text-file /tmp/_g.txt
