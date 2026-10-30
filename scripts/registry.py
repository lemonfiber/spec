#!/usr/bin/env python3
"""How spec's scripts ask a container registry what a tag names, and what it has.

Two questions, both anonymous and both read-only: which tags a repository publishes,
and which multi-architecture index a reference resolves to. Every upstream image a
plugin pins is public, so nothing here holds a credential of anybody's: the bearer a
registry hands out is its own anonymous pull token, asked for on the registry's own
challenge.

  The digest is computed, not taken. A registry names what it served in a header,
  and the header is the registry's claim; the SHA-256 of the bytes that arrived is
  the fact. Only the second is returned.

  A redirect off the host a request was sent to is refused rather than followed,
  because urllib copies request headers onto the redirected request and one of them
  is that pull token.

  A reply is bounded before it is read, and nothing arriving from a registry is
  printed before `printable` has made it one line of plain characters.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from patterns import DIGEST, IMAGE_TAG

SCHEME = "https"
TIMEOUT_S = 20
#: A tag listing for a busy repository runs to hundreds of kilobytes a page; an index
#: is a few kilobytes. One bound covers both with room.
MAX_REPLY = 4 * 1024 * 1024
#: The pages of a tag listing followed before this gives up, which at a thousand tags
#: a page is far more tags than any upstream image publishes.
MAX_PAGES = 50
#: How much of anything a registry said is printed.
SAID = 120

DOCKER_HUB = "registry-1.docker.io"
INDEX_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
)
IMAGE_TYPES = (
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)
ACCEPT = ", ".join(INDEX_TYPES + IMAGE_TYPES)
USER_AGENT = "lemonfiber-spec"

#: A repository path as a registry spells one, and a host.
REPOSITORY = re.compile(r"\A[a-z0-9]+(?:[._/-][a-z0-9]+)*\Z")
HOST = re.compile(r"\A[a-z0-9.-]+(?::\d+)?\Z", re.ASCII)
UNPRINTABLE = re.compile(r"[^A-Za-z0-9 .,;:/+_()-]")


def printable(text: object) -> str:
    """One line of a network reply, fit to print into a workflow log."""
    return UNPRINTABLE.sub("?", str(text).strip().replace("\n", " "))[:SAID]


def address(image: str) -> tuple[str, str] | None:
    """The registry host and repository an image name refers to, or None.

    Docker's own reading: a first segment with a dot or a colon in it, or
    `localhost`, is a host, and anything else is on Docker Hub, where a
    single-segment name is an official image under `library/`. `docker.io` is Docker
    Hub's name, not the host its registry answers on.
    """
    first, _, rest = image.partition("/")
    if rest and ("." in first or ":" in first or first == "localhost"):
        host, repository = first.lower(), rest
    else:
        host, repository = DOCKER_HUB, image if rest else f"library/{image}"
    if host in ("docker.io", "index.docker.io"):
        host = DOCKER_HUB
        repository = repository if "/" in repository else f"library/{repository}"
    if not HOST.match(host) or not REPOSITORY.match(repository):
        return None
    return host, repository


def digest_of(body: bytes) -> str:
    """The content digest of a manifest, as a registry addresses it."""
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def platforms_of(document: dict) -> set[tuple[str, str]]:
    """The runnable platforms an index lists, leaving out attestations."""
    found = set()
    for entry in document.get("manifests", []):
        platform = entry.get("platform", {})
        if platform.get("os") == "unknown" or platform.get("architecture") == "unknown":
            continue
        found.add((str(platform.get("os")), str(platform.get("architecture"))))
    return found


def is_index(document: dict, media_type: str) -> bool:
    """Whether a manifest is an index of images rather than one image."""
    declared = document.get("mediaType") or media_type
    return declared in INDEX_TYPES or ("manifests" in document and "config" not in document)


class SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to the host the request went to, over https."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        here, there = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if there.scheme != SCHEME or there.netloc.lower() != here.netloc.lower():
            raise urllib.error.HTTPError(
                req.full_url, code, "redirected off the registry; not followed", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, headers: dict[str, str]) -> tuple[bytes, dict[str, str]]:
    """One bounded GET, and the reply's headers by lower-cased name."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    with urllib.request.build_opener(SameHostRedirects).open(request, timeout=TIMEOUT_S) as reply:
        body = reply.read(MAX_REPLY + 1)
        if len(body) > MAX_REPLY:
            raise ValueError(f"the registry answered with more than {MAX_REPLY // 1024} KiB")
        return body, {key.lower(): value for key, value in reply.headers.items()}


