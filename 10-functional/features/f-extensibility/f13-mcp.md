---
id: F13
title: An assistant's way in
kind: feature
area: F
audience: operator
status: accepted
maturity: building
labels: [extensibility, household, web]
relates: [C10, F12, G2, D11]
---

# F13 — An assistant's way in

**Status:** Accepted · **Audience:** Operator, household member · **Area:** F — Extensibility

---

## Purpose

Let a person ask an AI assistant about the stack, and have it do what they could do
themselves, through the Model Context Protocol. An operator asks why a download is stuck or
has the doctor run. A member asks what they have asked for and what they are watching, and,
once the core serves it ([D11](../d-content/d11-watching-what-the-house-holds.md)), finds a title,
asks for it and plays it.

The server lives in [`integration-mcp`](../../../30-repos/integration-mcp.md) and speaks to
the stack only through [`sdk-python`](../../../30-repos/sdk-python.md), with an integration
key ([C10](../c-trust/c10-integration-keys.md)). What the assistant may see and do is
exactly what the key's scope admits.

## Behaviour

### Its tools are the web API, generated

Every read the web API serves is a tool and a resource, and every action a key may call is a
tool. They are generated from the contract the core publishes, so the server offers nothing
the web API does not, and a read or action the contract gains appears as a tool when the
server is regenerated. Only each tool's description is written, in plain language. A member
key's tools are described in the household's words ([G2](../g-ux/g2-plain-language.md)).

### A write is rehearsed, and the yes is the offer

An action that can be rehearsed is two tools. The rehearsal writes nothing and answers with
an offer. The action takes that offer as its yes, so a state that moved in between is refused
by name, as it is for every other client
([ADR-0031](../../../00-overview/decisions/0031-a-plugin-and-a-choice-are-web-writes-a-credential-is-not.md)).
Every write tool carries the protocol's annotations saying whether it is destructive and
whether repeating it is safe, so the assistant's client can ask the person first.

### It runs where the person is, or beside the stack

On a person's own machine it speaks over stdio, run straight from this organisation's
repository. Beside the stack it speaks Streamable HTTP, from an image its release builds, so
an assistant on a phone or in a browser can reach it. Either way it is configured with the
stack's address, a key and the certificate pin, like Home Assistant
([F12](f12-home-assistant.md)).

Beside the stack, the certificate it serves comes one of four ways
([the certificates contract](../../../20-architecture/contracts/certificates.md)): the
operator's own files, ACME from any authority (a public one, or one the operator runs), a root
lemonfiber makes and the operator installs, or a certificate of its own whose fingerprint a
client pins. The last is what it serves unless told otherwise, and two of the four depend on no
company outside the house. Only a publicly trusted certificate reaches an assistant whose
provider makes the connection, so the server says, at start and in its documentation, who can
check the certificate it serves.

### What the stack says is data

A tool's result carries text other people wrote: a release's name in a log line, a title in a
request. The assistant reads it, so it is handed over as the stack's answer, delimited from
anything the server says itself, and never folded into the server's own sentences.

### A member's data goes where the member sends it

An assistant sends what it reads to whichever model provider its client uses. So no member
can connect one until the operator allows members to mint their own keys (`C10-R15`). The
documentation says plainly that turning the setting on lets a member's requests and viewing
reach a provider of their choosing.

## States

| State | Meaning |
|---|---|
| `connected` | Tools answer from the stack |
| `refused` | The key was refused; every tool says so and that a new key is needed |
| `unreachable` | The stack did not answer, or the pin did not match |

## Edge cases

| Situation | Behaviour |
|---|---|
| The assistant calls an action without rehearsing | Refused by the server before the stack is asked, since the action tool takes only an offer; the tool says to rehearse first. A call the core receives with no offer acts as it would without one (`ARCH-R164`), so the refusal is the server's. |
| The offer is stale by the time the action runs | Refused naming what moved; the assistant can rehearse again. |
| A member key calls a technical read | Not offered: a member key's tool list has no technical tool. |
| The contract gains a read the server was not regenerated for | Not offered until regeneration; the server never forwards an unknown call. |
| The HTTP mode is exposed beyond the machine it runs on | It serves only over TLS and requires the person's key on every request; it holds no credential of its own. |

## Acceptance criteria

| ID | Requirement |
|----|-------------|
| **F13-R1** | The server MUST reach a stack only through `sdk-python` and only with an integration key, and MUST NOT ask for, accept or store the operator password. |
| **F13-R2** | Its tools and resources MUST be generated from the core's published contract: a tool and a resource for every served read and a tool for every action a key may call. A test MUST fail when a read or a key-callable action has no tool, or a tool has no description. |
| **F13-R3** | It MUST offer only the tools its key's scope admits. A member key MUST yield no technical tool, and its tools' descriptions MUST be in the household's words. |
| **F13-R4** | An action that can be rehearsed MUST be offered as a rehearsal tool, which writes nothing and returns an offer, and an action tool that takes only that offer as its yes. |
| **F13-R5** | Every write tool MUST carry the protocol's annotations stating whether it is destructive and whether it is idempotent. |
| **F13-R6** | The server MUST speak stdio, runnable from this organisation's repository without a package registry, and Streamable HTTP, from a multi-arch image its release builds. |
| **F13-R7** | In either mode it MUST be configured with the stack's address, a key and the certificate pin, and MUST refuse to start without a pin for a non-loopback address. |
| **F13-R8** | In HTTP mode it MUST serve only over TLS, MUST require a key on every request and use that request's key for the stack, and MUST NOT hold a credential of its own. |
| **F13-R9** | A refused key MUST be reported by every tool as refused, saying a new key is needed, and MUST NOT be retried. |
| **F13-R10** | It MUST NOT log, return or include in an error any key, pin or credential. |
| **F13-R11** | Its documentation MUST state that an assistant sends what it reads to its client's model provider, and that allowing members to mint keys lets a member's requests and viewing reach a provider of their choosing. |
| **F13-R12** | In HTTP mode it MUST come by its certificate as [the certificates contract](../../../20-architecture/contracts/certificates.md) sets out, offering its four modes and serving `pinned` where none is chosen. |
| **F13-R13** | Its start-up log and its documentation MUST say, for the mode it serves, who can check its certificate, and MUST say that an assistant whose provider makes the connection can reach it only with a publicly trusted certificate. |
| **F13-R14** | Every tool result MUST carry what the stack answered as data, delimited from the server's own words, and MUST NOT place text the stack answered with outside that delimitation. |

## Related

- [C10 Integration keys](../c-trust/c10-integration-keys.md) — what it holds, and the setting that lets members in
- [F12 Home Assistant](f12-home-assistant.md) — the other program built the same way
- [D11 Watching what the house holds](../d-content/d11-watching-what-the-house-holds.md) — the member reads it grows with
- [`integration-mcp`](../../../30-repos/integration-mcp.md) · [`sdk-python`](../../../30-repos/sdk-python.md)
