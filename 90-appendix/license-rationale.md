# Licence rationale

**Status:** Accepted

Governance, not architecture — which is why this lives here rather than in an
ADR. No component's design depends on the licence choice.

---

## What we chose

| Repo | Licence |
|------|---------|
| `cli` | Hippocratic License 3.0 |
| `media-stack` | Hippocratic License 3.0 |
| `homebrew-tap` | Hippocratic License 3.0 |
| `spec` | CC BY-SA 4.0 |
| `brand` — marks (`assets/logo/*`) | **Proprietary, all rights reserved** |
| `brand` — tokens + docs | Hippocratic 3.0 (tokens) / CC BY-SA 4.0 (docs) |

The [Hippocratic License](https://firstdonoharm.dev/) is an *ethical source*
licence from the Organization for Ethical Source. It grants broad permissions
while prohibiting uses that violate human rights standards.

HL3 is **modular** — a core set of terms plus optional modules. Unless a module
is explicitly adopted here, the project ships **HL3-CORE**.

## Why

The project's values are the reason. This is software for individuals running
things on their own hardware, and the licence is meant to state a position
rather than maximise adoption. Restricting harmful use is the point, not a side
effect.

## What this costs — read this before depending on it

The Hippocratic License is **not OSI-approved** and is **not recognised as open
source** by the OSI, nor as free software by the FSF. This is not an oversight
or a pending application: HL3 restricts *fields of endeavour*, which
[OSD clause 6](https://opensource.org/osd) forbids by design. The
ethical-source movement's position is that the OSD is wrong on this point — a
coherent stance, but it means the "open source" label does not apply.

Practical consequences, stated plainly:

| Area | Consequence |
|------|-------------|
| **GitHub** | Sidebar shows "Other". No recognised licence badge. |
| **crates.io** | `HL3` is not an SPDX identifier. `Cargo.toml` must use `license-file = "LICENSE.md"` instead of `license = "…"`. Publishing still works. |
| **Distro packaging** | Debian, Fedora, nixpkgs and similar will not accept it into their repositories. |
| **`homebrew-core`** | Requires OSI-approved licences. **Our own tap is unaffected** — this is why `homebrew-tap` exists and is not a limitation in practice. |
| **Corporate use** | Many legal teams auto-reject non-OSI licences. Given this is a self-hosted household tool, that's not a target audience. |
| **Contributors** | Some will decline to contribute to non-OSI-licensed projects. |
| **Enforceability** | Largely untested in court. Its practical force is normative rather than legal. |

None of these block the project. All of them are worth knowing before someone
builds on it.

## What we didn't choose

| Option | Why not |
|--------|---------|
| **AGPL-3.0-or-later** | The strongest OSI-approved approximation of the same instinct: it can't restrict *who* uses the software or *for what*, but it closes the SaaS loophole, so hosted derivatives must publish source. Rejected because the goal here is to state an ethical position directly, not to approximate it through reciprocity. Remains the obvious fallback if OSI approval ever becomes necessary. |
| **GPL-3.0** | Conventional fit for a desktop application, but weaker reciprocity than AGPL and no ethical clause — loses on both axes. |
| **MIT / Apache-2.0** | Rust ecosystem default and best for adoption. Permits exactly the unrestricted commercial use the Hippocratic choice objects to. |
| **SSPL / BUSL / Commons Clause** | Also non-OSI, but motivated by commercial moats rather than ethics. Worst of both worlds. |

## The brand marks are proprietary — deliberately

The one component that is **not** open in any form is the logo and marks
(`brand/assets/logo/*`). This is not a contradiction of the project's values; it
is the standard pattern for open projects with a protected identity.

**Rust, Mozilla, Python and Docker all do this**: the software is open, the
trademark is not. Anyone may use, fork and redistribute the code; nobody may ship
their fork under the original name and logo, because that would let a fork
impersonate the project. Trademark protection is what keeps "lemonfiber" meaning
*this* project.

So within `brand`:

- **Marks** (`assets/logo/*`) — proprietary, all rights reserved. Use requires
  permission.
- **Tokens** (`tokens/*`) — Hippocratic 3.0, because the web UI embeds them and
  they must be freely usable by anyone building on or forking the code.
- **Docs** (`docs/*`) — CC BY-SA 4.0, like the rest of the documentation.

The README states the split at the top so no one mistakes a proprietary mark for a
freely reusable asset. This keeps the "no proprietary *components*" claim honest:
the software carries none — the tokens it embeds are open — while the *identity*
is protected, which is a trademark matter, not a software-freedom one.

## Note on bundled services

Every service the stack orchestrates is OSI-licensed open source:

| Licence | Services |
|---------|----------|
| GPL-3.0 | Prowlarr, Sonarr, Radarr, Lidarr, Bazarr, Calibre-Web(-Automated), Homepage |
| GPL-2.0 | Jellyfin, SABnzbd, qBittorrent |
| MIT | Seerr, Gluetun, FlareSolverr, Recyclarr, Unpackerr |
| Apache-2.0 | NZBHydra2, Caddy |

**Our licence choice has no effect on theirs, and theirs has none on ours.**
`media-stack` distributes configuration that *references* public container
images; it does not link against, embed, or redistribute their code. No copyleft
obligation propagates in either direction.

## Documentation licence

`spec` uses **CC BY-SA 4.0**. Creative Commons licences are unsuitable for
software — [Creative Commons say so themselves](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software) —
but CC BY-SA is the right tool for prose, and its ShareAlike clause is
consistent with the reciprocity instinct behind the code licence.

## Revisiting

Reasons that would justify reopening this:

- Distribution via distro packaging becomes important.
- Contributor friction from the licence becomes measurable.
- The OSI position on ethical-source licensing changes.

If reopened, **AGPL-3.0-or-later** is the leading alternative.
