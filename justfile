# lemonfiber/spec tasks. `just` to list.
default:
    @just --list

# Run every check CI runs.
ci: integrity typos links

# Verify identifiers resolve, no dups, links unbroken.
integrity:
    python3 scripts/integrity.py

# Spell check.
typos:
    typos

# Link check.
links:
    lychee --no-progress .

# Build the docs site locally into ./book.
docs:
    rm -rf src && mkdir src && cp README.md src/ && \
        for d in [0-9]*-*; do cp -r "$d" "src/$d"; done && \
        python3 scripts/strip_frontmatter.py && \
        python3 scripts/gen_summary.py src && mdbook build

# Self-test the governance gate against a sample citation.
check-gate text:
    echo "{{text}}" > /tmp/_g.txt && python3 scripts/spec_check.py --spec-dir . --text-file /tmp/_g.txt
