# ADR-0035: What the phone keeps, and how

**Status:** Accepted
**Date:** 2026-09-29
**Decided:** 2026-09-29, by the maintainer, Wessel Verheij: readings, preferences and markers kept in the app's SQLite database, each decided by the capability it belongs to and stored by a small adapter of its own, with every payload sealed before it reaches a store, under a key the platform's secure storage holds.

## Context

The companion app keeps two things between launches today, and both are in the
platform's secure storage: the stacks it is paired with, and a session per stack
([N4](../../10-functional/features/n-companion/n4-native-integration.md), `N4-R5`).
Everything it reads from a stack lives only as long as the process does.

The spec already asks for more than that. A screen paints its first frame from what
the app holds before it reaches the stack (`N1-R25`,
[ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md)); a reading kept from
an earlier session may be shown on opening with when it was read (`N1-R24`, `N1-R9`);
a spinner is allowed only where the app holds nothing to show (`N1-R28`); and the
period after which the app asks for the passcode again is the operator's to set
(`N4-R19`). With nothing kept, every cold start is a spinner, and the lock period has
nowhere to live.

Three facts constrain how it is kept.

**What a stack says is private.** Its readings name services, members of the
household and what they asked for. The paired-stack list went into secure storage
rather than a file for exactly this reason: a file in the app's own storage is
readable by a device backup, by a rooted device, and by whatever a restore puts it
back onto.

**The framework's own key sits beside the data.** NativePHP generates an `APP_KEY`
per install and keeps it as a plain file in the app's private storage, next to the
database. Encrypting with it would put the key in the same place as what it locks.

**The app is modular, and one store would not stay small.** Every module that decides
something about a stack would add its tables, queries and migrations to whichever
module held the store, until that module held everything
([`30-repos/lemonfiber-companion.md`](../../30-repos/lemonfiber-companion.md), *How
it is laid out*).

**A capability holds no framework.** The companion's architecture keeps its capability
modules free of Laravel, so that a decision cannot be run wrong, and lets only adapter
modules touch storage (its rules A1 and A7). An adapter may use the kernel and the one
package it adapts, and never a capability.

## Decision

1. **The phone keeps three kinds of thing, and nothing else.**
   - **Readings**, the newest per stack of each kind: health (the summary, the
     problems and what stopped in the queue), what runs (services and forms),
     updates (the version running, the offer, the history and what became of the
     last update) and household (members and their requests).
   - **Preferences**: the lock period, how long readings are kept, the order of the
     stacks, where the operator was (stack and tab), and per stack which kinds of
     notification and which kinds of *new* the operator wants.
   - **Markers**: per stack and kind, an identifier of the newest item the operator
     has seen, so that *new since you looked* can be worked out. A marker is an
     identifier, never a second copy of the content.

   It never keeps a credential, a session token or pairing material (`N1-R23`), an
   action the stack did not receive (`N1-R41`), the confirmation of an action
   (`N1-R24`), an agreement (`N13-R7`) or a repair offer, which is something one
   agrees to and so must always be fresh.

2. **Each owner decides, and a small adapter of its own stores.** The capability a
   thing belongs to decides what is kept, when it is pruned and what counts as new:
   `health` its readings and the problem markers, `updates` its readings and the
   release markers, `household` its readings and the request markers, `stacks` what
   runs, where the operator was, the order of the stacks and how long readings are
   kept, `connection` the lock period and `device` the notification kinds. Each asks a
   kernel port of its own, and an adapter module of its own implements it —
   `health-kept`, `updates-kept`, `household-kept`, `stacks-kept`, `connection-kept`,
   `device-kept` — adapting Laravel's database and nothing else. That adapter owns its
   tables, named with its owner's prefix (`health_readings`), and its migrations in its
   own `database/migrations`. No adapter reads another's tables; one owner that needs
   another's data asks that owner's capability. Capabilities stay free of the
   framework, and no module grows with every feature.

3. **Queries are intents, written once.** A store port speaks the app's language —
   `keep`, `newest`, `forget` — and never a row or a column. Behind it, in the owner's
   adapter, one class holds one private, named method per query over Laravel's query
   builder with an injected connection, and turns rows into values in one place. There
   is no Eloquent model, no facade and no hand-written SQL. Every store port is proven
   twice: one contract suite runs against its fake and against its SQLite adapter.

4. **Every payload is sealed with a key the platform holds.** On first use the app
   generates a 32-byte data key and keeps it in the platform's secure storage at the
   narrowest accessibility, readable only while the device is unlocked, as a session
   is. Payloads are encrypted with Laravel's `Encrypter`, AES-256-GCM, constructed with
   that key — never with `APP_KEY` or the `Crypt` facade. What a query needs stays
   readable: the kind, when it was read and the version of its shape. The stack is
   stored as a keyed hash rather than its identity, so a row on disk cannot be tied to
   a stack without the key. One kernel port, `Sealed`, does the sealing, and the
   `vault` module implements it. **The owning capability seals before it asks its
   store**: a store port accepts a sealed payload and a stack's keyed hash, never a
   plain value, so a store adapter never sees what it keeps.

5. **Every row carries the version of its shape** (`N1-R32`). A reading of a shape this
   build does not know is discarded, because it can always be read again; a
   preference is the operator's own choice, so every change to a preference's shape
   ships with a migration and its test (`N1-R33`). Nothing here touches a pairing or
   its fingerprint (`N1-R34`).

