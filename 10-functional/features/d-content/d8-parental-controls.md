# D8 — Parental controls

**Status:** Accepted · **Audience:** Both · **Area:** D — Content & household

---

## Purpose

Let a household with children restrict what those children can watch and request,
using the ratings systems parents already understand.

Without this, a shared library is all-or-nothing: either the child has an account
that exposes everything, or they don't have an account. Both are unacceptable,
and the practical consequence is that families don't adopt the stack at all.

This is genuinely two restrictions, not one. Jellyfin can limit what is
*watchable*; Jellyseerr can limit what is *requestable*. Setting one without the
other leaves an obvious hole.

## Behaviour

### Ratings, not categories

Restrictions use the content rating systems that already exist — age ratings on
films and television. Parents understand these; a bespoke tiering system would be
another thing to learn and would map poorly onto what services actually report.

The rating system is regional. lemonfiber uses the operator's locale to present
the familiar labels rather than an arbitrary set.

### Both surfaces restricted together

Setting a limit for a household member applies to watching **and** requesting.
Configuring them separately is how the gap appears: a child who cannot watch
something but can request it, filling the library with content they aren't
permitted to see.

Set once, applied to both.

### Library-level access as the coarse control

Beyond ratings, whole libraries can be withheld. Some content isn't rated
meaningfully, and some families prefer a simple boundary.

### Unrated content is a deliberate decision

A significant amount of content carries no rating. The behaviour must be chosen,
not defaulted silently:

| Choice | Effect |
|--------|--------|
| **Block unrated** *(default for restricted members)* | Safer; some legitimate content becomes invisible |
| **Allow unrated** | More permissive; unrated content is genuinely unpredictable |

Defaulting to block for restricted members is the conservative choice, and the
consequence is stated so the operator isn't puzzled by missing content.

### Honest about what this is not

Parental controls here are a **content filter, not a security boundary**. A
determined teenager with access to the home network and a browser has options.
lemonfiber says this plainly rather than implying a guarantee it can't make.

Overstating protection is worse than an accurate modest claim, because a parent
may rely on it.

### Changes take effect promptly

Adjusting a limit applies without requiring the member to sign out and back in,
so far as the underlying services permit.

## States

Per household member:

| State | Meaning |
|-------|---------|
| `unrestricted` | Full access |
| `rating-limited` | Restricted to a maximum content rating |
| `library-limited` | Restricted to specific libraries |
| `both` | Rating and library restrictions |
| `inconsistent` | Watching and requesting restrictions disagree — **a defect to surface** |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Content has no rating | Apply the configured unrated policy; state which was applied. |
| Rating systems differ between metadata sources | Normalise to the operator's locale where possible; treat as unrated where not. |
| Watching and requesting restrictions disagree | Report `inconsistent` and offer to reconcile. This is the gap the feature exists to close. |
| Restriction tightened after content was watched | Applies going forward. Watch history is not retroactively hidden. |
| Restricted member requests blocked content | Don't offer it. Never present something then refuse it. |
| Content rating changes upstream | Re-evaluate on metadata refresh. |
| Family uses an unsupported regional rating system | Fall back to a documented equivalent and state the mapping. |
| Operator wants time-based limits | Out of scope. Neither service supports it natively and reimplementing it would be unreliable. |
| Member reaches an age where restrictions should lift | Manual. Automatic aging-up would require storing birth dates for no real gain. |
| Shared device with multiple profiles | Restrictions follow the profile, not the device. |
| Restricted member browsing a shared library | Restricted content is hidden, not shown greyed out — visibility of titles is itself sometimes the concern. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **D8-R1** | Restrictions MUST use existing content rating systems, presented in the operator's locale. |
| **D8-R2** | A restriction MUST apply to both watching and requesting from a single setting. |
| **D8-R3** | Disagreement between watching and requesting restrictions MUST be detected and reported. |
| **D8-R4** | Library-level access restriction MUST be supported independently of ratings. |
| **D8-R5** | Behaviour for unrated content MUST be explicitly configurable, defaulting to blocked for restricted members. |
| **D8-R6** | The applied unrated policy MUST be stated so unexplained absences are avoidable. |
| **D8-R7** | lemonfiber MUST state that parental controls are a content filter and not a security boundary. |
| **D8-R8** | Restricted content MUST NOT be offered to a member who cannot access it. |
| **D8-R9** | Restricted content MUST be hidden rather than displayed as unavailable. |
| **D8-R10** | Restriction changes MUST take effect without requiring re-authentication where the services permit. |
| **D8-R11** | Upstream rating changes MUST be re-evaluated on metadata refresh. |
| **D8-R12** | Unsupported regional rating systems MUST fall back to a documented mapping, and the mapping MUST be stated. |
| **D8-R13** | Restrictions MUST follow the member profile rather than the device. |

## Related

- [D6 Household identity](d6-household-identity.md) — where restrictions are set
- [D4 Household request flow](d4-request-flow.md) — the requesting surface
- [D7 Approval & quotas](d7-approval-quotas.md) — the other restriction axis
- [G2 Plain-language layer](../g-ux/g2-plain-language.md)
