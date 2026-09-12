# Brand accessibility

**Status:** Accepted

Whether the palette meets [WCAG AA](../10-functional/features/g-ux/g3-accessibility.md)
is a **computed property of the tokens**, not an opinion. This page states the
baseline, with the actual ratios, and the pairings that are unsafe.

Consistent with [P3](../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them):
the contrast is measured, and re-measured by a CI check
([ARCH-R40](../20-architecture/contracts/design-tokens.md)), not assumed.

---

## The measured baseline

Every number below is computed from [`tokens.json`](tokens.json) by
[`gen_contrast.py`](../scripts/gen_contrast.py), and the integrity job fails if
the page and the tokens disagree. Nobody types a ratio here, because the page's
own premise is that a ratio is not an opinion — and because the numbers that
were typed here went wrong three times over without anyone noticing.

**AA** needs 4.5:1 for body text and 3:1 for large text; **AAA** needs 7:1. The
three surfaces are the grounds anything is ever set on: `paper` is the default,
`canvas` the darker page behind cards, `ink` the dark theme.

| Token | Hex | On `paper` | On `canvas` | On `ink` |
|-------|-----|---|---|---|
| `ink` | #17160F | 16.92 · AAA | 14.67 · AAA | — |
| `ink-soft` | #241F14 | 15.29 · AAA | 13.26 · AAA | 1.11 · fails |
| `lemon` | #F0C419 | 1.55 · fails | 1.35 · fails | 10.89 · AAA |
| `lemon-bright` | #FFD84D | 1.29 · fails | 1.12 · fails | 13.11 · AAA |
| `fiber` | #E07A17 | 2.81 · fails | 2.44 · fails | 6.01 · AA |
| `fiber-deep` | #9C5411 | 5.31 · AA | 4.61 · AA | 3.19 · AA large |
| `fiber-light` | #F09A3C | 2.09 · fails | 1.81 · fails | 8.11 · AAA |
| `leaf` | #5B6B2A | 5.47 · AA | 4.74 · AA | 3.09 · AA large |
| `paper` | #FBF7EA | — | 1.15 · fails | 16.92 · AAA |
| `pith` | #FBF6E7 | 1.01 · fails | 1.14 · fails | 16.78 · AAA |
| `canvas` | #EDE7D5 | 1.15 · fails | — | 14.67 · AAA |
| `line` | #DAD2BC | 1.41 · fails | 1.22 · fails | 12.02 · AAA |
| `line-soft` | #E4DCC7 | 1.28 · fails | 1.11 · fails | 13.26 · AAA |
| `text-muted` | #565344 | 7.21 · AAA | 6.26 · AA | 2.35 · fails |
| `text-faint` | #6A6756 | 5.31 · AA | 4.61 · AA | 3.18 · AA large |

`tokens.json` here is a distribution copy. The brand maintains it, and
[`shared/assets.sha256`](../shared/assets.sha256) holds this copy byte-identical
to it — so a token changing in the brand reaches this page by the copy being
refreshed, and the table follows on the next run.

## What the measurements decide

**The body-safe set is whatever the table says it is.** A pairing at AA or
better may carry body text; one below it may not, and no list needs keeping.
That is the whole of `DES-R15`, and it is why the list that used to sit here is
gone: it was a second statement of the table, and it was the half that went
stale.

**Both surfaces are measured, not just the default.** A pairing is about a
foreground *and* a ground, and the same token can clear AA on `paper` and fail
on `canvas`, which is darker. The table carries a column for each so the
question cannot be answered for the wrong one.

**Amber is never text on a light ground, and the rule and the meter agree.**
`fiber` and `fiber-light` both fail against `paper` and `canvas`, which is the
accessibility reason behind the [brand rule](brand-rules.md#the-closed-palette)
that amber is signal-only. They clear AA against `ink`, and that is not a
loophole — it is the same finding read from the other side, and it is why the
dark theme lightens amber rather than keeping the light-theme value. Amber is
fine as a **non-text** accent anywhere — a fibre core, a focus ring, an active
underline — where contrast rules for text do not apply.

**`text-faint` is restrained by emphasis, not by contrast.** It clears AA for
body text against `paper` and `canvas` both. It is still not body copy: it is
the lowest-emphasis token in the palette, for eyebrow labels and secondary type,
and information a reader needs does not go there. That is a typographic
decision rather than a measured one, and saying so is better than implying a
meter forbids it.

**The dark theme is the comfortable one.** The `On ink` column is generous
throughout, which is why the ink theme lightens amber to `fiber-light`
([token contract](../20-architecture/contracts/design-tokens.md#theme)) — on a
dark surface the lighter amber is legible where the same lightening on paper
would fail. The theme switch is a contrast decision, not just a mood one.

## The contract this creates

The [design-token contract](../20-architecture/contracts/design-tokens.md#what-the-tokens-must-guarantee)
requires every body-text pairing to meet AA, and a CI check verifies it. Two
checks, in two repositories, and neither is a person reading a table:
`brand:scripts/check_tokens.py` refuses a token change that puts a failing
pairing into body use, and the integrity job here refuses a page that has
drifted from the tokens.

A new or changed token that would put a failing pairing into body use is a
**contract violation**, not a design preference.

## Beyond contrast

Contrast is the measurable part; the [web accessibility requirements](../10-functional/features/g-ux/g3-accessibility.md)
still apply on top — focus visibility, keyboard operability, reduced-motion, text
alternatives for the logo. The brand doesn't override G3; it must satisfy it.

The logo in particular carries a text alternative (`alt="lemonfiber"`), and the
ink/paper theme honours `prefers-color-scheme` and the explicit toggle
([G3-R5](../10-functional/features/g-ux/g3-accessibility.md), the token
[theme attribute](../20-architecture/contracts/design-tokens.md#theme)).

## Requirements

| ID | Requirement |
|----|-------------|
| **DES-R15** | Body text MUST use only token pairings meeting WCAG AA (4.5:1); the body-safe set MUST be computed from the tokens rather than listed by hand. |
| **DES-R16** | Every surface a token may sit on MUST be measured, not only the default one. |
| **DES-R17** | `text-faint` MUST NOT carry information a reader needs; it is the lowest-emphasis token, restrained by emphasis rather than by contrast. |
| **DES-R18** | `fiber` and `fiber-light` MUST NOT be used as text. |
| **DES-R19** | A token change producing a failing body pairing MUST be treated as a contract violation. |
| **DES-R20** | The logo MUST carry a text alternative in the web UI. |

## Related

- [design-tokens contract](../20-architecture/contracts/design-tokens.md) — the CI check that enforces this
- [brand-rules.md](brand-rules.md) — the amber rule this explains
- [G3 Accessibility](../10-functional/features/g-ux/g3-accessibility.md) — the broader requirements
