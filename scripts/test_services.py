#!/usr/bin/env python3
"""Coverage tests for the bundled-service count gate — Q-R61, Q-R66.

Most of what follows is a refusal, because a gate is worth what it refuses. The two
that matter are the silences: a stack manifest that could not be read, and a tree
holding no governed sentence at all. Both would otherwise read as a pass, and the
second is the one that fires exactly when the prose format has moved under the gate.

The pattern is held to counting words rather than to any word. Its first draft was
`\\w+`, which offered to rewrite "the bundled services" and "on bundled services" —
a gate loose enough to catch every phrasing catches sentences about other things.

Stdlib unittest, no dependencies. Run:  python3 scripts/test_services.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_services  # noqa: E402

STACK = "\n".join(f'[[service]]\nid = "s{n}"\n' for n in range(20))


def run(argv: list[str]) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        kept, sys.argv = sys.argv, ["check_services.py", *argv]
        try:
            code = check_services.main()
        except SystemExit as stopped:
            code = stopped.code
        finally:
            sys.argv = kept
    return code, said.getvalue()


class ServiceCount(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.addCleanup(lambda: os.chdir(self.cwd))
        self.stack = pathlib.Path("stack.toml")
        self.stack.write_text(STACK, encoding="utf-8")
        (self.tmp / "00-overview" / "decisions").mkdir(parents=True)

    def page(self, name: str, body: str) -> pathlib.Path:
        page = pathlib.Path(name)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(body, encoding="utf-8")
        return page

    def gate(self, *extra: str):
        return run(["--stack", str(self.stack), "--root", ".", *extra])

    def test_prose_that_agrees_with_the_stack_passes(self):
        self.page("a.md", "The twenty bundled services it composes.\n")
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn("twenty — 1 page(s) agree", said)

    def test_prose_that_disagrees_is_named_with_both_numbers(self):
        self.page("a.md", "The nineteen bundled services it composes.\n")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("a.md says 'nineteen bundled services'; the stack composes twenty", said)

    def test_writing_puts_the_computed_word_in(self):
        page = self.page("a.md", "The nineteen bundled services it composes.\n")
        code, said = self.gate("--write")
        self.assertEqual(code, 0, said)
        self.assertIn("twenty bundled services", page.read_text(encoding="utf-8"))
        self.assertIn("rewrote 1 of 1", said)

    def test_a_page_already_right_is_not_rewritten(self):
        self.page("a.md", "The twenty bundled services it composes.\n")
        code, said = self.gate("--write")
        self.assertEqual(code, 0, said)
        self.assertIn("rewrote 0 of 1", said)

    # The silences.

    def test_a_tree_with_no_governed_sentence_cannot_answer(self):
        self.page("a.md", "No count here at all.\n")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("nothing to check", said)

    def test_a_stack_that_is_not_there_cannot_answer(self):
        self.page("a.md", "The twenty bundled services.\n")
        code, said = run(["--stack", "nowhere.toml", "--root", "."])
        self.assertEqual(code, 2)
        self.assertIn("no stack manifest at", said)

    def test_a_stack_that_cannot_be_read_cannot_answer(self):
        self.stack.write_text("[[service\n", encoding="utf-8")
        self.page("a.md", "The twenty bundled services.\n")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("cannot be read", said)

    def test_a_stack_composing_nothing_cannot_answer(self):
        self.stack.write_text("schema_version = 1\n", encoding="utf-8")
        self.page("a.md", "The twenty bundled services.\n")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("read the wrong file", said)

    def test_a_path_outside_the_working_tree_is_refused(self):
        self.page("a.md", "The twenty bundled services.\n")
        code, said = run(["--stack", "/etc/hosts", "--root", "."])
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", said)

    def test_a_stack_the_url_cannot_reach_cannot_answer(self):
        self.page("a.md", "The twenty bundled services.\n")
        code, said = run(["--stack", "https://127.0.0.1:1/stack.toml", "--root", "."])
        self.assertEqual(code, 2)
        self.assertIn("could not read", said)

    def test_a_stack_fetched_over_the_wire_is_read(self):
        # The fetch itself is stood in for rather than performed: a suite that
        # reached the network would fail on a runner without one and pass by not
        # asking, which is the silence this gate refuses. What is held here is that
        # what comes back over the wire is read the same way a file is.
        class Answered:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return STACK.encode("utf-8")

        self.page("a.md", "The twenty bundled services.\n")
        real = check_services.urllib.request.urlopen
        check_services.urllib.request.urlopen = lambda *_, **__: Answered()
        self.addCleanup(lambda: setattr(check_services.urllib.request, "urlopen", real))
        code, said = run(["--stack", "https://example.test/stack.toml", "--root", "."])
        self.assertEqual(code, 0, said)
        self.assertIn("1 page(s) agree", said)

    def test_more_services_than_counting_words_cannot_answer(self):
        self.stack.write_text(
            "\n".join(f'[[service]]\nid = "s{n}"\n' for n in range(99)), encoding="utf-8"
        )
        self.page("a.md", "The twenty bundled services.\n")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("past the counting words", said)

    # What the pattern must not reach.

    def test_a_sentence_without_a_counting_word_is_not_governed(self):
        # The first draft matched any word and offered to rewrite both of these.
        self.page("a.md", "The twenty bundled services.\nNote on bundled services.\n")
        self.page("b.md", "What the bundled services do.\n")
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn("1 page(s) agree", said)

    def test_a_decision_record_is_never_rewritten(self):
        record = self.page("00-overview/decisions/0023-a-pin.md",
                           "each of the nineteen bundled services is pinned\n")
        self.page("a.md", "The twenty bundled services.\n")
        code, said = self.gate("--write")
        self.assertEqual(code, 0, said)
        self.assertIn("nineteen bundled services", record.read_text(encoding="utf-8"))

    def test_a_clone_of_another_repository_holds_no_prose_of_ours(self):
        """`checkouts/` is where the other repositories are put, by hand and by
        the release lane, and one of them states this count in its own tracker.

        Read as ours, `just ci` goes red naming a file in a foreign repository,
        and `--write` edits inside somebody else's git repository where
        `.gitignore` means nothing would ever say so.
        """
        foreign = self.page("checkouts/lemonfiber/IMPLEMENTATION-STATUS.md",
                            "the nineteen bundled services are wired\n")
        worktree = self.page(".claude/worktrees/one/b.md",
                             "The nineteen bundled services.\n")
        self.page("a.md", "The twenty bundled services.\n")

        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn("twenty — 1 page(s) agree", said)

        code, said = self.gate("--write")
        self.assertEqual(code, 0, said)
        self.assertIn("nineteen bundled services",
                      foreign.read_text(encoding="utf-8"))
        self.assertIn("nineteen bundled services",
                      worktree.read_text(encoding="utf-8"))


class TheStackThisRepositoryDescribes(unittest.TestCase):
    """The committed prose agrees with the stack, read from a copy rather than the wire.

    A suite that reached the network would fail on a runner without one and pass by
    not asking, which is the silence the gate itself refuses. What is asserted here is
    that the tree holds governed sentences at all and that they agree with each other —
    the comparison against the real stack is the workflow's, where the network is.
    """

    def test_every_governed_sentence_in_the_tree_says_the_same_thing(self):
        root = HERE.parent
        pages = check_services.governed(root)
        self.assertTrue(pages, "no page states a bundled-service count")
        stated = {
            said
            for page in pages
            for said in check_services.SENTENCE.findall(
                page.read_text(encoding="utf-8", errors="ignore")
            )
        }
        self.assertEqual(len(stated), 1, f"the tree states {sorted(stated)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
