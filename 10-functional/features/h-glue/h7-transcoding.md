---
id: H7
title: Transcoding
kind: feature
area: H
audience: operator
status: accepted
tracks: v2
milestone: M7
priority: P3
labels: [transcoding, quality, verification, wiring]
depends: [C5]
---

# H7 — Transcoding

**Status:** Accepted · **Audience:** Operator · **Area:** H — Ecosystem glue

---

## Purpose

Normalise the library's formats and trim on-the-fly transcode load by transcoding
in advance — converting oddball or heavyweight files into a consistent, direct-play
profile so the media server spends less effort re-encoding at watch time. The work
is done by an open-source, self-hostable transcoder of the Unmanic class, and the
choice is deliberate: this feature refuses a freemium tool whose full capability
lives behind a paywall or a hosted control plane.

The value is not "we started a transcoder". It is that a transcode **actually
completed on a real file**, and — where hardware acceleration was asked for — that
the GPU was genuinely mapped and used, not merely present in a config. GPU
passthrough is the step that silently defeats even experienced operators; H7 proves
it rather than assuming it.

## Behaviour

### It uses an open-source transcoder, never a freemium one

The transcoding engine MUST be open-source and self-hostable, with no capability
gated behind a paid tier or an external coordinator. A freemium tool may be named in
documentation as something the operator could wire by hand, but it is never
configured as the built-in path.

### It registers a worker before it claims readiness

Transcoding is only considered available once a worker or node has actually
registered with the engine. A configured-but-unregistered worker is reported as
not-ready — the operator is told the difference between "set up" and "able to do
work".

### It proves the pipeline with a real test transcode

Before the library is handed to it, H7 runs a **test transcode of a known file** end
to end and asserts it completed and produced a valid output. A pipeline that has
never successfully converted a single file is not trusted with the library, no
matter how healthy its status endpoint looks.

### It verifies hardware acceleration is real, not assumed

When hardware acceleration is requested, H7 confirms the GPU device is actually
mapped into the worker and exercised by a real transcode — reading back that the job
ran on the accelerator rather than quietly falling to the CPU. A request for HW
accel that lands on software is reported as such, loudly, because a silent CPU
fallback is the exact failure that surprises operators when their library is large
and their evenings are not.

### It transcodes non-destructively and reversibly

The source file is not replaced until its transcode has been verified as valid, and
the replacement path keeps a remedy: a corrupt or failed output never overwrites a
good original, and a conversion that degrades a file can be rolled back to the
source. Transcoding that loses the only good copy of a title is treated as a defect.

### It normalises toward direct play

Rules target the formats and codecs that force the media server to re-encode at
watch time, converting them toward a profile the household's devices can play
directly — reducing live transcode load, which is the point.

### It manages a bounded queue

Work is queued and rate-limited so a large backlog does not saturate the host or
starve live playback; the queue's depth and per-file outcomes are readable.

### Every step has a non-interactive equivalent

Worker registration status, the test transcode, the HW-accel verification, and a
library-wide run are each reachable as plain subcommands, so transcoding can be
wired into maintenance without a prompt.

## States

| State | Meaning |
|-------|---------|
| `unregistered` | No worker registered; transcoding not yet available |
| `verifying` | Running the test transcode and, if requested, the HW-accel check |
| `ready` | A worker is registered and the test transcode succeeded |
| `hw-verified` | Ready, and hardware acceleration confirmed mapped and used |
| `sw-fallback` | Ready, but a requested accelerator was not usable; running on CPU, stated plainly |
| `working` | Transcoding the queue, per-file outcomes recorded |
| `degraded` | The engine or a worker unreachable; the library is not handed over |

## Edge cases

| Situation | Behaviour |
|-----------|-----------|
| Platform has no hardware acceleration | On the two of three platforms without HW accel, run on CPU and say so; never advertise an accelerator the platform cannot provide. |
| Driver or kernel update silently breaks HW transcode | Re-verify HW accel on start and after updates; a formerly-working accelerator that now fails drops to `sw-fallback` with the reason, rather than silently CPU-encoding. |
| A transcode corrupts or fails a file | The source is never replaced by an invalid output; the failure is recorded and the original preserved. |
| Requested HW accel falls back to software | Report `sw-fallback` loudly with the cause; do not present a CPU transcode as the accelerated path the operator asked for. |
| Queue backlog grows faster than throughput | Rate-limit and report the backlog honestly; never saturate the host or starve live playback to drain it. |
| Worker registers then disappears mid-job | Mark the in-flight file incomplete, preserve its source, and requeue rather than leaving a half-written output as the library copy. |
| Output would be larger or lower quality than source | Skip or flag the conversion rather than degrade a file in the name of normalisation. |
| Test transcode fails | Stay out of `ready`; do not run the library through a pipeline that could not convert a known file. |
| Live playback needs the GPU the queue is using | Yield to live transcode demand; batch work is lower priority than a household member watching now. |
| Unsupported or DRM-locked source | Skip with a clear reason; never leave a partial or broken output in place of a file it could not process. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **H7-R1** | The transcoding engine MUST be open-source and self-hostable, with no capability gated behind a paid tier or external coordinator; a freemium tool MUST NOT be configured as the built-in path. |
| **H7-R2** | Transcoding MUST NOT be reported as available until a worker or node has actually registered with the engine. |
| **H7-R3** | The tool MUST run a test transcode of a known file end to end and assert a valid output before handing the library to the pipeline. |
| **H7-R4** | When hardware acceleration is requested, the tool MUST verify the GPU device is mapped into the worker and used by a real transcode, and MUST NOT assume it from configuration. |
| **H7-R5** | A requested accelerator that is not usable MUST be reported as a software fallback with its cause, and MUST NOT be presented as an accelerated path. |
| **H7-R6** | HW-accel verification MUST re-run on start and after driver or kernel updates, so a broken accelerator drops to reported fallback rather than silent CPU encoding. |
| **H7-R7** | A source file MUST NOT be replaced until its transcode is verified valid; a corrupt or failed output MUST NOT overwrite the original. |
| **H7-R8** | A conversion MUST be reversible to its source, so a degraded transcode can be rolled back. |
| **H7-R9** | On platforms without hardware acceleration, the tool MUST run on CPU and state so, and MUST NOT advertise an accelerator the platform cannot provide. |
| **H7-R10** | Work MUST be queued and rate-limited so a backlog cannot saturate the host, and MUST yield to live playback transcode demand. |
| **H7-R11** | A worker that disappears mid-job MUST leave the source preserved and the file requeued, never a half-written output as the library copy. |
| **H7-R12** | A conversion that would enlarge or lower the quality of a file MUST be skipped or flagged rather than silently degrade it. |
| **H7-R13** | An unsupported or DRM-locked source MUST be skipped with a clear reason and MUST NOT leave a partial output in place of the original. |
| **H7-R14** | Queue depth and per-file transcode outcomes MUST be readable. |
| **H7-R15** | Worker status, the test transcode, HW-accel verification, and a library run MUST each be reachable non-interactively. |

## Related

- [C5 Storage & hardlink management](../c-trust/c5-storage.md) — the storage layout transcoding writes into
- [B3 Live dashboard](../b-running/b3-dashboard.md) — where transcode queue and outcomes surface
- [G4 Error & remedy model](../g-ux/g4-error-model.md) — how a failed or fallback transcode carries a remedy
- [H8 Playback statistics](h8-stats.md) — the sibling read-only analytics glue
