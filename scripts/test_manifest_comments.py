#!/usr/bin/env python3
"""A manifest comment that says how far a goal has got is refused — OPS-R79.

The word list is narrow because the same words have other uses a manifest needs,
so both halves are driven: each state a sentence can claim for a requirement is
refused, and each ordinary use of those words — what a thing is built on, a
sentence that names no requirement, a word that is not a predicate — passes.
Stdlib unittest. Run:  python3 scripts/test_manifest_comments.py
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_manifest_comments as lint  # noqa: E402


def words(comment: str) -> list[str]:
    text = "".join(f"# {line}\n" for line in comment.splitlines()) + 'version = "0.1.0"\n'
    return [claim[1] for claim in lint.claims(text)]


class ItRefusesAStateClaimedForARequirement(unittest.TestCase):
    def test_each_word_on_the_list(self):
        self.assertEqual(words("`A1-R1` is built."), ["is built"])
        self.assertEqual(words("`A1-R1` and `A1-R2` are met by the E2 work."), ["are met"])
        self.assertEqual(words("`ARCH-R9` and `ARCH-R10` are not met."), ["are not met"])
        self.assertEqual(words("`ARCH-R5` is part met in the core."), ["is part met"])
        self.assertEqual(words("`C1-R1` is done."), ["is done"])
        self.assertEqual(words("`C1-R1` is partial."), ["is partial"])
        self.assertEqual(words("`C1-R1` is already built in two places."), ["is already built"])
        self.assertEqual(words("`E2-R10` landed in `abc1234`."), ["landed in"])

    def test_a_sentence_wrapped_across_lines_is_read_whole(self):
        text = "# `A1-R1` and `A1-R2`\n# are\n# built.\n"
        self.assertEqual(lint.claims(text), [(2, "are built",
                                             "`A1-R1` and `A1-R2` are built.")])

    def test_a_long_sentence_is_quoted_short(self):
        long = "`A1-R1` is built, " + "and so on " * 30 + "end."
        quoted = lint.claims(f"# {long}\n")[0][2]
        self.assertTrue(quoted.endswith("…"))
        self.assertLessEqual(len(quoted), lint.QUOTED + 1)


class ItPassesTheOtherUsesOfThoseWords(unittest.TestCase):
    def test_what_a_thing_is_built_on(self):
        self.assertEqual(words("`F9-R2` and `F9-R5` are built on the contract."), [])
        self.assertEqual(words("Setup from the web (`G1-R14`) is built against the source."), [])
        self.assertEqual(words("`A1-R1` is built from the manifest."), [])

    def test_a_sentence_naming_no_requirement(self):
        self.assertEqual(words("The web surface is where these are built, so it is searched."), [])

    def test_a_word_that_is_not_a_predicate(self):
        self.assertEqual(words("`L3-R1` to `L3-R8` are the image, built by the release."), [])

    def test_the_next_sentence_does_not_borrow_an_identifier(self):
        self.assertEqual(words("`A1-R1` is here. The web surface is where these are built."), [])


class TheCommandLine(unittest.TestCase):
    def run_on(self, files):
        root = pathlib.Path(tempfile.mkdtemp())
        versions = root / lint.VERSIONS
        versions.mkdir(parents=True)
        for name, text in files.items():
            (versions / name).write_text(text, encoding="utf-8")
        out = io.StringIO()
        saved = sys.argv
        sys.argv = ["check_manifest_comments.py", "--root", str(root)]
        try:
            with contextlib.redirect_stdout(out):
                code = lint.main()
        finally:
            sys.argv = saved
        return code, out.getvalue()

    def test_a_clean_train_passes(self):
        code, said = self.run_on({"0.1.0.toml": "# `A1-R1` asks for a form.\nversion = \"0.1.0\"\n"})
        self.assertEqual(code, 0)
        self.assertIn("1 manifests say why", said)

    def test_a_claim_is_named_with_its_file_and_line_and_where_it_belongs(self):
        code, said = self.run_on({"0.1.0.toml": "version = \"0.1.0\"\n\n# `A1-R1` is built.\n"})
        self.assertEqual(code, 1)
        self.assertIn("0.1.0.toml:3: \"is built\"", said)
        self.assertIn("status.toml (OPS-R79)", said)

    def test_no_manifests_is_not_a_pass(self):
        code, said = self.run_on({})
        self.assertEqual(code, 2)
        self.assertIn("no manifests", said)


if __name__ == "__main__":
    unittest.main()
