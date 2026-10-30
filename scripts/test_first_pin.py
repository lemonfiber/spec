"""What a built part's Dockerfile stands in for, and that a revision still running what
its Dockerfile builds on ships nothing — ARCH-R285."""

from __future__ import annotations

import contextlib
import io
import pathlib
import shutil
import tempfile
import unittest

import first_pin

DIGEST = "sha256:" + "3a" * 32
OTHER = "sha256:" + "3b" * 32
DOCKERFILE = f"FROM caddy:2.11.6@{DIGEST}\nUSER 1000:1000\n"


def manifest(image: str, digest: str = DIGEST, **service: object) -> dict:
    return {
        "plugin": {"id": "door"},
        "service": [{"id": "door", "image": image, "digest": digest, **service}],
    }


class BuiltOn(unittest.TestCase):
    def test_the_last_from_is_read_with_its_flags_tag_and_stage_aside(self):
        for dockerfile, base in (
            (DOCKERFILE, ("caddy", DIGEST)),
            (f"from --platform=$BUILDPLATFORM caddy@{DIGEST} AS door\n", ("caddy", DIGEST)),
            (
                f"FROM rust@{OTHER} AS build\nFROM localhost:5000/x/y:1@{DIGEST}\n",
                ("localhost:5000/x/y", DIGEST),
            ),
            ("FROM caddy:2.11.6\n", ("caddy", None)),
            ("RUN true\n", None),
            ("FROM\n", None),
        ):
            with self.subTest(dockerfile=dockerfile):
                self.assertEqual(first_pin.built_on(dockerfile), base)


class Ships(unittest.TestCase):
    def test_a_part_still_running_what_its_dockerfile_builds_on_ships_nothing_at_any_digest(self):
        for digest in (DIGEST, OTHER):
            with self.subTest(digest=digest):
                why = first_pin.unshipped(manifest("caddy", digest), DOCKERFILE, "LemonFiber")
                self.assertIsNotNone(why)
                self.assertIn("ghcr.io/lemonfiber/door", why or "")

    def test_a_part_running_its_own_image_another_image_or_no_dockerfile_ships(self):
        for pinned, dockerfile in (
            (manifest("ghcr.io/lemonfiber/door"), DOCKERFILE),
            (manifest("ghcr.io/gethomepage/homepage"), f"FROM gcr.io/distroless/static@{DIGEST}\n"),
            (manifest("caddy"), None),
            ({"plugin": {"id": "door"}, "service": [{"id": "door-adapter", "image": "caddy"}]}, DOCKERFILE),
        ):
            with self.subTest(pinned=pinned, dockerfile=dockerfile):
                self.assertIsNone(first_pin.unshipped(pinned, dockerfile, "LemonFiber"))


class StandsIn(unittest.TestCase):
    def test_what_the_built_image_stands_in_for(self):
        fronting = {
            "plugin": {"id": "caddy"},
            "service": [
                {"id": "caddy", "image": "ghcr.io/lemonfiber/caddy"},
                {"id": "caddy-adapter", "image": "ghcr.io/lemonfiber/caddy-adapter", "fronts": "caddy"},
            ],
        }
        for pinned, dockerfile, said in (
            (fronting, "FROM scratch\n", "adapter"),
            (manifest("ghcr.io/lemonfiber/door"), "FROM scratch\n", "built"),
            (manifest("caddy"), DOCKERFILE, "built unpinned"),
            (manifest("caddy", OTHER), DOCKERFILE, ""),
            (manifest("caddy"), "FROM caddy:2.11.6\n", ""),
            (manifest("caddy", speaks=["stream.guard@1"]), DOCKERFILE, ""),
            (manifest("ghcr.io/lemonfiber/door", speaks=["stream.guard@1"]), DOCKERFILE, ""),
            (manifest("caddy"), None, ""),
        ):
            with self.subTest(pinned=pinned, dockerfile=dockerfile):
                self.assertEqual(first_pin.stands_in(pinned, dockerfile, "LemonFiber"), said)


class Command(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def ran(self, *asked: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = first_pin.main([*asked, "--owner", "LemonFiber", "--directory", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_a_revision_before_its_first_pin_is_refused_by_name_and_stands_in_unpinned(self):
        (self.root / "plugin.toml").write_text(
            f'[plugin]\nid = "door"\n\n[[service]]\nid = "door"\nimage = "caddy"\ndigest = "{DIGEST}"\n',
            encoding="utf-8",
        )
        (self.root / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
        code, _, said = self.ran("ships")
        self.assertEqual(code, 1)
        self.assertIn("ships nothing", said)
        self.assertEqual(self.ran("stands-in"), (0, "built unpinned\n", ""))

    def test_a_revision_running_its_own_image_ships(self):
        (self.root / "plugin.toml").write_text(
            '[plugin]\nid = "door"\n\n[[service]]\nid = "door"\nimage = "ghcr.io/lemonfiber/door"\n',
            encoding="utf-8",
        )
        (self.root / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
        self.assertEqual(self.ran("ships"), (0, "", ""))

    def test_a_manifest_that_cannot_be_read_is_a_usage_failure(self):
        code, _, said = self.ran("ships")
        self.assertEqual(code, 2)
        self.assertIn("plugin.toml", said)


if __name__ == "__main__":
    unittest.main()
