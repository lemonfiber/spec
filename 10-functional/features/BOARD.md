# Feature board

**Status:** Accepted

Generated from feature frontmatter and the version manifests by
`scripts/gen_board.py` — do not edit by hand; `just board` regenerates it.

## v1 — the product (areas A–G, and L1 to release it)

| ID | Feature | Area | Audience | Status | Ships in |
|----|---------|------|----------|--------|----------|
| [A1](a-getting-started/a1-prerequisites.md) | Prerequisites & account guidance | A | operator | accepted | `0.2.0` |
| [A2](a-getting-started/a2-setup-wizard.md) | Setup wizard | A | operator | accepted | `0.2.0` |
| [A3](a-getting-started/a3-credential-validation.md) | Credential validation | A | operator | accepted | `0.13.0`, `0.2.0` |
| [A4](a-getting-started/a4-reconfiguration.md) | Reconfiguration | A | operator | accepted | `0.13.0` |
| [A5](a-getting-started/a5-migration.md) | Migration from an existing stack | A | operator | accepted | `0.13.0` |
| [A6](a-getting-started/a6-uninstall.md) | Clean uninstall | A | operator | accepted | `0.13.0` |
| [A7](a-getting-started/a7-credential-management.md) | Credential management & rotation | A | operator | accepted | `0.13.0` |
| [B1](b-running/b1-forms.md) | Forms & partial stacks | B | operator | accepted | `0.1.0`, `0.8.0` |
| [B2](b-running/b2-lifecycle.md) | Lifecycle control | B | operator | accepted | `0.8.0` |
| [B3](b-running/b3-dashboard.md) | Live dashboard | B | operator | accepted | `0.5.0`, `1.0.0` |
| [B4](b-running/b4-logs.md) | Log viewing | B | operator | accepted | `0.8.0` |
| [B5](b-running/b5-notifications.md) | Notifications & alerting | B | both | accepted | `0.5.0` |
| [B6](b-running/b6-remote-stack.md) | Controlling a stack on another machine | B | operator | accepted | `0.15.0` |
| [B8](b-running/b8-autostart.md) | Autostart & boot persistence | B | operator | accepted | `0.15.0` |
| [C1](c-trust/c1-diagnostics.md) | Diagnostics | C | operator | accepted | `0.1.0`, `0.2.0`, `0.8.0` |
| [C2](c-trust/c2-vpn-verification.md) | VPN verification | C | operator | accepted | `0.6.0` |
| [C3](c-trust/c3-auto-remediation.md) | Auto-remediation | C | operator | accepted | `0.7.0` |
| [C4](c-trust/c4-support-bundle.md) | Support bundle | C | operator | accepted | `0.7.0` |
| [C5](c-trust/c5-storage.md) | Storage & hardlink management | C | operator | accepted | `0.2.0`, `0.6.0` |
| [C6](c-trust/c6-web-security.md) | Web UI security & binding policy | C | operator | accepted | `0.10.0` |
| [C7](c-trust/c7-queue-health.md) | Queue health & stuck items | C | operator | accepted | `0.6.0` |
| [C8](c-trust/c8-provider-health.md) | Provider health & quota tracking | C | operator | accepted | `0.7.0` |
| [C9](c-trust/c9-drift.md) | Config drift detection & seed policy | C | operator | accepted | `0.4.0`, `0.7.0` |
| [D1](d-content/d1-seed.md) | Service auto-wiring | D | operator | accepted | `0.4.0` |
| [D2](d-content/d2-quality-presets.md) | Quality presets in plain language | D | operator | accepted | `0.4.0` |
| [D3](d-content/d3-first-content.md) | First-content walkthrough | D | operator | accepted | `0.4.0` |
| [D4](d-content/d4-request-flow.md) | Household request flow | D | household | accepted | `0.11.0` |
| [D5](d-content/d5-disk-space.md) | Disk space management | D | operator | accepted | `0.12.0` |
| [D6](d-content/d6-household-identity.md) | Household identity & invitations | D | both | accepted | `0.11.0` |
| [D7](d-content/d7-approval-quotas.md) | Request approval & quotas | D | both | accepted | `0.12.0` |
| [D8](d-content/d8-parental-controls.md) | Parental controls | D | both | accepted | `0.12.0` |
| [D9](d-content/d9-pipeline-trace.md) | "Where is my show?" pipeline trace | D | both | accepted | `0.4.0` |
| [D10](d-content/d10-bandwidth.md) | Bandwidth & scheduling | D | operator | accepted | `0.12.0` |
| [E1](e-maintenance/e1-stack-updates.md) | Stack updates | E | operator | accepted | `0.14.0` |
| [E2](e-maintenance/e2-self-update.md) | lemonfiber self-update | E | operator | accepted | `0.14.0` |
| [E3](e-maintenance/e3-backup-restore.md) | Backup & restore | E | operator | accepted | `0.14.0`, `0.3.0` |
| [E4](e-maintenance/e4-rollback.md) | Rollback | E | operator | accepted | `0.14.0` |
| [E5](e-maintenance/e5-changelog.md) | Changelog & release notes | E | operator | accepted | `0.14.0` |
| [F1](f-extensibility/f1-customisation.md) | Customisation & escape hatches | F | operator | accepted | `0.15.0` |
| [F2](f-extensibility/f2-service-catalogue.md) | Service catalogue | F | operator | accepted | `0.15.0` |
| [G1](g-ux/g1-interface-tiers.md) | Interface tiers | G | both | accepted | `0.9.0` |
| [G2](g-ux/g2-plain-language.md) | Plain-language layer & in-product help | G | both | accepted | `0.9.0` |
| [G3](g-ux/g3-accessibility.md) | Accessibility | G | both | accepted | `0.9.0` |
| [G4](g-ux/g4-error-model.md) | Error & remedy model | G | both | accepted | `0.5.0` |
| [G5](g-ux/g5-front-door.md) | The front door | G | both | accepted | `0.10.0` |
| [G6](g-ux/g6-client-apps.md) | Client app guidance | G | household | accepted | `0.11.0` |
| [G7](g-ux/g7-health-summary.md) | Overall health summary | G | operator | accepted | `0.5.0` |
| [G8](g-ux/g8-privacy.md) | Privacy stance | G | both | accepted | `0.10.0` |
| [L1](l-release/l1-release-engineering.md) | v1 release engineering | L | operator | accepted | `1.0.0` |