6. **A kept reading is shown for what it is.** It is drawn on opening with when it was
   read (`N1-R9`, `N1-R24`) and replaced when a fresh one arrives. Until then, what acts
   on the stack is shown but cannot be used, with the reading's age beside it — offered,
   not hidden (`N1-R3`). Readings older than the operator's setting — any whole number
   of days from 1 to 365, or *until the stack is forgotten*, 30 by default — are
   deleted at launch and whenever the setting changes.

7. **Without the key, nothing is kept.** Where the device has no secure storage the
   app keeps nothing between launches and says why on its settings screen, as it does
   for a session (`N4-R6`). Where the key cannot be read — a restore onto another
   device, a reset keychain — the unreadable data is deleted, a new key is made, the
   pairings stay (`N1-R34`) and the app says once that its saved data was cleared.

8. **What is new is collected, not duplicated.** A kernel interface, `SaysWhatIsNew`,
   is implemented by each module that keeps markers, and the *What's new* screen asks
   every one of them. A module with a markers table and no implementation is a failing
   test, not a list somebody has to remember.

9. **The rules above are tests.** They join the companion's architecture document,
   each beside the test that enforces it:
   - a table belongs to one adapter: it carries its owner's prefix, is created in that
     adapter's migrations and is named in no other module's code;
   - database code lives only in a store adapter's query class and its migrations: no
     Eloquent anywhere, no raw SQL, no database facade, and `Illuminate\Database`
     nowhere outside adapters (the companion's A1 and A7, unchanged);
   - sealing goes through one port: the `Crypt` facade and the `Encrypter` class
     appear only in `vault`'s implementation of `Sealed`; no store port takes a type
     but a sealed payload, a stack's keyed hash and the bookkeeping beside them; and a
     test writes a value and reads the raw database file to find no trace of it;
   - no store method takes a session, a credential or pairing material, and no kept
     value holds one (`N1-R23`);
   - every kept value declares the version of its shape, and every shape ever written
     has a test that migrates or discards it (`N1-R32`, `N1-R33`).

## Alternatives considered

| Option | Why it lost |
|--------|-------------|
| **One store: a kernel port and one implementation in `vault`** | The first design. Every module that keeps something would add its tables, queries and migrations to `vault`, which would grow with every feature and become the place every change has to go through. An adapter per owner keeps each small and keeps the boundary rules meaningful. |
| **The store inside each capability** | Keeps each owner's queries beside its decisions, and puts Laravel's database into modules the architecture keeps framework-free (A1, A7): a capability that can reach a database is one that can be run wrong. |
| **Each store adapter seals** | Every adapter would receive plain values and have to remember to seal them. Sealing in the capability makes a plain value unrepresentable at a store port. |
| **Laravel's `Crypt` with the framework's `APP_KEY`** | The key is a plain file in the same private storage as the database, so anything that can read one can read the other. It stops only somebody opening the file by hand. |
| **Keep only what names nobody, in a plain file excluded from backups** | Would leave out the household's readings, and relies on the device's sandbox alone: a rooted device reads it. |
| **An encrypted database file (SQLCipher)** | Not something NativePHP's SQLite offers; it would mean patching the packager's native build on both platforms for what per-value encryption already gives. |
| **Eloquent models with encrypted casts** | The encrypted cast is bound to the application's encrypter unless overridden, models would cross into screens, and a model is a second place a row's meaning is decided. |
| **One key per stack** | Forgetting a stack could destroy its key and make its rows unreadable at once. It adds a key to manage per stack for what deleting the rows in the same act already achieves. |

## Consequences

**The app's database gains tables, one module's worth at a time.** Each module's
migrations run at launch, as the queue's already do. A module that keeps nothing has
no migrations and no store.

**Opening the app shows the last thing it knew.** The first frame is the kept reading
with its age, and actions wait for a fresh one. A stack out of reach shows what it last
said and when, beside the reason it cannot be reached now.

**A backup of the device carries only sealed data.** The data key stays in secure
storage, which a backup does not restore to another device; such a restore is the
*key cannot be read* case, and the app starts its saved data again.

**Settings the operator changes now persist**, which is what makes the lock period of
`N4-R19` buildable.

**A kept reading is not a live one.** Every surface that draws one has to say when it
was read and hold back its actions, and the tests of `N1-R9` and `N27` hold every
screen to that.

## Related

- [N27](../../10-functional/features/n-companion/n27-what-the-phone-keeps.md) — what the phone keeps, as requirements
- [N1](../../10-functional/features/n-companion/n1-companion-app.md) — `N1-R9`, `N1-R23` to `N1-R25`, `N1-R28`, `N1-R32` to `N1-R34`, `N1-R41`
- [N4](../../10-functional/features/n-companion/n4-native-integration.md) — `N4-R5`, `N4-R6`, `N4-R19`: secure storage and the lock period
- [ADR-0019](0019-a-screen-paints-before-it-reaches-the-stack.md) — a screen paints what it knows first
- [ADR-0020](0020-an-action-the-stack-did-not-receive-did-not-happen.md) — why an undelivered action is never kept
- [`30-repos/lemonfiber-companion.md`](../../30-repos/lemonfiber-companion.md) — the modules and their kinds
