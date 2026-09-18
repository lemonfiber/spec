# Contributing

**Status:** Accepted

The practical version. If you read one governance document, read this one.

---

## The rule in one line

**Every change cites something in the spec, and that something already exists.**

## Which case are you in?

### "I'm implementing something already in the spec"

The common case. Find the requirement, cite it, write the code.

```
feat: health-gate service startup

Spec: B2-R1, B2-R2
```

Put the same IDs in your PR body. Done.

### "I want to change how the product behaves"

Open a **spec PR first**.

1. Find or add the requirement in [10-functional/features](../10-functional/features/).
2. Open a PR against this repo.
3. Once it's merged, open your implementation PR citing the new ID.

The spec PR is usually small — one row in a requirements table and a paragraph
explaining the behaviour. It's not an essay.

**Why the extra step:** it separates *"should the product do this?"* from
*"is this code good?"*. Reviewed together, working code tends to win the first
question by default, because working code is persuasive. Reviewed apart, the
design gets judged on its merits.

### "I'm bumping a dependency / fixing a typo / touching CI"

Cite `GOV-R12`.

```
chore: bump tokio to 1.48

Spec: GOV-R12
```

### "I found a bug"

A bug is behaviour that contradicts the spec. Cite the requirement it violates:

```
fix: stop reporting killswitch as passing when untested

Spec: C2-R7
```

If the spec doesn't cover it, the spec has a gap — open a spec PR describing what
should happen, then fix it.

## Finding the right identifier

| Looking for | Go to |
|-------------|-------|
| What the product should do | [feature catalogue](../10-functional/features/) — every feature, by area |
| Why something is built this way | [decisions](../00-overview/decisions/) — ADRs |
| A specific behaviour | Search the spec for the behaviour, not the code |
| Routine maintenance | `GOV-R12` |

Requirement IDs look like `A2-R4`: feature `A2`, fourth requirement. Every one is
in a table at the bottom of its feature doc.

## What a commit message has to carry

Four things. Each is a separate check, each speaks after a push and a red run,
and one hook says all four before any of that.

| Rule | What it looks like | Check |
|------|--------------------|-------|
| A conventional subject (**OPS-R21**) | `feat: health-gate service startup` | `commitlint` |
| A DCO sign-off (**GOV-R29**) | `Signed-off-by: Your Name <you@example.com>` | `dco` |
| A citation of something in this spec (**GOV-R2**) | `Spec: B2-R1, B2-R2` | `spec-check` |
| No credit to the tool that wrote it (**GOV-R46**) | no `Co-authored-by:` naming an assistant | `attribution` |

The subject types are `feat fix docs refactor test chore ci perf build style
revert`, optionally scoped (`feat(api):`) and optionally breaking (`feat!:`). A
merge, a revert and a `fixup!` are written by git and are exempt, here and in CI.

### Turn the hook on, and none of the four costs a round trip

```sh
git config core.hooksPath .githooks
```

Every repository in the organisation carries `.githooks/commit-msg`; it is the
same file in each, held byte-identical to
[shared/hooks/commit-msg](../shared/hooks/commit-msg), and it names all four at
once with the literal line to add. It enforces nothing CI does not (**Q-R57**) —
where the two differ, CI is right and the hook is wrong.

The setting is per-clone local config, so no commit can carry it. Each repository
hangs it on a command you were going to run anyway — `just ci`, `npm install` or
`composer install`, whichever that repository has — and the line above is for a
clone where none of them has been run yet.
[shared/README.md](../shared/README.md#turning-it-on) is which repository uses
which name, and [adoption.toml](../shared/adoption.toml) is which repositories
carry the hooks at all.

### Signing is a fifth thing, and a different one

A sign-off is an assertion about rights; a signature is proof of identity. `main`
requires both.

`git config commit.gpgsign true` once, and always commit with `-s`, and both are
handled. Your contribution ships under the repo's licence (Hippocratic 3.0 for
code) — inbound equals outbound, no CLA. See [dco.md](dco.md).

## What not to do

**Don't put requirement IDs in code comments.** Ever. Not as a breadcrumb, not
"just this once". Provenance in a comment is worthless to the next reader and
rots the moment the requirement is superseded. IDs go in commits and PRs; code
links to `lemonfiber/.docs/`, and those pages cite the spec.

See [GOV-R6](canonical-spec.md#the-gov-r-namespace) and the
[comment policy](../40-quality/code-comments.md).

**Don't cite a Draft requirement.** Draft means undecided. If you're implementing
it, it should be Accepted first.

**Don't write the spec change to match code you've already written.** It's
technically possible and it inverts the whole point. If implementation taught you
something, say so in the spec PR — that's valuable and welcome.

## When your PR is closed

It will say something close to this:

> Thanks for this — the change itself looks fine, and it isn't rejected.
>
> This org keeps its specification canonical: every change references something
> in [lemonfiber/spec](https://github.com/lemonfiber/spec) that already exists
> there. It stops the spec drifting behind the code, which is the failure mode
> that makes specifications useless.
>
> Your PR doesn't cite a spec identifier yet. To proceed:
>
> **If this implements something already specified** — find the requirement,
> add a trailer to your commit, and reopen:
>
> ```
> Spec: A2-R4
> ```
>
> **If this changes product behaviour** — open a small PR against the spec repo
> first. Usually one requirement row and a short paragraph. Once it merges, cite
> the new ID here and reopen.
>
> **If this is routine maintenance** (dependencies, formatting, CI) — cite
> `GOV-R12` and reopen.
>
> Full guide: [contributing](https://github.com/lemonfiber/spec/blob/main/50-governance/contributing.md).
> Happy to help find the right identifier — just ask here.

**Reopening costs one click.** Nothing is lost, and no work is thrown away.

## If you disagree with the rule

Say so — in an issue on the spec repo, or in the PR. The rule is written down
precisely so it can be argued with, and changing it is itself a spec PR
(**GOV-R11**).

What isn't available is quietly ignoring it, because then the rule stops meaning
anything and the drift it prevents starts happening again.

## Questions

Ask on [Discord](https://discord.nightworks.io), or open an issue. If you're not
sure which repo an issue belongs in, file it anywhere — routing is a maintainer's
job rather than a reporter's (**GOV-R25**).

## Related

- [change-lifecycle.md](change-lifecycle.md) — the full flow
- [cross-repo-ci.md](cross-repo-ci.md) — what the bot checks
- [dco.md](dco.md) — the sign-off, and what it asserts
- [ai-contributors.md](ai-contributors.md) — **GOV-R46** and the rest of what an assistant is held to
- [issue-routing.md](issue-routing.md) — which repo an issue belongs in
- [40-quality/](../40-quality/) — code standards
