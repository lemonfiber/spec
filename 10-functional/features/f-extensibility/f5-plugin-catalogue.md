---
id: F5
title: The plugin catalogue and what vouches for a plugin
kind: feature
area: F
audience: operator
status: draft
maturity: planned
priority: P1
labels: [extensibility, security, verification]
requires: [F3]
relates: [F1, F4, F6, F7, C1]
---

# F5 — The plugin catalogue and what vouches for a plugin

**Status:** Draft · **Audience:** Operator · **Area:** F — Extensibility

---

## Purpose

Say where a plugin comes from, and what that origin does and does not vouch for.

Two audiences pull in opposite directions here. Someone who wants Plex wants to type one
command and have it work, and is not equipped to audit a manifest. Someone who evaluates
this project publicly wants to know they are not locked into a curated list, and will
install from their own fork on the first afternoon. Serving only the first produces a
walled garden; serving only the second produces an ecosystem where nothing is vouched for
and the first audience gets hurt.

So there are two routes, and lemonfiber is explicit about which one an operator is on.
A **reviewed catalogue** where every plugin landed by human review, validated in CI and
signed. And **any git source the operator names**, installed on the same technical terms
but with lemonfiber stating plainly that nothing has reviewed it and refusing to present
its proofs as vouched for.

The distinction is not a warning banner. It is carried on the plugin for as long as it is
installed, so an operator debugging a strange stack six months later can see which of
their plugins nobody ever read.

## Behaviour

### The catalogue is a repository, and it is reviewed like one

The catalogue is `lemonfiber-plugins` — a git repository in the project's own
organisation. A plugin enters it by pull request. Its CI validates every manifest against
the published schema, runs every declared proof, and refuses a contribution whose proofs
do not pass — so the acceptance bar is mechanical before it is human. A human then reads
the diff, which is possible precisely because a plugin is data.

Releases from the catalogue are signed. An operator installing from the catalogue is
relying on: a schema that was checked, proofs that ran, a person who read it, and a
signature that ties what they fetched to what was reviewed.

### An operator may install from anywhere, and is told what that means

`lemonfiber plugin add` accepts a git URL or a local path. The manifest is validated, the
proofs are run, and the same rules about undeclared reach apply — the technical bar does
not move. What moves is what lemonfiber claims: an unreviewed plugin is installed as
unreviewed, said at install and carried on the plugin afterwards.

lemonfiber never refuses an operator their own source. F1 exists because a tool that
stands between an experienced operator and their stack loses exactly the audience that
decides whether anyone else adopts it.

### What a plugin may reach is part of what is vouched for

A plugin declares the hosts its recipes reach. That declaration extends the account of
what leaves this machine — which is currently a closed list, and whose closedness is a
promise the product makes. The promise is not abandoned; it is made precise. The account
becomes *these destinations, and these others which this named plugin added* — so an
operator reading it sees the same completeness they had before, plus who is responsible
for each addition.

A plugin reaching a host it did not declare is a refusal, not a log line.

### Provenance is verifiable, not asserted

Where a plugin came from, which revision, and what signed it are recorded when it is
installed and readable afterwards. A plugin whose source can no longer be reached does
not become untrusted retroactively — but it does become unupdatable, and that is said
rather than discovered at the next attempt.

### The catalogue is not a single point of failure

Nothing about the design requires the catalogue to exist for lemonfiber to work, or for a
plugin already installed to keep working. If the catalogue is unreachable, installed
plugins are unaffected and installing from a named source still works. The catalogue is a
convenience and a review mechanism, not a runtime dependency.

## States

| State | Meaning |
|-------|---------|
| `reviewed` | Installed from the catalogue: schema-checked, proofs run in CI, human-reviewed, signed |
| `unreviewed` | Installed from an operator-named source; technically validated, vouched for by nobody |
| `signature-unverified` | The source claimed a signature that does not verify; refused |
| `source-unreachable` | The origin can no longer be fetched; the installed plugin still runs and cannot be updated |
| `undeclared-host` | A recipe reached a host the manifest did not declare; refused |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| The catalogue is unreachable | Installed plugins are unaffected; installing from a named source still works. The catalogue is not a runtime dependency. |
| A plugin's signature does not verify | Refuse. A claimed-but-invalid signature is worse than none and is treated as such. |
| An operator installs from their own fork | Allow it, install it as unreviewed, and carry that on the plugin for as long as it is installed. |
| A catalogue plugin and a named-source plugin have the same name | Refuse and name both origins; the operator chooses which they meant. |
| A plugin declares a host it never reaches | Allowed. Declaring more than is used is conservative, and the account says what was declared. |
| A recipe reaches a host the manifest did not declare | Refuse the plugin. The account of what leaves this machine must stay complete. |
| A plugin's source disappears after installation | Keep it running, mark it unupdatable, and say so rather than failing at the next update attempt. |
| A catalogue contribution's proofs fail in CI | Refuse the contribution before merge. The catalogue never serves a plugin whose proofs did not pass. |
| An operator asks whether a plugin was reviewed | Answerable from the installed plugin itself, not only from the catalogue. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F5-R1** | A reviewed plugin catalogue MUST exist as a git repository in the project's organisation, and every plugin MUST enter it by reviewed pull request. |
| **F5-R2** | The catalogue's CI MUST validate every manifest against the published schema and run every declared proof, and MUST refuse a contribution whose proofs do not pass. |
| **F5-R3** | Catalogue releases MUST be signed, and a signature that does not verify MUST be refused. |
| **F5-R4** | An operator MUST be able to install a plugin from a git source or local path they name. |
| **F5-R5** | A plugin not installed from the catalogue MUST be installed as unreviewed, MUST be said so at install time, and MUST carry that for as long as it is installed. |
| **F5-R6** | Technical validation — schema, declared reach, proofs — MUST be identical for reviewed and unreviewed plugins. |
| **F5-R7** | Where a plugin came from, at which revision, and what signed it MUST be recorded at install and readable afterwards. |
| **F5-R8** | A plugin MUST declare every host its recipes reach, and reaching an undeclared host MUST be refused. |
| **F5-R9** | The account of what leaves this machine MUST include hosts declared by installed plugins, and MUST attribute each to the plugin that declared it. |
| **F5-R10** | An unreachable catalogue MUST NOT affect installed plugins, and MUST NOT prevent installing from a named source. |
| **F5-R11** | A plugin whose origin can no longer be fetched MUST keep working and MUST be reported as unupdatable. |
| **F5-R12** | Two plugins of the same name from different origins MUST be refused, naming both origins. |

## Related

- [F3 Plugin manifests and recipes](f3-stack-manifests.md) — what the catalogue serves and CI validates
- [F6 Plugin lifecycle](f6-plugin-lifecycle.md) — what happens after one is fetched
- [F7 Plugin provenance](f7-plugin-provenance.md) — where origin is shown once installed
- [F1 Customisation & escape hatches](f1-customisation.md) — why an operator's own source is never refused
