# Repo: `integration-mcp`

**Status:** Accepted

lemonfiber for AI assistants: a Model Context Protocol server over the web API, for an
operator and for household members. Python, Hippocratic 3.0.

**Implements:** [F13 An assistant's way in](../10-functional/features/f-extensibility/f13-mcp.md).

---

## What this repo is

An MCP server that reaches a stack only through [`sdk-python`](sdk-python.md), and only
with an integration key ([C10](../10-functional/features/c-trust/c10-integration-keys.md)).
It runs over stdio on a person's own machine, started straight from this repository with
`uv`, or over Streamable HTTP beside the stack, from an image its release builds.

## What is generated and what is written

| | |
|---|---|
| **Generated** from `web-api.contract.json`, never edited by hand | A tool and a resource for every served read, a tool for every key-callable action, a rehearsal tool beside each action that can be rehearsed, and each write tool's annotations |
| **Written** | Each tool's description, in plain language and, for a member key, in the household's words; the two transports; configuration |

A generator run that changes anything committed fails CI, and a test fails when a read or a
key-callable action has no tool or a tool has no description (`F13-R2`).

## What it must not own

- **The wire.** Shapes, the stream and the pin are `sdk-python`'s.
- **Policy.** What a key may do is the core's published list. The server never forwards a
  call the contract does not name.
- **A credential of its own.** In HTTP mode each request's key is the one used for the
  stack (`F13-R8`). The operator password is never asked for.

## Quality bar

The organisation's standard, as for [`sdk-python`](sdk-python.md):

- `pyright` strict, and `ruff` with the formatter enforced.
- `pytest` at 100% line and branch coverage.
- Mutation testing with a minimum score in CI.
- A conformance suite run against the MCP specification's own schema for every tool.
- The organisation's shared workflows.

## Versioning and the client

`sdk-python` is vendored at a pinned commit by a script, with a drift check that fails when
the pin is behind the contract, as in
[`integration-home-assistant`](integration-home-assistant.md).

## Publishing

Not published to a package registry. The stdio server runs from this repository by `uv`, and
the HTTP server's multi-arch image is built, signed and attested by this repository's
release, which rides the version train.

## Related

- [F13 An assistant's way in](../10-functional/features/f-extensibility/f13-mcp.md) · [C10 Integration keys](../10-functional/features/c-trust/c10-integration-keys.md)
- [`sdk-python`](sdk-python.md) · [`integration-home-assistant`](integration-home-assistant.md)
