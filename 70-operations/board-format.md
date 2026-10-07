# The board snapshot

**Status:** Accepted

The report of [where every version stands](staging.md#where-every-version-stands)
publishes two files a script reads. `state.json` holds the verdict on every goal and
nothing else. `board.json`, described here, holds everything the frontpage's roadmap
and board render (`REPO-R39`): the catalogue of features and requirements, every
version manifest with the verdict on each goal, every repository's tracker, every
open pull request and what it cites, the repositories, the releases and the
proposals. It is a reading of git at the revisions it names, and nothing in it is
kept anywhere else.

**Satisfies:** `OPS-R80`, `OPS-R81`, `OPS-R82`; read by
[`website-lemonfiber.app`](../30-repos/website-lemonfiber.md).

---

## Where it is published

Each run of the `state` workflow replaces the assets of a release named `board` in
this repository with `board.json`, `state.json` and `STATE.md`, and uploads the same
three as the run's `state` artifact. A release asset of a public repository downloads
without credentials at a fixed address, so the newest snapshot is always at
`https://github.com/lemonfiber/spec/releases/download/board/board.json` (`OPS-R81`);
an artifact needs a token to download, and is kept for ninety days as the history.

## When it is written

The report runs when a version manifest, a feature, `30-repos/repos.toml` or the
report's own code changes on `main` here; when a repository announces that its
tracker changed on its default branch; when a release is published; and hourly, as
the backstop for anything no event announced (`OPS-R82`). A scheduled run is not
relied on to happen on time.

The frontpage is asked to rebuild only when the snapshot's content changed: the run
hashes `board.json` with `generated_at` removed and compares it with the hash the
`board` release holds.

## A repository it cannot read

A repository whose history or tracker cannot be read is listed under `unread` with
the reason, and a goal it is searched in reads `unknown` unless the repositories that
could be read show it met. The rest of the snapshot is written and published
(`OPS-R76`). The release gate reads the same
repositories and still refuses a version it cannot judge (`OPS-R75`); the report
answers more questions than the gate and does not stop at the first it cannot.

## Its shape

`format` names the shape, and is `1`. A field removed, renamed or given another
meaning raises it; a field added does not, so a reader checks `format`, refuses one
it does not know, and ignores fields it does not know.

| Field | Holds |
|---|---|
| `format` | The shape of the file, `1` |
| `generated_at` | When it was written, UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| `ref` | The revision each repository was read at |
| `sources` | The full commit read of `spec` and of every repository, by name |
| `unread[]` | Each repository that could not be read: `repo`, `reason` |
| `areas[]` | Each area of the catalogue: `id`, `name`, `directory` |
| `features[]` | Each feature: `id`, `title`, `area`, `audience`, `kind`, `status`, `maturity`, `shipped`, `priority`, `labels`, `requires`, `relates`, `path`, and `versions` (each version locking one of its requirements, with that version's `status`) |
| `requirements[]` | Each requirement the specification defines: `id`, `owner` (a feature's `id`, or the path of the document defining it), `namespace`, `keyword` (`MUST`, `SHOULD` or `MAY`, the strongest it uses), `text`, `status` (`withdrawn` or `superseded` where its row says so, `draft` where its feature is Draft, otherwise `accepted`), `replaced_by` (the identifier a superseded row names), and `versions` (each version locking it) |
| `versions[]` | Each manifest in train order: `version`, `status`, `milestone`, `delivers`, `released_on`, `released_as`, `repos`, `satisfied_in`, `prereleases`, and `goals` (each with `id`, `verdict` and the evidence `state.json` gives a goal) |
| `trackers[]` | Each repository a version is satisfied in: `repo`, `present`, and `rows` (each with `id`, `state`, `evidence`, `landed`) |
| `pulls[]` | Each open pull request in those repositories: `repo`, `number`, `url`, `title`, `author`, `bot`, `draft`, `created_at`, `updated_at`, `head` (its branch), and `cites` (the identifiers its body and commits cite in `Spec:` lines) |
| `repos[]` | Each repository in `30-repos/repos.toml`: `name`, `group`, `lang`, `note`, `pages` (its specification pages), `open_pulls`, `tracker` (`present`, `absent` or `unread`) |
| `releases[]` | Each release the core's changelog records: `version`, `tag`, `released_on`, `delivers`, and `groups` (each with `title` and `entries`, each entry with `summary`, `requirements` and `reference`) |
| `proposals[]` | Each Draft feature and Draft requirement, and each open `rfc` issue: `kind`, `id` or `number`, `title`, `url` |

A goal's `verdict` is one of `state.json`'s (`met`, `unmarked`, `uncited`, `claimed`,
`open`) or `unknown`, where it is searched in a repository listed under `unread` and
the repositories that could be read do not show it met. A field with no value is `null`, and a list with no members is `[]`, never
absent.

The snapshot reads the manifests, the trackers and the citations through the same
modules as the release gate and `goals.py`, so a verdict on the board cannot differ
from the gate's.

## Requirements

| ID | Requirement |
|----|-------------|
| **OPS-R80** | The report from `OPS-R76` MUST also publish a board snapshot holding the catalogue (every feature, and every requirement with its text and status), every version manifest with the verdict on each goal, every tracker row, every open pull request with its citations, author, draft state and dates, the repositories and the releases, with the commit of every source, in a documented shape whose `format` rises when a field is removed, renamed or given another meaning. |
| **OPS-R81** | The newest board snapshot MUST be downloadable without credentials at one fixed address. |
| **OPS-R82** | The report MUST run when a version manifest, the catalogue or a repository's tracker changes on its default branch, when a release is published, and on a schedule; it MUST ask the frontpage to rebuild only when the board snapshot's content changed. |