def challenge_fields(challenge: str) -> dict[str, str]:
    """The `key="value"` pairs of a `WWW-Authenticate` challenge, after its scheme."""
    fields = {}
    for part in challenge.partition(" ")[2].split(","):
        key, _, value = part.strip().partition("=")
        if key and len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            fields[key] = value[1:-1]
    return fields


def next_page(link: str) -> str:
    """The target of a `Link` header's `rel="next"`, or empty where it has none."""
    for part in link.split(","):
        target, _, parameters = part.partition(";")
        target = target.strip()
        relation = parameters.replace('"', "").replace(" ", "")
        if relation == "rel=next" and target.startswith("<") and target.endswith(">"):
            return target[1:-1]
    return ""


def anonymous_token(challenge: str) -> str:
    """The pull token a registry's `WWW-Authenticate: Bearer` challenge offers."""
    if not challenge.lower().startswith("bearer "):
        raise ValueError("the registry asked for credentials this does not hold")
    fields = challenge_fields(challenge)
    realm = urllib.parse.urlsplit(fields.get("realm", ""))
    if realm.scheme != SCHEME or not realm.netloc:
        raise ValueError("the registry's token service is not an https address")
    query = urllib.parse.urlencode({k: v for k, v in fields.items() if k in ("service", "scope")})
    body, _ = fetch(urllib.parse.urlunsplit((SCHEME, realm.netloc, realm.path, query, "")), {})
    document = json.loads(body)
    token = document.get("token") or document.get("access_token")
    if not token:
        raise ValueError("the registry's token service answered without a token")
    return str(token)


def get(host: str, path: str, accept: str = "") -> tuple[bytes, dict[str, str]]:
    """One GET against a registry, answering its anonymous challenge if it makes one."""
    url = f"{SCHEME}://{host}{path}"
    headers = {"Accept": accept} if accept else {}
    try:
        return fetch(url, headers)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
        challenge = error.headers.get("WWW-Authenticate", "")
    return fetch(url, {**headers, "Authorization": f"Bearer {anonymous_token(challenge)}"})


def problem(error: Exception) -> str:
    """Why a registry gave no answer: its status, no connection, or a reply that is not JSON."""
    if isinstance(error, urllib.error.HTTPError):
        return f"registry answered {error.code} {printable(error.reason)}"
    if isinstance(error, urllib.error.URLError):
        return f"registry unreachable {printable(error.reason)}"
    if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
        return "registry answered with something that is not JSON"
    return printable(error)


def tags(image: str) -> tuple[list[str], str]:
    """Every tag a repository publishes, or why they could not be listed."""
    where = address(image)
    if where is None:
        return [], f"{printable(image)} is not an image name this will address"
    host, repository = where
    path = f"/v2/{repository}/tags/list?n=1000"
    found: list[str] = []
    try:
        for _ in range(MAX_PAGES):
            body, headers = get(host, path)
            found.extend(str(tag) for tag in json.loads(body).get("tags") or [])
            following = next_page(headers.get("link", ""))
            if not following:
                return found, ""
            nxt = urllib.parse.urlsplit(following)
            if nxt.netloc and nxt.netloc.lower() != host:
                return found, "the registry paged its tag list onto another host; not followed"
            path = urllib.parse.urlunsplit(("", "", nxt.path, nxt.query, ""))
        return found, f"the tag list ran past {MAX_PAGES} pages"
    except (urllib.error.URLError, ValueError) as error:
        return [], problem(error)


def resolve(image: str, reference: str) -> tuple[str, set[tuple[str, str]], str]:
    """The index a tag or digest resolves to: its digest, its platforms, or why not.

    A reference that resolves to a single image rather than an index answers with the
    reason and no digest, because pinning one platform's image is what `E1-R1`
    forbids.
    """
    where = address(image)
    if where is None:
        return "", set(), f"{printable(image)} is not an image name this will address"
    if not (IMAGE_TAG.match(reference) or DIGEST.match(reference)):
        return "", set(), f"{printable(reference)} is neither a tag nor a sha256 digest"
    host, repository = where
    try:
        body, headers = get(host, f"/v2/{repository}/manifests/{reference}", ACCEPT)
        document = json.loads(body)
    except (urllib.error.URLError, ValueError) as error:
        return "", set(), problem(error)
    digest = digest_of(body)
    if DIGEST.match(reference) and digest != reference:
        return "", set(), f"asked for {reference} and was served content whose digest is {digest}"
    if not is_index(document, headers.get("content-type", "")):
        return "", set(), "resolves to a single-platform image, not a multi-architecture index"
    return digest, platforms_of(document), ""
