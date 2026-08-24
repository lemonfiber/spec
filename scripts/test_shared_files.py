#!/usr/bin/env python3
"""Coverage tests for check_shared_files.py — every copy of a shared file still
agrees with the one home it was taken from (GOV-R12, Q-R56).

It runs in the `hygiene` reusable workflow against whichever repository called
it, with the spec checked out beside it, so a copy that has quietly drifted is
what this refuses on every repo in the org. Each refusal is checked by the
message a maintainer would read as well as by the exit code: the message names
the home to copy from, which is the whole of the fix.

Stdlib unittest, no dependencies (the repo has none). A canonical `shared/` and
a repository to check are built in a temporary directory.
Run:  python3 scripts/test_shared_files.py
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_shared_files  # noqa: E402

MARKDOWNLINT = '{\n  "default": true,\n  "MD013": false\n}\n'
TYPOS = (
    "[default]\n"
    "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"ratatui\" }\n"
    "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\"]\n"
)
HOOK = "#!/bin/sh\n# Refuse a push that would empty the branch it lands on.\nexit 0\n"
LOGO = "<svg><!-- the lockup --></svg>\n"
OTHER = "<svg><!-- something else --></svg>\n"


def run_main(argv):
    """Call check_shared_files.main() with argv patched; return (code, stdout)."""
    out = io.StringIO()
    saved = sys.argv
    sys.argv = ["check_shared_files", *argv]
    try:
        with contextlib.redirect_stdout(out):
            code = check_shared_files.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


class Copies(unittest.TestCase):
    """A spec checkout holding the canonical files, and a repo carrying copies."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.canonical = self.tmp / "spec"
        self.repo = self.tmp / "repo"
        shared = self.canonical / "shared"
        (shared / "hooks").mkdir(parents=True)
        self.repo.mkdir()

        (shared / "markdownlint.jsonc").write_text(MARKDOWNLINT, encoding="utf-8")
        (shared / "typos.toml").write_text(TYPOS, encoding="utf-8")
        (shared / "hooks" / "pre-push").write_text(HOOK, encoding="utf-8")
        self.manifest(f"{self.digest(LOGO)}  .github/logo.svg  brand:assets/logo/lockup.svg")

        self.write(".markdownlint.jsonc", MARKDOWNLINT)
        self.write("typos.toml", TYPOS)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def digest(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def manifest(self, *rows):
        (self.canonical / "shared" / "assets.sha256").write_text(
            "# Brand assets more than one repository carries a copy of.\n"
            "#\n"
            "# Each row is: <sha256>  <path in the repo>  <home>\n"
            "\n" + "\n".join(rows) + "\n",
            encoding="utf-8")

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def check(self, repo_name="lemonfiber/cli"):
        return run_main(["--canonical", str(self.canonical), "--repo", repo_name,
                         "--root", str(self.repo)])


class Agreeing(Copies):
    """Everything the check must let through. A shared-file gate that refuses a
    correct copy blocks every repository at once."""

    def test_a_repo_whose_copies_all_agree(self):
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("match their canonical copies", out)

    def test_an_asset_the_repo_does_not_carry_is_not_asked_for(self):
        # The manifest lists what a copy must equal, not what a repo must have.
        self.assertFalse((self.repo / ".github" / "logo.svg").exists())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("logo.svg", out)

    def test_an_asset_the_repo_carries_and_matches(self):
        self.write(".github/logo.svg", LOGO)
        self.assertEqual(self.check()[0], 0)

    def test_the_repo_that_is_an_asset_home_is_not_checked_against_itself(self):
        # brand maintains the lockup; its own file is the original, not a copy,
        # and it must be free to change it.
        self.write(".github/logo.svg", OTHER)
        code, out = self.check("lemonfiber/brand")
        self.assertEqual(code, 0, out)

    def test_a_typos_config_adding_words_and_patterns_of_its_own(self):
        # The shared config is a floor: a repo may add entries, never contradict one.
        self.write("typos.toml",
                   "[default]\n"
                   "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"ratatui\", "
                   "Servarr = \"Servarr\" }\n"
                   "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\", \"SPDX-.*\"]\n")
        self.assertEqual(self.check()[0], 0)

    def test_a_repo_that_has_not_adopted_the_hook_is_not_failed_for_it(self):
        # Conditional, not required: hooks are opted into per clone, and a repo
        # without one is not carrying a copy that could have drifted.
        self.assertFalse((self.repo / ".githooks" / "pre-push").exists())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("pre-push", out)

    def test_a_repo_carrying_the_current_hook(self):
        self.write(".githooks/pre-push", HOOK)
        self.assertEqual(self.check()[0], 0)

    def test_a_bare_repo_name_is_read_the_same_as_a_qualified_one(self):
        self.write(".github/logo.svg", OTHER)
        self.assertEqual(self.check("brand")[0], 0)


class Drifted(Copies):
    """Every refusal, and the home each message sends the reader to."""

    def test_a_markdownlint_config_that_is_not_there(self):
        (self.repo / ".markdownlint.jsonc").unlink()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".markdownlint.jsonc is missing; copy", out)
        self.assertIn("shared/markdownlint.jsonc", out)
        self.assertIn("1 shared file(s) out of step with", out)

    def test_a_markdownlint_config_whose_keys_were_reordered(self):
        # Copied verbatim, key order included: the file is compared, not parsed.
        self.write(".markdownlint.jsonc", '{\n  "MD013": false,\n  "default": true\n}\n')
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".markdownlint.jsonc differs from the canonical copy", out)

    def test_a_typos_config_that_is_not_there(self):
        (self.repo / "typos.toml").unlink()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("typos.toml is missing; copy", out)

    def test_a_typos_config_missing_a_shared_word(self):
        self.write("typos.toml",
                   "[default]\n"
                   "extend-words = { lemonfiber = \"lemonfiber\" }\n"
                   "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\"]\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("typos.toml is missing the shared word 'ratatui'", out)

    def test_a_typos_config_contradicting_a_shared_word(self):
        self.write("typos.toml",
                   "[default]\n"
                   "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"Ratatui\" }\n"
                   "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\"]\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("typos.toml maps 'ratatui' to 'Ratatui', shared is 'ratatui'", out)

    def test_a_typos_config_missing_a_shared_pattern(self):
        self.write("typos.toml",
                   "[default]\n"
                   "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"ratatui\" }\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(r"missing the shared pattern '\\[[a-z]\\][a-zA-Z]+'", out)

    def test_a_typos_config_with_no_defaults_table_at_all(self):
        self.write("typos.toml", "[files]\nextend-exclude = []\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("missing the shared word", out)
        self.assertIn("missing the shared pattern", out)

    def test_an_asset_edited_where_it_was_copied_to(self):
        self.write(".github/logo.svg", OTHER)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".github/logo.svg differs from brand/assets/logo/lockup.svg", out)
        self.assertIn("copy it again rather than editing it here", out)

    def test_every_drifted_asset_is_named(self):
        self.manifest(
            f"{self.digest(LOGO)}  .github/logo.svg  brand:assets/logo/lockup.svg",
            f"{self.digest(LOGO)}  public/logo.svg   brand:assets/logo/lockup.svg")
        self.write(".github/logo.svg", OTHER)
        self.write("public/logo.svg", OTHER)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".github/logo.svg differs", out)
        self.assertIn("public/logo.svg differs", out)
        self.assertIn("2 shared file(s) out of step with", out)

    def test_a_hook_that_has_drifted(self):
        self.write(".githooks/pre-push", HOOK.replace("exit 0", "exit 0  # edited here"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".githooks/pre-push differs from the canonical copy", out)
        self.assertIn("shared/hooks/pre-push", out)

    def test_a_hook_whose_line_endings_changed(self):
        # A guard the kernel will not run: `#!/bin/sh\r` is not an interpreter.
        # Nothing about it is visible in the text, so the bytes are what is compared.
        self.write(".githooks/pre-push", HOOK.replace("\n", "\r\n"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".githooks/pre-push differs from the canonical copy", out)

    def test_every_kind_of_drift_is_reported_together(self):
        (self.repo / ".markdownlint.jsonc").unlink()
        self.write("typos.toml", "[default]\nextend-words = {}\n")
        self.write(".github/logo.svg", OTHER)
        self.write(".githooks/pre-push", "#!/bin/sh\nexit 1\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("6 shared file(s) out of step with", out)


class Usage(Copies):
    def test_a_canonical_path_with_no_shared_directory(self):
        shutil.rmtree(self.canonical / "shared")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("no shared/ directory under", out)

    def test_the_manifest_is_read_past_its_own_prose(self):
        # It opens with a comment block explaining itself, and rows are spaced out.
        rows = list(check_shared_files.asset_rows(self.canonical))
        self.assertEqual(rows, [(self.digest(LOGO), ".github/logo.svg",
                                 "brand", "assets/logo/lockup.svg")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
