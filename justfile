# lemonfiber/spec tasks. `just` to list.
default:
    @just --list

# Everything the `integrity` job decides, and the hooks turned on — the command
# to run before a push, which is when the hook matters.
#
# It is not CI and does not say it is. Most of what a pull request here starts is
# forge-side and no clone can run any of it, so a recipe claiming to be the whole
# of CI is making a promise it cannot keep — and a promise broken once teaches
# people to skip the command and read the run instead.
#
# Not here, and what answers each:
#
#   commitlint, dco, attribution,          `.githooks/commit-msg`, which `hooks`
#   the citation gate                      above turns on — all four, before the
#                                          push, with the line to add
#   coverage                               `python3 scripts/test_*.py` runs the
#                                          suites; the 100% floor is measured on
#                                          the forge
#   markdown, actionlint                   `npx markdownlint-cli2 "**/*.md"` and
#                                          `actionlint`
#   pins, workflow-pins                    ask the forge which commits a pin has
#                                          not taken
#   CodeQL, gitleaks, osv-scanner,         forge-side, and none of them decides
#   sonar, label, the reference comment    anything about a document here
#   the redirect site                      `just docs`
ci: hooks integrity shared services check-meta ordering generated lint typos links local

# What the recipe above says it covers, against what it cannot: a description
# claiming to be CI has to name what it leaves out, because CI is mostly jobs no
# clone can run. A recipe nobody described is refused too — the state in which
# this has nothing to read and would report that every claim here is honest.
local:
    python3 scripts/check_local_command.py --root .

# Every file this repository generates from something else, regenerated and
# compared. A generated file edited by hand, or left behind by an edit to its
# source, is the failure these exist to refuse — and the number in it goes
# stale silently, which is the whole reason it is generated.
generated:
    python3 scripts/gen_roadmap_table.py
    git diff --exit-code -- 00-overview/roadmap.md
    python3 scripts/gen_board.py
    git diff --exit-code -- 10-functional/features/index.json 10-functional/features/BOARD.md
    python3 scripts/gen_repos.py
    git diff --exit-code -- 30-repos/README.md
    python3 scripts/gen_contrast.py
    git diff --exit-code -- 60-brand/accessibility.md

# Nothing scheduled before what it requires, nothing binding resting on
# something unagreed, and every accepted requirement on the release train.
ordering:
    python3 scripts/check_order.py
    python3 scripts/check_binding_order.py
    python3 scripts/check_goal_coverage.py

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

# The bundled-service count this repository states, against the stack that holds
# them. Reads `lemonfiber-media-stack`'s own manifest over the wire, like `links`
# already does; `--stack <path>` reads a copy inside this checkout instead, and
# `--write` rewrites the prose rather than refusing it.
services *flags:
    python3 scripts/check_services.py {{flags}}

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
