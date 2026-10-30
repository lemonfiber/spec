#!/usr/bin/env python3
"""Moving an image the bundle pins apart from its parts — ARCH-R363.

Run:  python3 scripts/test_bundle_image_pin.py
"""

from __future__ import annotations

import io
import os
import pathlib
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import bundle_image_pin
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/bundle-image-pin.yml"

IMAGE = "ghcr.io/lemonfiber/fence"
DIGEST = "sha256:" + "a" * 64
OLD = "sha256:" + "0" * 64

BUNDLE = f"""schema = 2

[[plugin]]
id = "door"
tag = "kept"

# The image a fenced service runs behind.
[fence]
image  = "{IMAGE}"
tag    = "0.17.0"  # the build
digest = "{OLD}"

[after]
image = "untouched"
"""


REPOSITORY = "lemonfiber/lemonfiber-fence"

# A `docker` answering `imagetools inspect` as the registry would: with the digest in
# `ANSWERED`, failing where it is `fail`, or with no digest where it is `none`.
DOCKER = """#!/bin/sh
case "$ANSWERED" in
fail) echo "manifest unknown" >&2; exit 1 ;;
none) echo '{}' ;;
*) printf '{"digest": "%s"}\\n' "$ANSWERED" ;;
esac
"""


def answering(test: unittest.TestCase, digest: str) -> None:
    """Put a `docker` on the PATH answering `digest` for the image, for this test."""
    stub = pathlib.Path(tempfile.mkdtemp())
    (stub / "docker").write_text(DOCKER, encoding="utf-8")
    (stub / "docker").chmod(0o755)
    patched = mock.patch.dict(
        os.environ, {"PATH": f"{stub}{os.pathsep}{os.environ['PATH']}", "ANSWERED": digest}
    )
    patched.start()
    test.addCleanup(patched.stop)


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bundle_image_pin.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Checked(unittest.TestCase):
    def test_what_the_train_hands_over_is_taken(self):
        self.assertEqual(
            bundle_image_pin.checked("fence", REPOSITORY, IMAGE, "v0.18.0", DIGEST), "0.18.0"
        )
        self.assertEqual(
            bundle_image_pin.checked("fence", REPOSITORY, IMAGE, "v0.18.0-beta.1", DIGEST),
            "0.18.0-beta.1",
        )

    def test_anything_else_is_refused_naming_it(self):
        for args, said in [
            (("Fence", REPOSITORY, IMAGE, "v0.18.0", DIGEST), "not a service id"),
            (("fence", "lemonfiber/plugin-sonarr", IMAGE, "v0.18.0", DIGEST),
             "is not lemonfiber/lemonfiber-fence, the repository fence is built in"),
            (("fence", "elsewhere/lemonfiber-fence", IMAGE, "v0.18.0", DIGEST), "is not lemonfiber/lemonfiber-fence"),
            (("fence", REPOSITORY, "ghcr.io/else/fence", "v0.18.0", DIGEST), "is not ghcr.io/lemonfiber/fence"),
            (("fence", REPOSITORY, IMAGE, "0.18.0", DIGEST), "not a tag the train cuts"),
            (("fence", REPOSITORY, IMAGE, "v0.18.0-rc1", DIGEST), "not a tag the train cuts"),
            (("fence", REPOSITORY, IMAGE, "v0.18.0", "sha256:abc"), "not a sha256 digest"),
        ]:
            with self.subTest(args=args), self.assertRaisesRegex(bundle_image_pin.Refused, said):
                bundle_image_pin.checked(*args)


class Moved(unittest.TestCase):
    def test_the_table_is_moved_and_nothing_else(self):
        after = bundle_image_pin.moved(BUNDLE, "fence", IMAGE, "0.18.0", DIGEST)
        self.assertIn('tag    = "0.18.0"  # the build', after)
        self.assertIn(f'digest = "{DIGEST}"', after)
        self.assertIn('[[plugin]]\nid = "door"\ntag = "kept"', after)
        self.assertIn('[after]\nimage = "untouched"', after)
        self.assertIn("# The image a fenced service runs behind.", after)

    def test_a_bundle_without_one_table_or_its_fields_is_refused(self):
        with self.assertRaisesRegex(bundle_image_pin.Refused, "holds 0 \\[fence\\] tables"):
            bundle_image_pin.moved("schema = 2\n", "fence", IMAGE, "0.18.0", DIGEST)
        twice = BUNDLE + "\n[fence]\n"
        with self.assertRaisesRegex(bundle_image_pin.Refused, "holds 2"):
            bundle_image_pin.moved(twice, "fence", IMAGE, "0.18.0", DIGEST)
        partial = "[fence]\nimage = \"x\"\n"
        with self.assertRaisesRegex(bundle_image_pin.Refused, "names no digest, tag"):
            bundle_image_pin.moved(partial, "fence", IMAGE, "0.18.0", DIGEST)


