# G2 — Plain-language layer & in-product help

**Status:** Accepted · **Audience:** Both · **Area:** G — Cross-cutting UX

---

## Purpose

Make the product comprehensible to someone who doesn't already know the domain.

This ecosystem's vocabulary is a wall. *Indexer, NZB, hardlink, retention,
Torznab, custom format, root folder, killswitch, ratio* — all load-bearing, none
guessable. Existing documentation defines them by reference to each other, so
understanding requires already understanding.

The non-technical operator can follow instructions; what they cannot do is
**infer**. Every unexplained term is a point at which they must go elsewhere,
and each such point loses some of them.

## Behaviour

### Explanation lives where the term is used

Not in a glossary they must know to consult. A term appearing in the interface
carries its explanation inline — expandable, adjacent, and phrased for someone
encountering it for the first time.

### Explanations state purpose, not definition

| Instead of | Say |
|-----------|-----|
| "An indexer is a searchable index of Usenet articles" | "Indexers are search engines that find what you're looking for. You need at least one; most cost a small yearly fee." |
| "Hardlinks allow multiple directory entries to reference one inode" | "Lets a file appear in two places while taking up space once — so importing is instant and doesn't use extra disk." |
| "Retention is the period articles remain available" | "How far back your Usenet provider keeps things. Longer retention means older content is still downloadable." |

The second column answers *why should I care*, which is the actual question.

### Consistent terms, always

One concept, one word, everywhere. The ecosystem uses *grab*, *snatch* and
*fetch* interchangeably; lemonfiber picks one and never varies. Synonyms are a
tax paid by the least confident reader.

### Numbers are contextualised

"2.4 GB" means little on its own. "2.4 GB — about 40 minutes on your connection"
is actionable. Sizes, durations and rates carry consequence where it's knowable.

### Jargon appears alongside plain language, not instead of it

The plain phrasing must not prevent an operator from learning the real term —
they'll need it to search for help. Both are shown, with the plain one leading.

### Depth is available, never mandatory

A short explanation with an optional longer one. The newcomer isn't buried and
the curious aren't stonewalled.

### Errors are the highest-value place for this

An error is read by someone who is stuck, and often anxious. It's where jargon
does the most damage and clarity the most good. [G4](g4-error-model.md) governs
the structure; this feature governs the words.

## States

Per term or concept:

| State | Meaning |
|-------|---------|
| `explained` | Inline explanation available wherever it appears |
| `contextualised` | Explanation adapts to the operator's configuration |
| `deep` | Extended explanation available on request |
| `untranslated` | Domain term with no plain-language form yet — **a defect** |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Term has no good plain-language form | Explain by consequence rather than definition. Some concepts are only definable by what they cause. |
| Explanation would be misleadingly simple | Prefer accurate-and-longer over simple-and-wrong. Simplification that produces a false mental model costs more than it saves. |
| Experienced operator finds it patronising | Explanations are collapsed by default once acknowledged, and can be turned off wholesale. |
| Term differs between services | State the mapping. Sonarr and SABnzbd use different words for the same thing. |
| Message would be very long inline | Lead with one sentence; link to depth. |
| Non-English operator | Out of scope for 1.0; write text that translates cleanly — avoid idiom and cultural reference. |
| Explanation drifts from behaviour | Explanations live beside the behaviour they describe so they version together. |
| Household-facing text | Jellyseerr and Jellyfin own their own wording; lemonfiber doesn't rewrite it. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **G2-R1** | Domain terms MUST carry an inline explanation wherever they appear in the interface. |
| **G2-R2** | Explanations MUST state purpose and consequence, not formal definition. |
| **G2-R3** | One concept MUST use one term consistently across all surfaces and messages. |
| **G2-R4** | Sizes, durations and rates MUST be contextualised where the consequence is knowable. |
| **G2-R5** | Plain language MUST accompany the domain term, not replace it. |
| **G2-R6** | Extended explanation MUST be available on request and MUST NOT be mandatory. |
| **G2-R7** | Explanations MUST be dismissible and disableable. |
| **G2-R8** | A simplification that produces a false mental model MUST NOT be used. |
| **G2-R9** | Where services use different terms for one concept, the mapping MUST be stated. |
| **G2-R10** | Error messages MUST follow the same plain-language rules. |
| **G2-R11** | Text MUST avoid idiom and cultural reference so it translates cleanly. |
| **G2-R12** | Explanations MUST be versioned alongside the behaviour they describe. |
| **G2-R13** | A domain term appearing without an explanation MUST be treated as a defect. |

## Related

- [G4 Error model](g4-error-model.md) — where clarity matters most
- [F2 Service catalogue](../f-extensibility/f2-service-catalogue.md) — service descriptions
- [A1 Prerequisites](../a-getting-started/a1-prerequisites.md) — the densest concentration of unfamiliar terms
- [D2 Quality presets](../d-content/d2-quality-presets.md) — plain language over a complex domain
- [Glossary](../../../00-overview/glossary.md)
