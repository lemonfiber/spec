# Brand rules

**Status:** Accepted

The binding constraints — the ones a consumer must not violate. The `brand` repo's
[`.docs/logo-usage.md`](../30-repos/brand.md) carries the full usage guidance; this
page carries only what is a **requirement**.

---

## The mark

A whole pixel lemon with a play triangle on its face and a leaf on its stem,
drawn on a 32-cell grid, with a 16-cell redraw for the sizes where 32 cells cannot
each get a pixel. Every file of it is drawn by the `brand` repository's generator
(`scripts/logo.py`) from those grids, with every cell's colour taken from the
tokens.

| Constraint | Requirement |
|------------|-------------|
| Minimum size | The 32-cell mark, icon and lockups at 32px screen / 9mm print; below that, the 16-cell icon (`app-icon-16.svg`) or mark (`mark-small.svg`, `favicon.svg`), min 16px. The tray icon at 16, 22 and 32px |
| Clear space | 4 cells of the mark's own grid on all four sides, measured from the lemon's outermost cell (2 cells on the 16-cell) |
| Scale | Shown at a whole multiple of its grid, so every cell lands on whole pixels; never smoothed |
| Colour | Only from the token palette — never recoloured to match a partner brand |
| Geometry | Never rotated, skewed, stretched; no gradients, bevels, or drop shadows |
| Source | Every mark and the wordmark come from the generator's grids; never re-drawn or re-typeset — change the grid in `brand` |

## The closed palette

Four working colours, two surfaces. **The palette is closed**: nothing outside the
tokens appears in brand usage.

| Token | Role | Constraint |
|-------|------|-----------|
| `ink` | Structure, text, dark surfaces | — |
| `lemon` | Primary brand colour, the fruit | — |
| `fiber` (amber) | **Signal only** — fibre cores, active states, accents | **Never a background fill at scale; never body text** (see [accessibility](accessibility.md)) |
| `leaf` | The leaf | Leaf only — not a general green |
| `paper` / `pith` / `canvas` | Surfaces | Never more than two backgrounds in one layout |

Two hard exclusions:

- **No blues, teals, or cyans anywhere.** The palette is warm; a cool accent
  breaks it.
- **Amber is not decoration.** It marks the fibre and active states. Using it as
  a fill or a text colour both breaks the brand *and* fails contrast — the rule
  is aesthetic and accessible at once.

## The wordmark

Always lowercase, always one word, "fiber" always in amber (`fiber-light` over
`fiber`) except in one-colour reproduction. It is drawn in pixel cells by the
`brand` repository's generator, on the same grid as the mark, and is never set in
a typeface or re-drawn.

## Capitalisation — prose vs. identifier

The lowercase wordmark is a *design* treatment. In writing, the name follows one
rule:

| Context | Form |
|---------|------|
| **Public-facing prose** — marketing copy, README intros, announcements, descriptions | **Lemonfiber** (capital L) |
| **The command, binary, package, repository, crate, and any code identifier** | `lemonfiber` (lowercase) |
| The logo wordmark | lowercase (design) |

So: *"Lemonfiber sets itself up"* in a sentence, but *"run `lemonfiber up tv`"*
for the command, `@lemonfiber/brand` for the package, `lemonfiber/lemonfiber` for the
repo. When the name is set in `code font`, it is the identifier and stays
lowercase; in ordinary prose it is capitalised.

## The don'ts, as requirements

- No tagline, descriptor, or strapline added to the lockup.
- No recolouring of the mark's cells outside the palette.
- No stretching, rotating, or effects on the mark.
- No 32-cell mark below its minimum size — switch to the 16-cell.

## Governing a visual repo

Brand is judgment-heavy, which sits awkwardly with the [canonical-spec
rule](../50-governance/canonical-spec.md) that every change cite a requirement. A
recolour or a new lockup export has no natural `DES-R` to point at.

The resolution: **checkable constraints are `DES-R` requirements; aesthetic
changes cite `GOV-R12`** (routine maintenance), the same identifier a dependency
bump uses. A new logo export that stays within the palette and mark-integrity
rules is maintenance against those rules; a change that alters what the rules
*permit* — a palette addition, a new minimum size — is a `DES-R` change and
follows the normal lifecycle.

This keeps brand under governance without pretending aesthetics are requirements.

## Requirements

| ID | Requirement |
|----|-------------|
| **DES-R1** | Brand usage MUST draw only from the token palette; no colour outside the tokens. |
| **DES-R2** | The palette MUST contain no blue, teal, or cyan. |
| **DES-R3** | Amber (`fiber`) MUST NOT be used as a background fill at scale or as body text. |
| **DES-R4** | The 32-cell mark MUST NOT be rendered below its minimum size; the 16-cell redraw MUST be used instead. |
| **DES-R5** | The mark MUST NOT be rotated, skewed, stretched, or given gradients, bevels, or shadows. |
| **DES-R6** | The wordmark MUST be the pixel wordmark the `brand` repository's generator draws from its grids, with "fiber" in amber except in one-colour reproduction, and MUST NOT be set in a typeface or re-drawn. |
| **DES-R7** | No tagline or descriptor MAY be added to any lockup. |
| **DES-R8** | A change altering what the brand rules permit MUST follow the normal change lifecycle as a `DES-R` change; a change within the rules MAY cite `GOV-R12`. |
| **DES-R21** | In public-facing prose the name MUST be written **Lemonfiber** (capital L); the command, binary, package, repository, crate, code identifiers, and the logo wordmark MUST be lowercase `lemonfiber`. |

## Related

- [surface-mapping.md](surface-mapping.md) — where these apply, per surface
- [accessibility.md](accessibility.md) — the contrast reason behind the amber rule
- [brand repo .docs](../30-repos/brand.md) — full usage guidance
