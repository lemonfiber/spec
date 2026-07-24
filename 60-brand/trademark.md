# Trademark & forking policy

**Status:** Accepted

The code is open; the **identity** is not. This page says what that means for
someone who forks — because a proprietary mark without a stated forking policy
just leaves people guessing.

---

## What's protected

The name **lemonfiber**, the **logo and wordmark**, and the marks under
`brand/assets/logo/` are proprietary ([licence rationale](../90-appendix/license-rationale.md)).
The code (Hippocratic 3.0) and the design **tokens** (open) are not.

This is the ordinary shape of an open project with a protected identity — Rust,
Mozilla, Python and Docker all do it. The software is free to use, fork and
redistribute; the name and logo are not, so a fork can't impersonate the project.

## If you fork

You may fork any repo and build on the code. If you distribute your fork:

| Do | Don't |
|----|-------|
| Rename it — your own name, your own logo | Ship it as "lemonfiber" or with the lemonfiber mark |
| Use the open tokens if you like | Use the proprietary logo assets |
| Say *"based on lemonfiber"* factually | Imply endorsement or that it *is* lemonfiber |
| Keep the licence and attribution | Remove the licences or DCO history |

The one-line version: **fork the code freely; don't wear the name.**

## Nominative use is fine

You can refer to lemonfiber by name — "a plugin for lemonfiber", "compatible with
lemonfiber", "based on lemonfiber" — that's honest, factual reference and needs no
permission. What needs permission is using the name or mark *as your own*
project's identity, or in a way that suggests official status.

## Why this matters for the token split

It's why [`brand`](../30-repos/brand.md) is licensed in two parts: the tokens are
open so a fork (or the web UI) can use the visual system, while the marks stay
proprietary so the *identity* can't be lifted. A forker gets the design language
and must bring their own name.

## Requirements

| ID | Requirement |
|----|-------------|
| **DES-R22** | The forking policy MUST be stated: the code and tokens are open; the name and marks are not and MUST NOT be used by a fork as its own identity. |
| **DES-R23** | Nominative reference to lemonfiber MUST be permitted without requiring permission. |

## Related

- [90-appendix/license-rationale.md](../90-appendix/license-rationale.md) — the licence split
- [30-repos/brand.md](../30-repos/brand.md) — the two-part licence in the repo
- [brand-rules.md](brand-rules.md) — the mark-integrity rules