## v2 — the ecosystem (areas H–K, plus F3, and L2 to release it)

| ID | Feature | Area | Audience | Status | Ships in |
|----|---------|------|----------|--------|----------|
| [B9](b-running/b9-notification-backends.md) | Open notification back-ends | B | both | accepted | `2.5.0` |
| [F3](f-extensibility/f3-stack-manifests.md) | Third-party stack manifests | F | operator | draft | `2.4.0` |
| [G9](g-ux/g9-mobile-handoff.md) | Mobile client handoff | G | both | accepted | `2.4.0` |
| [H1](h-glue/h1-cross-seed.md) | Cross-seeding | H | operator | accepted | `2.1.0` |
| [H2](h-glue/h2-autobrr.md) | Announce-driven grabbing | H | operator | accepted | `2.1.0` |
| [H3](h-glue/h3-quality-sync.md) | Quality-profile sync | H | operator | accepted | `2.1.0` |
| [H4](h-glue/h4-subtitles.md) | Subtitles | H | both | accepted | `2.1.0` |
| [H5](h-glue/h5-queue-selfheal.md) | Queue self-healing | H | operator | accepted | `2.2.0` |
| [H6](h-glue/h6-library-cleanup.md) | Library cleanup | H | both | accepted | `2.2.0` |
| [H7](h-glue/h7-transcoding.md) | Transcoding | H | operator | accepted | `2.2.0` |
| [H8](h-glue/h8-stats.md) | Playback statistics | H | both | accepted | `2.2.0` |
| [I1](i-remote-access/i1-remote-access.md) | Remote access for the household | I | both | accepted | `2.3.0` |
| [I2](i-remote-access/i2-identity.md) | Household identity & single sign-on | I | both | accepted | `2.3.0` |
| [J1](j-runtime/j1-engine-abstraction.md) | Container-engine abstraction | J | operator | draft | `2.0.0` |
| [J2](j-runtime/j2-podman.md) | Running under Podman | J | operator | draft | `2.0.0` |
| [J3](j-runtime/j3-native.md) | Running natively, without containers | J | operator | draft | `2.0.0` |
| [K1](k-observability/k1-metrics.md) | Metrics & dashboards | K | operator | accepted | `2.5.0` |
| [K2](k-observability/k2-uptime.md) | Uptime monitoring | K | operator | accepted | `2.5.0` |
| [L2](l-release/l2-v2-release.md) | v2 release | L | operator | accepted | `2.0.0` |
