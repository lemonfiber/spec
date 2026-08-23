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

## What is here

| File | Copied to | Rule |
|------|-----------|------|
| [markdownlint.jsonc](markdownlint.jsonc) | each repo's `.markdownlint.jsonc` | Byte-identical, key order included |
| [typos.toml](typos.toml) | each repo's `typos.toml` | Every entry present; a repo may add more |
| [assets.sha256](assets.sha256) | — | Digests of the brand assets repos carry copies of |

The two configs differ in kind deliberately. A markdown rule that one repo needs
costs the others nothing, so one file serves everybody. A spelling allowance is
about a specific tree — the site excludes its Dutch translations, this repo
allows `UPnP` — so the shared file is a floor rather than a copy.

## What enforces it

The `shared-files` job in the hygiene gate, which runs
[`scripts/check_shared_files.py`](../scripts/check_shared_files.py) against the
calling repository. It fails on a config that differs, a shared word that is
missing, and a brand asset that has been edited in place instead of copied again.

## Changing one of them

A change here reaches a repo when that repo's next hygiene run compares against
it, so land the change and the copies together. Cite `GOV-R12` — configuration is
routine maintenance ([change lifecycle](../50-governance/change-lifecycle.md)).

## Related

- [40-quality/tooling.md](../40-quality/tooling.md) — the anti-drift posture this belongs to
- [50-governance/cross-repo-ci.md](../50-governance/cross-repo-ci.md) — reusable workflows, the other half
