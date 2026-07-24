# User journeys

**Status:** Accepted

Nine paths through the product. Where a [feature](../features/) describes one
capability in depth, a journey describes what someone actually *does* — crossing
several features, in order, with the seams visible.

Journeys are the acceptance tests. Each names the features it exercises, so a
journey can be walked end to end to verify they compose.

## Index

| # | Journey | Audience | Exercises |
|---|---------|----------|-----------|
| [J1](j1-first-run.md) | First run on a clean machine | Operator | A1, A2, A3, C5, D1, D3, B8 |
| [J2](j2-search-only.md) | "I just want to search for an NZB" | Operator | B1, B2 |
| [J3](j3-download-only.md) | "I have a link — just fetch it" | Operator | B1, B2, C2 |
| [J4](j4-daily-use.md) | Daily use | Operator | B3, B4, G7 |
| [J5](j5-vpn-verification.md) | Verifying the VPN isn't leaking | Operator | C1, C2 |
| [J6](j6-recovery.md) | Recovering after breaking something | Operator | D1, E3, E4, C9 |
| [J7](j7-upgrading.md) | Upgrading | Operator | E1, E3, E4 |
| [J8](j8-customising.md) | Customising the stack | Operator | F1, C9 |
| [J9](j9-household.md) | Getting the household watching | Both | D6, D4, G5, G6 |

## The two shapes

**J1 and J9 are the product.** J1 is the operator getting to a working stack; J9
is everyone else getting value from it. If either fails, nothing else matters.

**J2–J8 are the long tail** — the narrow slices, the routine operations, and
recovery. They matter because they're what the operator does for years after
setup, and because they're where a stack that was merely *set up* becomes one
that is *maintained*.

## Convention

Journeys reference requirements by their feature-scoped ID (`A2-R4`, `C2-R1`).
There is no separate requirements tree — requirements live inside their
[feature](../features/README.md#requirement-ids).
