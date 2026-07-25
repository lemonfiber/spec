# Version manifests

Each file here is one release's [staged](../staging.md) state — the single source
of truth for a version's goals and progress. Named `<version>.toml`
(e.g. `0.2.0.toml`). Written by `stage-version`, read by the tracker and the gate,
and finalised by `execute-version`.

## Contract

```toml
version = "0.2.0"         # the release this manifest describes; matches the tag v0.2.0
status  = "staged"        # planned → staged → releasable → released → yanked
repos   = ["lemonfiber", "media-stack"]   # streams this version cuts; never "brand"
goals   = ["A2-R1", "A2-R6", "C1-R13"]    # locked Accepted requirement IDs (OPS-R30)

[pins]                    # written at execute (OPS-R35); absent while staged
media-stack = "fbdafe0eb229c5c5016decf00b8a460b488a4225"
```

| Field | Meaning |
|-------|---------|
| `version` | Semver, matching the eventual `v<version>` tag. |
| `status` | The lifecycle state ([OPS-R32](../staging.md)); every transition is recorded here. |
| `repos` | The release streams this version cuts. `brand` releases on its own clock and is never listed. |
| `goals` | The locked set of `Accepted` requirement IDs the release must satisfy before it ships. |
| `pins` | The exact submodule commits embedded, recorded at execute so the release is reproducible from this file alone. |

## Rules

- A goal MUST be an `Accepted` requirement; a `Draft` or `Withdrawn` one is
  rejected at staging ([OPS-R30](../staging.md)).
- Once `status = "staged"`, the `goals` set is frozen — changing it needs review
  and a maintainer-channel notice ([OPS-R31](../staging.md)).
- The file, not CI history, answers "where is this version": read `status`.

See [TEMPLATE.toml](TEMPLATE.toml) to start one, and [staging.md](../staging.md)
for the lifecycle these files move through.
