# Shared files

**Status:** Accepted

The canonical copy of every file more than one repository has to carry.

---

## Why copies exist at all

The [hygiene gate](../.github/workflows/hygiene.yml) checks out the **calling**
repository and lints that tree, so `typos` and `markdownlint` read the calling
repo's own config. GitHub renders a README from the repository it lives in, so a
badge or a logo resolves against that repo's tree. Neither tool can be pointed at
a file in another repository, and the `.github` repo's community-file inheritance
does not reach either of them.

So the copies are load-bearing and cannot be deleted. What can be removed is the
*drift*: before this directory existed there were four different
`.markdownlint.jsonc` files across the org, two of them holding identical rules in
different key order.

A built application is the third reason, and it is the same one: the companion
app is a bundle on a phone, so a value it paints has to be inside that bundle at
build time — there is no request during which it could reach another repository.
It carries the brand's token file for that reason and checks the two colours it
asserts against it, and the row here is what keeps that copy equal to the
brand's own.

## What is here

| File | Copied to | Rule |
|------|-----------|------|
| [markdownlint.jsonc](markdownlint.jsonc) | each repo's `.markdownlint.jsonc` | Byte-identical, key order included |
| [typos.toml](typos.toml) | each repo's `typos.toml` | Every entry present; a repo may add more |
| [ruff.toml](ruff.toml) | each Python-carrying repo's `ruff.toml` | Every shared rule selected and none of them ignored; a repo may select more |
| [hooks/pre-push](hooks/pre-push) | each repo's `.githooks/pre-push` | Byte-identical, where a repo has adopted it |
| [hooks/commit-msg](hooks/commit-msg) | each repo's `.githooks/commit-msg` | Byte-identical, where a repo has adopted it |
| — | each repo's `.githooks/pre-commit` | Not shared: the fast checks are different in each. Its *absence* is not checked, and a hook-manager config in its place is refused |
| [gates/no_open_codeql_alert.py](gates/no_open_codeql_alert.py) | each repo's `scripts/no_open_codeql_alert.py` | Byte-identical, where a repo has adopted it |
| [assets.sha256](assets.sha256) | — | Digests of the brand assets repos carry copies of |

`gates/` is for scripts that decide whether a branch merges, and they are held to
the strictest of the rules above: byte-identical, and compared as bytes so a copy
rewritten with CRLF endings cannot read as the same file. A drifted gate is worse
than a missing one, because it is trusted — `no_open_codeql_alert.py` spent its
whole life reading an empty alert list as an analysed and clean one, and a
repository still carrying that version would report a pass it had not earned.

Adoption is per repository and conditional: a repository gating on none of them
is not asked for one. What is refused is carrying a copy that is not the current
one.

Each asset row is read from both ends. In a repository carrying a copy, the copy
is checked against the digest. In the repository that *is* the home, the original
is checked against the digest instead — so changing an original and leaving the
record behind is refused there, on the day, rather than leaving every copy in
step with a record that has stopped describing anything. It takes nothing away
from a home repository: it changes its own files whenever it likes, and moves the
digest and the copies in the same round.

The three lint configs differ in kind deliberately. A markdown rule that one repo
needs costs the others nothing, so one file serves everybody. A spelling allowance
is about a specific tree — the site excludes its Dutch translations, this repo
allows `UPnP` — so the shared file is a floor rather than a copy.

`ruff.toml` is a floor in one direction and a ceiling in the other, which is the
asymmetry the other two do not need. Selecting a rule a repo's own scripts want
raises that repo's standard and costs nobody anything, so a copy may add. Ignoring
one lowers the standard every repo is held to while looking like a local decision,
so a copy may not silence what this file keeps — an allowance belongs here, with
the reason, where every copy takes it at once.

It is also not byte-identical, and that is the difference from `markdownlint.jsonc`:
each copy opens with a paragraph saying what *that* repository's scripts are and
why they are worth linting, because the scripts are different in each. What has to
agree is the two lists and the width. Four repositories carry one today —
`lemonfiber`, `lemonfiber-media-stack`, `brand` and this one — and every one of
them held identical lists that nothing compared, which is four lists that agree
until the first is edited.

