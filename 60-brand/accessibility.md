# Brand accessibility

**Status:** Accepted

Whether the palette meets [WCAG AA](../10-functional/features/g-ux/g3-accessibility.md#g3-r3)
is a **computed property of the tokens**, not an opinion. This page states the
baseline, with the actual ratios, and the pairings that are unsafe.

Consistent with [P3](../00-overview/vision.md#p3--the-tool-proves-things-rather-than-assuming-them):
the contrast is measured, and re-measured by a CI check
([ARCH-R40](../20-architecture/contracts/design-tokens.md)), not assumed.

---

## The measured baseline

Contrast ratios against the default `paper` surface (#FBF7EA), computed to WCAG
2.1. **AA** needs 4.5:1 for body text, 3:1 for large text.

| Foreground | On paper | Verdict | Use |
|------------|----------|---------|-----|
| `ink` #17160F | **16.9** | AAA | Body, headings — the default |
| `ink-soft` #241F14 | **15.3** | AAA | Body |
| `leaf` #5B6B2A | **5.5** | AA | Text where the green is wanted |
| `text-muted` #6E6A57 | **5.1** | AA | Secondary body text — **on paper only** |
| `fiber-deep` #A85A12 | **4.7** | AA | Links, the "fiber" wordmark |
| `text-faint` #8B8770 | **3.4** | AA-large | **Not body** — labels, large only |
| `fiber` #E07A17 | **2.8** | ✗ FAIL | **Never text** — signal accent only |
| `fiber-light` #F09A3C | **2.1** | ✗ FAIL | Dark-mode amber only, never light-mode text |

## The findings that constrain usage

Three are not obvious and each is a rule:

### `text-muted` is body-safe on paper, not on canvas

On `paper` it's 5.1 (AA). On `canvas` (#EDE7D5, the darker page behind cards) it
drops to **4.4 — below AA for body**. So muted secondary text MUST sit on paper,
not on canvas. This is the kind of pairing that passes a casual eye and fails a
meter.

### Amber is unusable as text — which the brand already forbids

`fiber` at 2.8 and `fiber-light` at 2.1 both fail as text. This is the
*accessibility* reason behind the [brand rule](brand-rules.md#the-closed-palette)
that amber is signal-only: the aesthetic rule and the contrast rule agree, which
is why amber-as-text is forbidden twice over.

Amber is fine as a **non-text** accent — a fibre core, a focus ring, an active
underline — where contrast rules for text don't apply.

### `text-faint` is decorative

At 3.4 it clears AA only for *large* text. It is for eyebrow labels and
oversized secondary type, never body copy.

## The ink theme is comfortable

Dark mode inverts to `paper` = #17160F, and the pairings there are generous:

| On ink #17160F | Ratio | Verdict |
|----------------|-------|---------|
| Light text #FBF7EA | 16.9 | AAA |
| `lemon` #F0C419 | 10.9 | AAA |
| `fiber-light` #F09A3C | 8.1 | AAA |

This is why the ink theme lightens amber to `fiber-light`
([token contract](../20-architecture/contracts/design-tokens.md#theme)) — on a
dark surface the lighter amber is not only legible but AAA, whereas the same
lightening on paper would fail. The theme switch is a contrast decision, not just
a mood one.

## The contract this creates

The [design-token contract](../20-architecture/contracts/design-tokens.md#what-the-tokens-must-guarantee)
requires every body-text pairing to meet AA, and a CI check verifies it. This page
is the baseline that check enforces:

- **Body text** MUST use `ink`, `ink-soft`, `text-muted` (on paper), `leaf`, or
  `fiber-deep`.
- `text-faint` MUST be large-text only.
- `fiber` and `fiber-light` MUST NOT be text.
- A new or changed token that would put a failing pairing into body use is a
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
| **DES-R15** | Body text MUST use only token pairings meeting WCAG AA (4.5:1); the body-safe set MUST be as listed here. |
| **DES-R16** | `text-muted` MUST be used for body text only on `paper`, not on `canvas`. |
| **DES-R17** | `text-faint` MUST be restricted to large text. |
| **DES-R18** | `fiber` and `fiber-light` MUST NOT be used as text. |
| **DES-R19** | A token change producing a failing body pairing MUST be treated as a contract violation. |
| **DES-R20** | The logo MUST carry a text alternative in the web UI. |

## Related

- [design-tokens contract](../20-architecture/contracts/design-tokens.md) — the CI check that enforces this
- [brand-rules.md](brand-rules.md) — the amber rule this explains
- [G3 Accessibility](../10-functional/features/g-ux/g3-accessibility.md) — the broader requirements
