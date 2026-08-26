# Version manifests

Each file here is one release's [staged](../staging.md) state — the single source
of truth for a version's goals and progress. Named `<version>.toml`
(e.g. `0.2.0.toml`). Written by `stage-version`, read by the tracker and the gate,
and finalised by `execute-version`.

## Contract

```toml
version = "0.2.0"         # the release this manifest describes; matches the tag v0.2.0
epoch   = "v1"            # the epoch this version belongs to
status  = "staged"        # planned → staged → releasable → released → yanked
released_on = "2026-07-30"   # UTC date the release was published; written at release (OPS-R57)
released_as = "0.2.1"     # the tag that carried these goals, where it is not this version's own
repos   = ["lemonfiber", "lemonfiber-media-stack"]   # streams this version cuts; never "brand"
goals   = ["A2-R1", "A2-R6", "C1-R13"]    # locked Accepted requirement IDs (OPS-R30)

[pins]                    # written at execute (OPS-R35); absent while staged
lemonfiber-media-stack = "fbdafe0eb229c5c5016decf00b8a460b488a4225"
```

| Field | Meaning |
|-------|---------|
| `version` | Semver, matching the eventual `v<version>` tag. |
| `epoch` | The epoch this version belongs to — `v1` (features A–G) or `v2` (the ecosystem). Minors advance an epoch; a major closes it. |
| `status` | The lifecycle state ([OPS-R32](../staging.md)); every transition is recorded here. |
| `released_on` | The UTC date the release was published, `YYYY-MM-DD` ([OPS-R57](../staging.md)). Written by the transition to `released`, from the publication that triggered it — never typed. Absent on every earlier status. |
| `repos` | The release streams this version cuts. `brand` releases on its own clock and is never listed. |
| `goals` | The locked set of `Accepted` requirement IDs the release must satisfy before it ships. |
| `closes_epoch` | Present **only on an `X.0.0` major**. Names the epoch it completes; the [epoch-completeness gate](../staging.md) then refuses to ship it unless every `tracks:` feature of that epoch is `Accepted` and done. |
| `released_as` | The tag the goals actually shipped under, present **only where it is not this version's own**. A minor whose release run fails part-way is finished by a patch, and the patch is the artefact people install; there is no manifest per patch, because a patch delivers no goals and a manifest for it would be another version the serial train must walk past. Written by the transition to `released` — never typed. |
| `pins` | The exact submodule commits embedded, recorded at execute so the release is reproducible from this file alone. |

## Epochs and the no-stub-major rule

The train ships in two **epochs**: `v1` (the A–G product) reaching `1.0.0`, then
`v2` (the ecosystem) reaching `2.0.0`. Minors (`0.4.0`, `1.3.0`, …) are themed
slices toward the next major; patches (`x.y.Z`) are hotfixes. A **major closes an
epoch and MUST NOT ship with stubs** — the epoch-completeness gate asserts every
feature tagged `tracks: <epoch>` is `Accepted` and implemented before the
`X.0.0` tag. That is why a major's own `goals` list may be empty: the *epoch*, not
a per-requirement list, is what it must satisfy.

## Rules

- A goal MUST be an `Accepted` requirement; a `Draft` or `Withdrawn` one is
  rejected at staging ([OPS-R30](../staging.md)).
- Once `status = "staged"`, the `goals` set is frozen — changing it needs review
  and a maintainer-channel notice ([OPS-R31](../staging.md)).
- The file, not CI history, answers "where is this version": read `status`.
- The file, not the forge, answers "when did it ship": read `released_on`
  ([OPS-R57](../staging.md)).
- And what it shipped *as*: read `released_as` where there is one, `version`
  otherwise. A patch records the line it closed rather than a manifest of its
  own, so the train stays serial and the record still names the tag.

See [TEMPLATE.toml](TEMPLATE.toml) to start one, and [staging.md](../staging.md)
for the lifecycle these files move through.