class Main(unittest.TestCase):
    def setUp(self):
        answering(self, DIGEST)
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.bundle = self.dir / "bundle.toml"
        self.bundle.write_text(BUNDLE, encoding="utf-8")
        self.message = self.dir / "message.txt"

    def apply(self, tag: str = "v0.18.0", digest: str = DIGEST, repository: str = REPOSITORY):
        return run(
            "apply", "--bundle", str(self.bundle), "--service", "fence", "--repository", repository,
            "--image", IMAGE, "--tag", tag, "--digest", digest, "--message", str(self.message),
        )

    def test_a_tag_moves_the_pin_and_writes_the_message(self):
        code, out, _ = self.apply()
        self.assertEqual((code, out), (0, "moved=yes\n"))
        self.assertIn(f'digest = "{DIGEST}"', self.bundle.read_text(encoding="utf-8"))
        said = self.message.read_text(encoding="utf-8")
        self.assertTrue(said.startswith("chore(bundle): the fence image at v0.18.0\n\n"))
        self.assertIn(f"{IMAGE}@{DIGEST}", said)

    def test_the_same_pin_again_moves_nothing(self):
        self.apply()
        self.message.unlink()
        code, out, _ = self.apply()
        self.assertEqual((code, out), (0, "moved=no\n"))
        self.assertFalse(self.message.exists())

    def test_a_refusal_or_an_unreadable_bundle_fails_naming_why(self):
        code, _, err = self.apply(digest="nope")
        self.assertEqual(code, 1)
        self.assertIn("::error::'nope' is not a sha256 digest", err)
        self.bundle.unlink()
        code, _, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)

    def test_another_repository_moves_nothing(self):
        code, _, err = self.apply(repository="lemonfiber/plugin-sonarr")
        self.assertEqual(code, 1)
        self.assertIn("is not lemonfiber/lemonfiber-fence", err)
        self.assertIn(f'digest = "{OLD}"', self.bundle.read_text(encoding="utf-8"))

    def test_a_digest_the_registry_does_not_answer_moves_nothing(self):
        for answered, said in [
            ("sha256:" + "b" * 64, f"is sha256:{'b' * 64} at the registry, not {DIGEST}"),
            ("fail", "the registry does not answer for ghcr.io/lemonfiber/fence:v0.18.0: manifest unknown"),
            ("none", "names no digest"),
        ]:
            with self.subTest(answered=answered):
                answering(self, answered)
                code, _, err = self.apply()
                self.assertEqual(code, 1)
                self.assertIn(said, err)
                self.assertIn(f'digest = "{OLD}"', self.bundle.read_text(encoding="utf-8"))
                self.assertFalse(self.message.exists())

    def test_it_runs_as_a_script(self):
        argv = [
            "bundle_image_pin.py", "apply", "--bundle", str(self.bundle), "--service", "fence",
            "--repository", REPOSITORY, "--image", IMAGE, "--tag", "v0.18.0", "--digest", DIGEST, "--message", str(self.message),
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as ended,
        ):
            runpy.run_path(bundle_image_pin.__file__, run_name="__main__")
        self.assertEqual(ended.exception.code, 0)


class Workflow(unittest.TestCase):
    """The token is minted only for a pushed train tag in the organisation, judged before
    any step runs, for lemonfiber-plugins alone, and nothing checked out keeps it."""

    JOBS = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]

    def test_only_a_train_tag_of_the_services_own_repository_reaches_the_token(self):
        guard = self.JOBS["commit"]["if"]
        for held in (
            "github.repository_owner == 'lemonfiber'",
            "github.repository == format('{0}/lemonfiber-{1}', github.repository_owner, inputs.service)",
            "github.event_name == 'push'",
            "github.ref_type == 'tag'",
        ):
            self.assertIn(held, guard)

    def test_the_registry_is_asked_with_a_read_only_token_before_anything_is_minted(self):
        commit = self.JOBS["commit"]
        self.assertEqual(commit["permissions"], {"contents": "read", "packages": "read"})
        names = [one.get("name", one.get("uses", "")) for one in commit["steps"]]
        login = names.index("Log in to the registry, to read")
        moved = names.index("Move the table")
        minted = next(index for index, name in enumerate(names) if "create-github-app-token" in name
                      or name == "Mint a token that can commit to the bundle")
        self.assertLess(login, moved)
        self.assertLess(moved, minted)
        self.assertIn("--repository", commit["steps"][moved]["run"])

    def test_the_token_writes_the_bundle_alone_and_no_checkout_keeps_one(self):
        steps = self.JOBS["commit"]["steps"]
        minted = [one for one in steps if one.get("uses", "").startswith("actions/create-github-app-token@")]
        self.assertEqual(len(minted), 1)
        self.assertEqual(minted[0]["with"]["repositories"], "lemonfiber-plugins")
        self.assertEqual(
            {key for key in minted[0]["with"] if key.startswith("permission-")},
            {"permission-contents"},
        )
        for one in steps:
            if one.get("uses", "").startswith("actions/checkout@"):
                self.assertFalse(one["with"]["persist-credentials"])
        self.assertEqual(self.JOBS["pull-request"]["with"]["repository"], "lemonfiber-plugins")


if __name__ == "__main__":
    unittest.main()
