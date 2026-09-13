# Version manifests

Each file here is one release's [staged](../staging.md) state — the single source
of truth for a version's goals and progress. Named `<version>.toml`
(e.g. `0.2.0.toml`). Written by `stage-version`, read by the tracker and the gate,
and finalised by `execute-version`.

## Contract

```toml
version = "0.2.0"         # the release this manifest describes; matches the tag v0.2.0
status  = "staged"        # planned → staged → in_progress → releasable → released → yanked
released_on = "2026-07-30"   # UTC date the release was published; written at release (OPS-R57)
released_as = "0.2.1"     # the tag that carried these goals, where it is not this version's own
withdrawn_because = "the installer shipped a broken pin"   # why it was yanked; only on `yanked` (E5-R8)
repos   = ["lemonfiber", "lemonfiber-media-stack"]   # streams this version cuts; never "brand"
satisfied_in = ["lemonfiber", "lemonfiber-web"]   # where the goal gate searches; omit to mean `repos`
goals   = ["A2-R1", "A2-R6", "C1-R13"]    # locked Accepted requirement IDs (OPS-R30)

[pins]                    # written at execute (OPS-R35); absent while staged
lemonfiber-media-stack = "fbdafe0eb229c5c5016decf00b8a460b488a4225"   # one line per embedded submodule
lemonfiber-web = "ed49b4224f91d4e53055910e27db5d1b697a2de3"
```

| Field | Meaning |
|-------|---------|
| `version` | Semver, matching the eventual `v<version>` tag. |
| `status` | The lifecycle state ([OPS-R32](../staging.md)); every transition is recorded here. |
| `released_on` | The UTC date the release was published, `YYYY-MM-DD` ([OPS-R57](../staging.md)). Written by the transition to `released`, from the publication that triggered it — never typed. Absent on every earlier status. |
| `repos` | The release streams this version cuts. `brand` releases on its own clock and is never listed. |
| `satisfied_in` | The repositories the goal gate searches for `Spec:` citations ([OPS-R58](../staging.md)). Omit it and the streams in `repos` are searched, which is right whenever the two coincide. They do not always. `0.10.0` cuts `lemonfiber` alone and its goals are satisfied across four repositories: `ARCH-R55` is cited in `lemonfiber-web`, and `ARCH-R58` and `ARCH-R67` in the two SDKs, which are rules only an SDK can be held to. Searched where it cuts, its gate calls all three unmet for a reason that is not about the work. `0.9.0` avoided that by putting `lemonfiber-web` in `repos`, and bought a different problem: `execute-version` tags every stream it names, and `lemonfiber-web` publishes on a version tag, so the first release run through the train would have published a build nobody asked for. Naming a repository here does **not** tag it; only `repos` does. **Write it by checking rather than from memory**: `0.10.0`'s list was drafted three times and was short each time — first missing the web surface, then the two SDKs, then the stack, and each omission read as a goal nobody had done. Run the gate over the manifest with a repository added and see whether any verdict changes; one that does belongs on the list. |
| `goals` | The locked set of `Accepted` requirement IDs the release must satisfy before it ships. |
| `withdrawn_because` | Why a shipped release was withdrawn, in one plain sentence. Present **only** on a `yanked` manifest, and required there: a withdrawal recorded bare is the record losing the only thing anyone comes back to it for. The release is never removed — the manifest stays, its `goals` stay, and this says what went wrong ([E5-R8](../../10-functional/features/e-maintenance/e5-changelog.md), [E5-R12](../../10-functional/features/e-maintenance/e5-changelog.md)). Written by the transition to `yanked`, which refuses without it. |
| `released_as` | The tag the goals actually shipped under, present **only where it is not this version's own**. A minor whose release run fails part-way is finished by a patch, and the patch is the artefact people install; there is no manifest per patch, because a patch delivers no goals and a manifest for it would be another version the serial train must walk past. Written by the transition to `released` — never typed. |
| `pins` | The exact submodule commits embedded, recorded at execute so the release is reproducible from this file alone. **One line per submodule the tag declares**, named for the repository rather than the path it is mounted at — `lemonfiber-media-stack`, not `assets/media-stack`. The list is enumerated from the tag's own `.gitmodules`, not named in the workflow: `release-finalize` spelled out the one path that existed when it was written, and went on recording only that one after [ADR-0012](../../00-overview/decisions/0012-web-assets-embedded-at-build-time.md) added the web app, so `0.10.0` first shipped a record that did not say which build of the app went out with it. |

## The no-stub rule

Minors (`0.4.0`, `1.3.0`, …) are themed slices toward the next major; patches
(`x.y.Z`) are hotfixes; a major (`X.0.0`) carries the capability that justifies
the number. Whichever it is, **a version MUST NOT ship a feature it has not
finished** — before the tag, every feature this manifest's `goals` name has to be
**`built`** in the [catalogue](../../10-functional/features/README.md), which
[OPS-R54](../staging.md) states in full along with why it is `built` rather than
`shipped`. A goal is a requirement, and a feature is more than its requirements
taken one at a time; a major's list is measured against both.

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
