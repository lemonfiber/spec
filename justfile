# lemonfiber/spec tasks. `just` to list.
default:
    @just --list

# Run every check CI runs.
ci: integrity shared typos links

# The lint configs and brand assets here match the canonical copies in shared/.
shared:
    python3 scripts/check_shared_files.py --canonical . --repo lemonfiber/spec

# Verify identifiers resolve, no dups, links unbroken.
integrity:
    python3 scripts/integrity.py

# Validate feature frontmatter against the schema.
check-meta:
    python3 scripts/check_frontmatter.py

# Regenerate the feature board (index.json + BOARD.md) from frontmatter + manifests.
board:
    python3 scripts/gen_board.py

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