## The pre-push hook

Twice, a `git checkout` that failed silently left a shell on the trunk, and the
push that followed sent the trunk over a feature branch — deleting its commits
and closing its pull request. Neither time was the mistake visible while it
happened: every command succeeded on its own terms, `git rebase` correctly
reported "up to date", and the push was a legitimate force-push to a branch that
legitimately existed.

The hook asks the one question that sequence never did — does what is being
pushed differ from the trunk at all — and refuses a push straight to `main`
besides. It permits every ordinary force-push, because a rebased branch is still
ahead of the trunk; only one that has been *replaced* by the trunk is not.

It is a copy rather than a reference because git reads hooks from the tree it is
given, the same reason the lint configs are copied.

Adoption is per repo and the check below is conditional, so a repo without a copy
is not failed for it — but a repo that carries one must carry the current one. A
guard that has quietly drifted is worse than none, because it is trusted.

## Turning it on

Git reads `.git/hooks` unless `core.hooksPath` says otherwise, and that setting is
per-clone local config. **No commit can carry it**, so every repo has to set it
from a command a contributor was going to run anyway:

| Repo | Set by | Fires on |
|------|--------|----------|
| `lemonfiber`, `lemonfiber-media-stack`, `spec` | the `hooks` recipe, which `just ci` depends on | `just ci` or `just hooks` |
| `sdk-ts`, `lemonfiber-web`, `website-docs.lemonfiber.app`, `website-lemonfiber.app` | npm's `prepare` script | `npm install` or `npm ci` |
| `sdk-php` | Composer's `post-install-cmd` and `post-update-cmd` | `composer install` or `composer update` |
| `homebrew-tap` | the `hooks` recipe, which `just ci` depends on | `just ci` or `just hooks` |

Each is `git config core.hooksPath .githooks` under a different name. Run it by
hand in a clone where it has not happened yet.

## Where it still does not reach

Stated plainly, because a guard half the people believe in is worse than none:

- **A clone nobody has installed dependencies into has no hook.** Cloning and
  pushing without running `just ci`, `npm ci` or `composer install` is enough to
  skip it, and nothing in a repository can change that.
- `npm install <package>` and `npm install --ignore-scripts` do not run `prepare`;
  neither does `composer install --no-scripts`.
- A hook manager that writes `.git/hooks` — lefthook, CaptainHook — is inert while
  `core.hooksPath` is set, because git then reads only the path it names. lefthook
  2.x refuses to install for exactly that reason and offers `--reset-hooks-path`,
  which turns this hook **off**: the one command that repairs the dead config
  disables the working one. Six repos carried a `lefthook.yml` and `sdk-php` a
  `captainhook.json`, none of them installed anywhere; all are gone, every repo
  carries a `pre-commit` in `.githooks/`, and `check_shared_files.py` refuses a
  hook-manager config coming back
  ([tooling](../40-quality/tooling.md#the-hooks-and-why-there-is-no-hook-manager)).

Refusing a push straight to `main` is belt and braces: branch protection already
enforces it server-side on every repo, for everyone, hook or not. Refusing a push
that would empty a branch has no server-side equivalent, so it exists only where
the hook is on.

## What enforces it

The `shared-files` job in the hygiene gate, which runs
[`scripts/check_shared_files.py`](../scripts/check_shared_files.py) against the
calling repository. It fails on a config that differs, a shared word that is
missing, a lint rule that has been dropped or silenced, and a brand asset that has
been edited in place instead of copied again.

It also fails on a file added to this directory that no check there looks at,
because a shared file nothing compares is copied into every repository and held to
in none — and the run still says the copies match, which is true of the ones it
looked at and reads as an account of all of them.

## Changing one of them

A change here reaches a repo when that repo's next hygiene run compares against
it, so land the change and the copies together. Cite `GOV-R12` — configuration is
routine maintenance ([change lifecycle](../50-governance/change-lifecycle.md)).

## Related

- [40-quality/tooling.md](../40-quality/tooling.md) — the anti-drift posture this belongs to
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — reusable workflows, the other half
