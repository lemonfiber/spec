#!/usr/bin/env python3
"""`registry.py`: where an image lives, what its registry publishes and what a tag names,
asked anonymously, bounded, and never followed off the registry.

Stdlib unittest, no dependencies. No registry is asked: every reply is a document here.
Run:  python3 scripts/test_registry.py
"""

from __future__ import annotations

import email.message
import json
import pathlib
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import registry

INDEX = {
    "mediaType": registry.INDEX_TYPES[0],
    "manifests": [
        {"platform": {"os": "linux", "architecture": "amd64"}},
        {"platform": {"os": "linux", "architecture": "arm64"}},
        {"platform": {"os": "unknown", "architecture": "unknown"}},
    ],
}
CHALLENGE = 'Bearer realm="https://ghcr.io/token",service="ghcr.io",scope="repository:a/b:pull"'


def http_error(code: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    held = email.message.Message()
    for key, value in (headers or {}).items():
        held[key] = value
    return urllib.error.HTTPError("https://x.test/", code, "Nope\nsecond line", held, None)


class Reading(unittest.TestCase):
    """What is read out of a name, a document and a header, without asking anybody."""

    def test_an_image_name_is_addressed_as_docker_reads_it(self):
        for image, wanted in (
            ("caddy", (registry.DOCKER_HUB, "library/caddy")),
            ("jellyfin/jellyfin", (registry.DOCKER_HUB, "jellyfin/jellyfin")),
            ("docker.io/jellyfin/jellyfin", (registry.DOCKER_HUB, "jellyfin/jellyfin")),
            ("docker.io/caddy", (registry.DOCKER_HUB, "library/caddy")),
            ("lscr.io/linuxserver/sonarr", ("lscr.io", "linuxserver/sonarr")),
            ("ghcr.io/hotio/unpackerr", ("ghcr.io", "hotio/unpackerr")),
            ("localhost:5000/x", ("localhost:5000", "x")),
            ("ghcr.io/../../evil", None),
            ("Caddy", None),
            ("ghcr.io/a?b", None),
        ):
            with self.subTest(image=image):
                self.assertEqual(registry.address(image), wanted)

    def test_the_digest_is_sha256_of_the_bytes(self):
        self.assertEqual(
            registry.digest_of(b""), "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_an_index_is_told_apart_from_one_image_and_attestations_are_left_out(self):
        self.assertEqual(registry.platforms_of(INDEX), {("linux", "amd64"), ("linux", "arm64")})
        self.assertTrue(registry.is_index(INDEX, ""))
        self.assertTrue(registry.is_index({"manifests": []}, registry.INDEX_TYPES[1]))
        self.assertFalse(
            registry.is_index({"mediaType": registry.IMAGE_TYPES[0], "config": {}, "layers": []}, "")
        )

    def test_a_challenge_and_a_link_are_read(self):
        self.assertEqual(
            registry.challenge_fields(CHALLENGE),
            {"realm": "https://ghcr.io/token", "service": "ghcr.io", "scope": "repository:a/b:pull"},
        )
        self.assertEqual(registry.challenge_fields('Bearer a=b,c="'), {})
        for link, wanted in (
            (
                '</v2/library/caddy/tags/list?last=2.8&n=1000>; rel="next"',
                "/v2/library/caddy/tags/list?last=2.8&n=1000",
            ),
            ("</v2/x/tags/list?last=1>; rel=next", "/v2/x/tags/list?last=1"),
            ('</v2/x/tags/list?last=1>; rel="prev"', ""),
            ("", ""),
        ):
            with self.subTest(link=link):
                self.assertEqual(registry.next_page(link), wanted)

    def test_what_a_registry_said_is_printed_as_one_plain_line(self):
        self.assertEqual(registry.printable(" a\nb\x1b[31m "), "a b??31m")
        self.assertEqual(len(registry.printable("x" * 500)), registry.SAID)

    def test_why_there_was_no_answer_is_said(self):
        self.assertEqual(registry.problem(http_error(404)), "registry answered 404 Nope second line")
        self.assertEqual(registry.problem(urllib.error.URLError("refused")), "registry unreachable refused")
        self.assertEqual(
            registry.problem(json.JSONDecodeError("x", "", 0)),
            "registry answered with something that is not JSON",
        )
        self.assertEqual(registry.problem(ValueError("too big")), "too big")


class Reply:
    """A reply as urllib's opener hands one back."""

    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        self.body, self.headers = body, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


class Opener:
    """Answers each URL from a table, records every request, and raises where told to."""

    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def open(self, request, timeout):
        self.asked.append(request)
        answer = self.answers[request.full_url]
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, Exception):
            raise answer
        return answer


class Asking(unittest.TestCase):
    """The two questions, against registries that answer as documents here."""

    def opened(self, answers) -> Opener:
        opener = Opener(answers)
        patched = mock.patch.object(urllib.request, "build_opener", return_value=opener)
        patched.start()
        self.addCleanup(patched.stop)
        return opener

    def test_a_reply_past_the_bound_is_refused(self):
        self.opened({"https://h.test/x": Reply(b"x" * (registry.MAX_REPLY + 1))})
        with self.assertRaisesRegex(ValueError, "more than"):
            registry.fetch("https://h.test/x", {})

    def test_tags_are_listed_across_pages_with_the_anonymous_token(self):
        base = "https://ghcr.io/v2/hotio/unpackerr/tags/list"

        def first(request):
            if request.get_header("Authorization") != "Bearer t0k":
                return http_error(401, {"WWW-Authenticate": CHALLENGE})
            return Reply(
                json.dumps({"tags": ["1.0"]}).encode(),
                {"Link": '</v2/hotio/unpackerr/tags/list?last=1.0>; rel="next"'},
            )

        opener = self.opened(
            {
                f"{base}?n=1000": first,
                "https://ghcr.io/token?service=ghcr.io&scope=repository%3Aa%2Fb%3Apull": Reply(
                    b'{"token": "t0k"}'
                ),
                f"{base}?last=1.0": http_error(401, {"WWW-Authenticate": CHALLENGE}),
            }
        )
        opener.answers[f"{base}?last=1.0"] = lambda request: (
            Reply(json.dumps({"tags": ["1.1"]}).encode())
            if request.get_header("Authorization")
            else http_error(401, {"WWW-Authenticate": CHALLENGE})
        )
        self.assertEqual(registry.tags("ghcr.io/hotio/unpackerr"), (["1.0", "1.1"], ""))
        self.assertEqual(opener.asked[0].get_header("User-agent"), registry.USER_AGENT)

    def test_a_tag_list_paged_onto_another_host_or_without_end_is_not_followed(self):
        base = "https://ghcr.io/v2/a/b/tags/list?n=1000"
        self.opened(
            {base: Reply(b'{"tags": ["1"]}', {"Link": '<https://evil.test/v2/a/b/tags/list>; rel="next"'})}
        )
        self.assertEqual(
            registry.tags("ghcr.io/a/b"),
            (["1"], "the registry paged its tag list onto another host; not followed"),
        )
        self.opened(
            {
                base: Reply(
                    b'{"tags": null}', {"Link": f'<{base.removeprefix("https://ghcr.io")}>; rel="next"'}
                )
            }
        )
        self.assertEqual(
            registry.tags("ghcr.io/a/b"), ([], f"the tag list ran past {registry.MAX_PAGES} pages")
        )

    def test_tags_that_could_not_be_listed_say_why(self):
        self.assertEqual(registry.tags("Nope"), ([], "Nope is not an image name this will address"))
        self.opened({"https://ghcr.io/v2/a/b/tags/list?n=1000": http_error(500)})
        self.assertEqual(registry.tags("ghcr.io/a/b"), ([], "registry answered 500 Nope second line"))

    def test_a_challenge_this_will_not_answer_is_refused(self):
        for challenge, why in (
            ('Basic realm="https://x.test"', "credentials"),
            ('Bearer realm="http://x.test/token",service="x"', "not an https address"),
        ):
            with self.subTest(challenge=challenge), self.assertRaisesRegex(ValueError, why):
                registry.anonymous_token(challenge)
        self.opened({"https://x.test/token?service=x": Reply(b"{}")})
        with self.assertRaisesRegex(ValueError, "without a token"):
            registry.anonymous_token('Bearer realm="https://x.test/token",service="x"')

    def test_a_tag_resolves_to_its_index_digest_and_platforms(self):
        body = json.dumps(INDEX).encode()
        self.opened({"https://lscr.io/v2/linuxserver/sonarr/manifests/4.0.21": Reply(body)})
        self.assertEqual(
            registry.resolve("lscr.io/linuxserver/sonarr", "4.0.21"),
            (registry.digest_of(body), {("linux", "amd64"), ("linux", "arm64")}, ""),
        )

    def test_a_reference_that_is_not_an_index_or_not_what_was_asked_is_refused(self):
        image = json.dumps({"mediaType": registry.IMAGE_TYPES[0], "config": {}}).encode()
        wrong = "sha256:" + "0" * 64
        self.opened(
            {
                "https://lscr.io/v2/a/b/manifests/1": Reply(image),
                f"https://lscr.io/v2/a/b/manifests/{wrong}": Reply(json.dumps(INDEX).encode()),
                "https://lscr.io/v2/a/b/manifests/2": Reply(b"not json"),
                "https://lscr.io/v2/a/b/manifests/3": http_error(403),
            }
        )
        self.assertIn("single-platform image", registry.resolve("lscr.io/a/b", "1")[2])
        self.assertIn("was served content whose digest is", registry.resolve("lscr.io/a/b", wrong)[2])
        self.assertEqual(
            registry.resolve("lscr.io/a/b", "2")[2], "registry answered with something that is not JSON"
        )
        self.assertEqual(registry.resolve("lscr.io/a/b", "3")[2], "registry answered 403 Nope second line")
        self.assertIn("not an image name", registry.resolve("Nope", "1")[2])
        self.assertIn("neither a tag nor", registry.resolve("lscr.io/a/b", "../x")[2])


class Redirects(unittest.TestCase):
    """A redirect is followed only to the same host over https, because the token rides along."""

    def redirected(self, to: str):
        request = urllib.request.Request("https://ghcr.io/v2/a/b/manifests/1")
        return registry.SameHostRedirects().redirect_request(request, None, 307, "", {}, to)

    def test_the_same_host_is_followed(self):
        self.assertEqual(
            self.redirected("https://ghcr.io/v2/a/b/blobs/x").full_url, "https://ghcr.io/v2/a/b/blobs/x"
        )

    def test_another_host_or_plain_http_is_not(self):
        for to in ("https://evil.test/x", "http://ghcr.io/x"):
            with self.subTest(to=to), self.assertRaises(urllib.error.HTTPError):
                self.redirected(to)


if __name__ == "__main__":
    unittest.main()
