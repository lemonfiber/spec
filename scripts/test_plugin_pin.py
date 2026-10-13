#!/usr/bin/env python3
"""`plugin_pin.py`: every service running an image moves to the new pin, and nothing else does.

Stdlib unittest, no dependencies.
Run:  python3 scripts/test_plugin_pin.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import plugin_pin

IMAGE = "lscr.io/linuxserver/sonarr"
DIGEST = "sha256:" + "a" * 64
OLD = "sha256:" + "0" * 64
MANIFEST = f'''schema_version = 1

[plugin]
id = "sonarr"

[[service]]
id          = "sonarr"
image       = "{IMAGE}"
digest      = "{OLD}"
tag         = "4.0.20.3014-ls326"  # the build the stack ran
port        = 8989

[[service.mount]]
from = "cache"
to   = "/cache"

[[service]]
id     = "other"
image  = "caddy"
digest = "sha256:{"1" * 64}"
tag    = "2.11.6"
'''


class Pinned(unittest.TestCase):
    """The text rewrite, read back."""

    def test_the_running_service_moves_and_every_other_line_stays(self):
        written, moved = plugin_pin.pinned(MANIFEST, IMAGE, "4.0.21.3020-ls327", DIGEST)
        self.assertEqual(moved, ["sonarr"])
        self.assertIn(f'digest      = "{DIGEST}"\n', written)
        self.assertIn('tag         = "4.0.21.3020-ls327"  # the build the stack ran\n', written)
        self.assertEqual(written.replace(DIGEST, OLD).replace("4.0.21.3020-ls327", "4.0.20.3014-ls326"), MANIFEST)
        services = {one["id"]: one for one in tomllib.loads(written)["service"]}
        self.assertEqual(services["other"]["tag"], "2.11.6")

    def test_every_service_running_the_image_moves(self):
        twice = MANIFEST.replace('image  = "caddy"', f'image  = "{IMAGE}"')
        written, moved = plugin_pin.pinned(twice, IMAGE, "4.0.21", DIGEST)
        self.assertEqual(moved, ["sonarr", "other"])
        self.assertEqual(written.count(DIGEST), 2)

    def test_a_manifest_naming_no_service_of_the_image_moves_nothing(self):
        self.assertEqual(plugin_pin.pinned(MANIFEST, "elsewhere", "1", DIGEST), (MANIFEST, []))

    def test_a_digest_or_a_tag_that_is_not_one_is_refused(self):
        for tag, digest in (("1", "sha256:short"), ("1", DIGEST.upper()), ("-1", DIGEST), ('1"\n[x]', DIGEST)):
            with self.subTest(tag=tag, digest=digest), self.assertRaises(plugin_pin.Refused):
                plugin_pin.pinned(MANIFEST, IMAGE, tag, digest)

    def test_a_running_service_without_a_field_to_move_is_refused(self):
        for field, line in (("digest", f'digest      = "{OLD}"\n'),
                            ("tag", 'tag         = "4.0.20.3014-ls326"  # the build the stack ran\n')):
            without = MANIFEST.replace(line, "")
            with self.subTest(field=field), self.assertRaisesRegex(plugin_pin.Refused, f"`{field}` once"):
                plugin_pin.pinned(without, IMAGE, "1", DIGEST)

    def test_a_service_written_so_the_rewrite_cannot_see_it_is_refused(self):
        quoted = MANIFEST.replace(f'image       = "{IMAGE}"', f"image       = '{IMAGE}'")
        with self.assertRaisesRegex(plugin_pin.Refused, "1 services run .* and 0 are written"):
            plugin_pin.pinned(quoted, IMAGE, "1", DIGEST)

    def test_a_rewrite_the_manifest_does_not_read_back_is_refused(self):
        hidden = MANIFEST.replace(
            f'digest      = "{OLD}"',
            f'why = """\ndigest = "not a field"\n"""\n"digest" = "{OLD}"', 1)
        with self.assertRaisesRegex(plugin_pin.Refused, "is not the one it was"):
            plugin_pin.pinned(hidden, IMAGE, "1", DIGEST)


class Main(unittest.TestCase):
    """The command writes the manifest in place, and says what moved or why it did not."""

    def run_on(self, text: str, *args: str, link: bool = False) -> tuple[int, str, str, str]:
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as scratch:
            os.chdir(scratch)
            try:
                target = pathlib.Path(scratch) / ("elsewhere.toml" if link else "plugin.toml")
                target.write_text(text, encoding="utf-8")
                if link:
                    os.symlink(target, pathlib.Path(scratch) / "plugin.toml")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = plugin_pin.main(["--manifest", "plugin.toml", *args])
                return code, out.getvalue(), err.getvalue(), target.read_text(encoding="utf-8")
            finally:
                os.chdir(here)

    def test_a_manifest_that_is_a_link_is_neither_read_nor_written(self):
        code, out, err, written = self.run_on(MANIFEST, "--image", IMAGE, "--tag", "4.0.21", "--digest", DIGEST,
                                              link=True)
        self.assertEqual((code, out, written), (1, "", MANIFEST))
        self.assertIn("is a link", err)

    def test_a_move_is_written_and_named(self):
        code, out, _, written = self.run_on(MANIFEST, "--image", IMAGE, "--tag", "4.0.21", "--digest", DIGEST)
        self.assertEqual((code, out), (0, "sonarr\n"))
        self.assertIn(DIGEST, written)

    def test_nothing_to_move_leaves_the_file_and_says_nothing(self):
        code, out, _, written = self.run_on(MANIFEST, "--image", "elsewhere", "--tag", "1", "--digest", DIGEST)
        self.assertEqual((code, out, written), (0, "", MANIFEST))

    def test_a_refusal_writes_nothing_and_names_why(self):
        code, out, err, written = self.run_on(MANIFEST, "--image", IMAGE, "--tag", "1", "--digest", "nope")
        self.assertEqual((code, out, written), (1, "", MANIFEST))
        self.assertIn("::error::'nope' is not a sha256 digest", err)

    def test_a_manifest_that_is_not_toml_is_refused(self):
        code, _, err, _ = self.run_on("[[service]\n", "--image", IMAGE, "--tag", "1", "--digest", DIGEST)
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)


if __name__ == "__main__":
    unittest.main()
