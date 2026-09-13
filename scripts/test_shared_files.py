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
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent

#: A registry with one maintainer scoped to everything, which is what the real
#: one holds. `gen_codeowners.py` turns this into `* @lead`.
REGISTRY = """
[[maintainer]]
handle  = "lead"
name    = "A Lead"
lead    = true
scope   = ["*"]
domains = ["*"]
"""
sys.path.insert(0, str(HERE))
import check_shared_files  # noqa: E402

MARKDOWNLINT = '{\n  "default": true,\n  "MD013": false\n}\n'
TYPOS = (
    "[default]\n"
    "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"ratatui\" }\n"
    "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\"]\n"
)
GATE = """#!/usr/bin/env python3
\"\"\"A gate, for the fixture to compare copies of.\"\"\"
import sys

if __name__ == "__main__":
    sys.exit(0)
"""

HOOK = "#!/bin/sh\n# Refuse a push that would empty the branch it lands on.\nexit 0\n"
RUFF = (
    "# The Python lint floor.\n"
    'target-version = "py312"\n'
    "line-length = 110\n"
    "\n"
    "[lint]\n"
    'select = ["E", "F", "ISC"]\n'
    'ignore = ["E501"]\n'
)
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
        (shared / "gates").mkdir(parents=True)
        self.repo.mkdir()

        # The real generator and a registry for it to read, rather than a stub:
        # what the check compares against is this script's output, so a stub here
        # would be testing the stub.
        (self.canonical / "scripts").mkdir(parents=True)
        shutil.copy(HERE / "gen_codeowners.py", self.canonical / "scripts")
        (self.canonical / "70-operations").mkdir(parents=True)
        (self.canonical / "70-operations" / "maintainers.toml").write_text(
            REGISTRY, encoding="utf-8")

        (shared / "markdownlint.jsonc").write_text(MARKDOWNLINT, encoding="utf-8")
        (shared / "typos.toml").write_text(TYPOS, encoding="utf-8")
        (shared / "ruff.toml").write_text(RUFF, encoding="utf-8")
        (shared / "hooks" / "pre-push").write_text(HOOK, encoding="utf-8")
        (shared / "gates" / "a_gate.py").write_text(GATE, encoding="utf-8")
        self.manifest(f"{self.digest(LOGO)}  .github/logo.svg  brand:assets/logo/lockup.svg")

        # The repo under test also carries the file the manifest names as the
        # home, so that a run as the home repository has the original in front
        # of it. Without it every such run reports a home that is not there,
        # which is a true answer about this fixture and an unhelpful one.
        self.write("assets/logo/lockup.svg", LOGO)

        self.write(".markdownlint.jsonc", MARKDOWNLINT)
        self.write("typos.toml", TYPOS)
        self.write(".github/CODEOWNERS", self.generated())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def generated(self, repo_name="cli"):
        """What `gen_codeowners.py` writes for a repo, asked of the real script."""
        done = subprocess.run(
            [sys.executable, str(self.canonical / "scripts" / "gen_codeowners.py"), repo_name],
            capture_output=True, text=True, check=True)
        return done.stdout

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
        self.assertIn("match their one home", out)

    def test_an_asset_the_repo_does_not_carry_is_not_asked_for(self):
        # The manifest lists what a copy must equal, not what a repo must have.
        self.assertFalse((self.repo / ".github" / "logo.svg").exists())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("logo.svg", out)

    def test_an_asset_the_repo_carries_and_matches(self):
        self.write(".github/logo.svg", LOGO)
        self.assertEqual(self.check()[0], 0)

    def test_the_home_repos_own_copy_of_a_row_is_not_checked_against_itself(self):
        # brand maintains the lockup, so its `.github/logo.svg` is not held to
        # the row that names brand as the home — the original is what that row
        # is about, and it is checked separately below.
        self.write(".github/logo.svg", OTHER)
        code, out = self.check("lemonfiber/brand")
        self.assertEqual(code, 0, out)

    def test_a_home_file_that_still_hashes_to_what_the_manifest_records(self):
        code, out = self.check("lemonfiber/brand")
        self.assertEqual(code, 0, out)
        self.assertNotIn("lockup.svg", out)

    def test_a_repo_carrying_no_hook_manager_config(self):
        # The state every repository is in, and the one this keeps them in.
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("hook manager", out)

    def test_a_repo_with_no_ruff_config_is_not_asked_for_one(self):
        # Conditional, as the hook is. A repository with no Python has nothing to
        # lint, and requiring the file would mean carrying a config for a
        # language it does not use.
        self.assertFalse((self.repo / "ruff.toml").exists())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("ruff.toml", out)

    def test_a_ruff_config_holding_the_same_lists(self):
        self.write("ruff.toml", RUFF)
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_ruff_config_selecting_more_than_the_floor(self):
        # The direction that is allowed: a rule added here raises this
        # repository's standard and costs nobody else anything.
        self.write("ruff.toml", RUFF.replace('"ISC"]', '"ISC", "PERF", "PL"]'))
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_ruff_config_with_a_preamble_of_its_own(self):
        # Not compared byte for byte: each copy says what its own scripts are and
        # why they are worth linting, and those paragraphs differ because the
        # scripts do.
        self.write("ruff.toml", "# The gates in scripts/, and what they decide.\n" + RUFF)
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_ruff_config_holding_a_narrower_line(self):
        # Narrower is stricter, and stricter is this repository's business.
        self.write("ruff.toml", RUFF.replace("line-length = 110", "line-length = 88"))
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_typos_config_adding_words_and_patterns_of_its_own(self):
        # The shared config is a floor: a repo may add entries, never contradict one.
        self.write("typos.toml",
                   "[default]\n"
                   "extend-words = { lemonfiber = \"lemonfiber\", ratatui = \"ratatui\", "
                   "Servarr = \"Servarr\" }\n"
                   "extend-ignore-re = [\"\\\\[[a-z]\\\\][a-zA-Z]+\", \"SPDX-.*\"]\n")
        self.assertEqual(self.check()[0], 0)

    def test_a_repo_running_no_gate_script_is_not_asked_for_one(self):
        # Conditional, as the hook is. A repository that gates on nothing here is
        # not failed for it; one carrying a copy must carry the current one.
        self.assertFalse((self.repo / "scripts" / "a_gate.py").exists())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("a_gate.py", out)

    def test_a_repo_carrying_the_current_gate(self):
        self.write("scripts/a_gate.py", GATE)
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_gate_that_has_drifted(self):
        # Worse than no gate, because it is trusted: `no_open_codeql_alert.py`
        # spent its whole life reading an empty alert list as a clean one, and a
        # repository still carrying that version reports a pass it has not earned.
        self.write("scripts/a_gate.py", GATE + "\n# a local tweak\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("scripts/a_gate.py differs from the canonical copy", out)

    def test_a_gate_rewritten_with_carriage_returns(self):
        # Reading both as text folds CRLF to LF and calls them identical. The
        # kernel disagrees: the interpreter the first line names has a carriage
        # return on the end of it.
        self.write("scripts/a_gate.py", GATE.replace("\n", "\r\n"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("a_gate.py differs", out)

    def test_a_gate_added_to_shared_is_compared_everywhere(self):
        # Listed from the canonical directory rather than named in the script, so
        # a second gate cannot be copied into every repository and compared in
        # none — which is what a hard-coded list did to `shared/hooks/`.
        (self.canonical / "shared" / "gates" / "another.py").write_text(
            GATE, encoding="utf-8")
        self.write("scripts/another.py", GATE + "# drifted\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("scripts/another.py differs", out)

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

    def test_a_repo_that_is_nobodys_home_is_asked_for_no_original(self):
        # The row names brand as the home, so a run as any other repository
        # checks the copy and never looks for `assets/logo/lockup.svg`.
        (self.repo / "assets" / "logo" / "lockup.svg").unlink()
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("lockup.svg", out)

    def test_a_tool_cache_in_the_shared_directory_is_not_a_shared_file(self):
        """`uvx ruff` run with `shared/` as its working directory leaves a
        `.ruff_cache/` there. Nothing copies it anywhere, so naming it as an
        uncompared shared file turns every later run of this check red over a
        directory no repository has ever carried."""
        (self.canonical / "shared" / ".ruff_cache").mkdir()
        (self.canonical / "shared" / ".ruff_cache" / "CACHEDIR.TAG").write_text(
            "Signature: 8a477f597d28d172789f06886806bc55\n", encoding="utf-8")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn(".ruff_cache", out)


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

    def test_a_lefthook_config(self):
        # Not a style preference: `core.hooksPath` makes it inert, and the one
        # command that would repair it unsets the setting and takes the pre-push
        # guard with it.
        self.write("lefthook.yml", "pre-commit:\n  commands:\n    lint:\n      run: true\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("lefthook.yml is a hook manager's config", out)
        self.assertIn("turn off the pre-push guard", out)
        self.assertIn(".githooks/pre-commit", out)

    def test_a_captainhook_config(self):
        self.write("captainhook.json", "{}\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("captainhook.json is a hook manager's config", out)

    def test_the_other_spellings_lefthook_accepts(self):
        # lefthook reads four names. Refusing one and letting the other three
        # through would be a rule that reads as enforced and is not.
        for name in ("lefthook.yaml", ".lefthook.yml"):
            with self.subTest(name):
                path = self.write(name, "pre-commit:\n")
                code, out = self.check()
                self.assertEqual(code, 1, out)
                self.assertIn(name, out)
                path.unlink()

    def test_a_ruff_config_selecting_fewer_rules_than_the_floor(self):
        self.write("ruff.toml", RUFF.replace(', "ISC"]', "]"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("does not select 'ISC'", out)

    def test_a_ruff_config_silencing_a_rule_the_floor_keeps(self):
        # The direction that is refused, and the reason the message gives: an
        # ignore added here lowers the standard every repository is held to,
        # while looking like a local decision.
        self.write("ruff.toml", RUFF.replace('ignore = ["E501"]', 'ignore = ["E501", "B007"]'))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("ignores 'B007'", out)
        self.assertIn("lowers the floor", out)
        self.assertIn("add it to shared/ruff.toml with the reason", out)

    def test_a_ruff_config_allowing_a_wider_line(self):
        self.write("ruff.toml", RUFF.replace("line-length = 110", "line-length = 200"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("allows 200 columns, shared allows 110", out)

    def test_a_ruff_config_that_states_no_width_is_left_alone(self):
        # `ruff` has a default of its own, and a copy that does not set one is
        # taking that default rather than widening anything.
        self.write("ruff.toml", RUFF.replace("line-length = 110\n", ""))
        code, out = self.check()
        self.assertEqual(code, 0, out)

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

    def test_a_home_that_moved_away_from_its_own_record(self):
        # The failure this half exists for. Changing the original is allowed;
        # leaving the manifest behind is what every copy then follows, and
        # nothing anywhere used to say so.
        self.write("assets/logo/lockup.svg", OTHER)
        code, out = self.check("lemonfiber/brand")
        self.assertEqual(code, 1, out)
        self.assertIn("assets/logo/lockup.svg no longer hashes to what", out)
        self.assertIn(self.digest(OTHER), out)
        self.assertIn("refresh the copies in the same round", out)

    def test_a_home_the_manifest_names_and_the_repo_does_not_have(self):
        (self.repo / "assets" / "logo" / "lockup.svg").unlink()
        code, out = self.check("lemonfiber/brand")
        self.assertEqual(code, 1, out)
        self.assertIn("is named as a home in shared/assets.sha256 and is not here", out)

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

    def test_a_shared_file_no_check_here_compares(self):
        """The corpus this file checks is named check by check, and `shared/` is a
        directory anyone may add to. A file added there is copied into every
        repository by whoever adds it and compared in none — and the run still
        says the copies match, which is true of the ones it looked at."""
        (self.canonical / "shared" / "eslint.json").write_text("{}\n", encoding="utf-8")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("shared/eslint.json is compared by nothing here", out)

    def test_a_hook_added_to_the_shared_directory_is_compared(self):
        """The hook names were written when there were two. A third is read from
        the canonical directory rather than waited for."""
        (self.canonical / "shared" / "hooks" / "pre-commit").write_text(
            HOOK, encoding="utf-8")
        self.write(".githooks/pre-commit", HOOK.replace("exit 0", "exit 1"))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn(".githooks/pre-commit differs from the canonical copy", out)

    def test_every_kind_of_drift_is_reported_together(self):
        (self.repo / ".markdownlint.jsonc").unlink()
        self.write("typos.toml", "[default]\nextend-words = {}\n")
        self.write(".github/logo.svg", OTHER)
        self.write(".githooks/pre-push", "#!/bin/sh\nexit 1\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("6 shared file(s) out of step with", out)


class Owners(Copies):
    """`OPS-R17` — CODEOWNERS is generated from the registry, in every repo.

    Required rather than conditional, unlike the hooks: five of the seven
    implementation repositories had no CODEOWNERS at all, and the absence
    satisfied "never hand-edited" in the only sense anything was asking about.
    """

    def test_a_generated_codeowners_agrees(self):
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_a_missing_codeowners_is_refused(self):
        (self.repo / ".github" / "CODEOWNERS").unlink()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("CODEOWNERS is missing", out)
        self.assertIn("gen_codeowners.py", out)

    def test_a_hand_edited_codeowners_is_refused(self):
        self.write(".github/CODEOWNERS", self.generated() + "* @someone-else\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("differs from what the registry generates", out)

    def test_the_message_names_the_repo_to_generate_for(self):
        # The fix is one command, and it takes the repo's name. Printing the
        # name means the reader does not have to work out which one they are in.
        (self.repo / ".github" / "CODEOWNERS").unlink()
        _, out = self.check(repo_name="lemonfiber/sdk-php")
        self.assertIn("gen_codeowners.py sdk-php", out)

    def test_without_a_repo_name_it_says_so_rather_than_guessing(self):
        # The generator's output depends on the name, so there is nothing to
        # compare against without one. Saying so beats comparing against a guess.
        code, out = self.check(repo_name="")
        self.assertEqual(code, 1)
        self.assertIn("--repo was not given", out)

    def test_a_generator_that_cannot_run_says_so_rather_than_failing_the_repo(self):
        # A broken canonical checkout is this check's fault, not the repo's, and
        # reporting it as a missing file would send somebody to fix the wrong tree.
        (self.canonical / "70-operations" / "maintainers.toml").unlink()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("could not generate", out)


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
