# ADR-0047: A phone hears its stacks without a vendor's push service, in the kinds the core declares

**Status:** Accepted
**Date:** 2026-10-12
**Decided:** 2026-10-12, by the maintainer, Wessel Verheij: the companion uses no Apple or Google push service; it raises local notifications from its own pinned connection while it runs or when the platform's background refresh wakes it, and on Android it is also woken through UnifiedPush where a distributor is installed; delivery while closed is best-effort on iOS and is said to be; the core publishes a closed list of the notification kinds it raises, `problem`, `completion`, `update`, `backup`, `request` and `member`, every alert names one, and the app offers exactly those; a new request and an answered invitation reach the operator's phone and never a household member, amending `B5-R1`.

## Context

`N27-R17` has each stack's settings offer, for each kind of notification the stack raises,
whether it may reach the phone, and `N4-R11` has every notification originate in the core.
Neither says how a notification reaches a phone that is not on screen, nor what a kind is.
The core raises alerts on its event stream as they start and resolve (`ARCH-R162`), each with
an event kind such as `vpn.leak`: an open set, grown by every new check, which no switch on a
phone can be built over.

The ordinary answer is a vendor push service: Apple's on iOS, Google's on Android. Both see
every message, both tie the app to an account with a large company, and Google's needs Play
Services on the phone. lemonfiber's first principles are privacy and not being tied to big
companies, and a stack is a machine in somebody's house that has no business telling Apple or
Google when its VPN dropped.

## Decision

**Notifications are raised on the phone, from the phone's own connection.** The app holds
each stack's event stream while it runs, and reads it again when the platform wakes it for
background refresh: `BGAppRefreshTask` on iOS, a periodic worker on Android. What it hears is
notified locally, filtered by the kinds the operator switched on for that stack. Nothing about
a notification leaves the stack except over the pinned connection the app already trusts
(ADR-0025).

**A stream resumed from an event id replays the alerts it missed.** A phone woken an hour
later has to hear the alert raised while it slept, so a stream opened with `Last-Event-ID`
replays the `alert` events raised after it, within a retention the contract states. A client
connecting without one is still sent none, as `ARCH-R162` says.

**On Android, UnifiedPush wakes the app where a distributor is installed.** UnifiedPush is an
open protocol with self-hostable distributors, ntfy among them. The app registers the endpoint
its distributor gives it with the stack, and the core sends that endpoint a WebPush message,
encrypted to the app (RFC 8291), that says only that the stack has something to say. The app
then reads the stream over its own connection. The distributor learns when a stack spoke and
nothing of what it said.

**iOS delivery while backgrounded is best-effort, and the app says so.** Without Apple's push
service, iOS wakes an app for background refresh when it chooses, which may be rarely or not
at all. The app does not pretend otherwise: where the operator turns notifications on, it says
that a closed app on iOS hears its stacks when the system lets it, and that Android without a
distributor is the same.

**The core declares the kinds, in a closed list.** The contract names every notification kind
the core raises, and every alert names exactly one beside its event kind. A new kind is a
contract change, so an app built today offers every kind a stack of the same contract can
raise, and a stack says which of them it raises. The list follows what the core raises
([B5](../../10-functional/features/b-running/b5-notifications.md)):

| Kind | What it covers |
|---|---|
| `problem` | Every critical or warning condition, at onset and at resolution |
| `completion` | Work the operator asked for finishing: a download completed, an import succeeded |
| `update` | An update to the stack or to lemonfiber available |
| `backup` | A backup that succeeded; one that failed is a `problem` |
| `request` | A request from somebody in the house, waiting on the operator |
| `member` | An invitation answered: accepted, declined, or lapsed |

**Requests and members reach the operator, never a member.** The request service tells a
requester about their own request, and the invitee knows what they answered, so lemonfiber
still sends neither of them anything (`B5-R1`). What it adds is the operator's side: somebody is
waiting on a decision, or answered the invitation the operator sent. `B5-R1` is amended to say
so, and the core's rule that refused every event in a request's or a household member's domain
narrows to refusing one addressed to a member.

## Consequences

- The core gains the kind list, its refusal of request and household events narrowed to the
  ones addressed to a member, a `kinds` field on the alerts read, replay of `alert` events
  on a resumed stream, and registered push endpoints with the WebPush wake
  ([web API](../../20-architecture/contracts/web-api.md)).
- The app gains local notifications, background refresh on both platforms and a UnifiedPush
  client on Android; it never links a vendor push SDK.
- An operator on iOS who needs every alert at once is told to use a channel the core already
  delivers to, such as ntfy (`B5`), rather than being promised what the phone cannot do.

## Related

- [N4](../../10-functional/features/n-companion/n4-native-integration.md) — notifications on the phone
- [N27](../../10-functional/features/n-companion/n27-what-the-phone-keeps.md) — which kinds reach the phone
- [B5](../../10-functional/features/b-running/b5-notifications.md) — what the core raises
- [ADR-0025](0025-nothing-leaves-this-machine-unpinned.md) — the pinned connection
