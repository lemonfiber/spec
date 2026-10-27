#!/usr/bin/env python3
"""`image_inputs.py`: which push changes what an image is built from, so which commit on
an image repository's `main` publishes it (OPS-R93).

Stdlib unittest. Each case is a git repository of its own; no image is built.
Run:  python3 scripts/test_image_inputs.py
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import image_inputs  # noqa: E402

GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")
DOCKERFILE = """\
# The image.
FROM rust:1@sha256:{zero} AS build
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY --chown=1000:1000 \\
     config/caddy/*.json /etc/caddy/
ADD ["assets/a b", "/opt/"]
ADD https://example.invalid/tool.tgz /opt/
RUN cargo build --release
FROM scratch
COPY --from=build /out /out
""".format(zero="0" * 64)


class Sources(unittest.TestCase):
    """What a `Dockerfile` takes from its build context."""

    def test_copy_and_add_take_their_sources_and_nothing_else(self):
        self.assertEqual(image_inputs.sources(DOCKERFILE),
                         ["Cargo.toml", "Cargo.lock", "src", "config/caddy/*.json", "assets/a b"])

    def test_a_source_takes_itself_what_is_under_it_and_what_its_pattern_matches(self):
        self.assertTrue(image_inputs.taken("src/main.rs", "src"))
        self.assertTrue(image_inputs.taken("src", "./src/"))
        self.assertTrue(image_inputs.taken("config/caddy/a.json", "config/caddy/*.json"))
        self.assertFalse(image_inputs.taken("srcs/main.rs", "src"))
        self.assertFalse(image_inputs.taken("config/caddy/Caddyfile", "config/caddy/*.json"))

    def test_a_last_line_left_continued_is_still_read(self):
        self.assertEqual(image_inputs.sources("FROM scratch\nCOPY one two /to \\"), ["one", "two"])

    def test_the_context_itself_takes_every_path(self):
        for source in (".", "./", "./."):
            with self.subTest(source=source):
                self.assertTrue(image_inputs.taken("README.md", source))


class Pushed(unittest.TestCase):
    """Which push changes what the image is built from."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        self.put("Dockerfile", "FROM scratch\nCOPY bin /bin\n")
        self.put("bin/tool", "v1\n")
        self.put("README.md", "# image\n")
        self.before = self.commit()

    def put(self, relative: str, body: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    def commit(self) -> str:
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "--allow-empty", "-m", "c"], cwd=self.root, check=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                              check=True).stdout.strip()

    def ran(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = image_inputs.main(list(args))
        return code, out.getvalue().strip(), err.getvalue()

    def asked(self, *changed: str, directory: str = ".", before: str = "") -> str:
        for path in changed:
            self.put(path, f"changed {path}\n")
        after = self.commit()
        code, out, _ = self.ran("--before", before or self.before, "--after", after, "--directory", directory)
        self.assertEqual(code, 0)
        return out

    def test_the_dockerfile_its_ignore_and_what_it_copies_are_inputs(self):
        for path in ("Dockerfile", ".dockerignore", "bin/tool", "bin/other"):
            with self.subTest(path=path):
                self.assertEqual(self.asked(path), "yes")

    def test_documents_workflows_and_anything_else_are_not(self):
        self.assertEqual(self.asked("README.md", "AGENTS.md", ".github/workflows/image.yml", "typos.toml"), "no")
        self.assertEqual(self.asked(), "no")

    def test_a_context_in_a_directory_is_read_there(self):
        self.put("door/Dockerfile", "FROM scratch\nCOPY . /\n")
        self.before = self.commit()
        self.assertEqual(self.asked("door/notes.txt", directory="door/"), "yes")
        self.before = self.commit()
        self.assertEqual(self.asked("bin/tool", directory="door"), "no")

    def test_a_commit_before_that_cannot_be_read_publishes(self):
        self.assertEqual(self.asked("README.md", before="0" * 40), "yes")
        self.assertEqual(self.asked("README.md", before="f" * 40), "yes")

    def test_a_commit_after_that_cannot_be_read_fails(self):
        code, _, err = self.ran("--before", self.before, "--after", "f" * 40)
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)

    def test_a_dockerfile_too_large_to_read_fails(self):
        self.put("Dockerfile", "#" * (image_inputs.LIMIT + 1))
        code, _, err = self.ran("--before", self.before, "--after", self.commit())
        self.assertEqual(code, 1)
        self.assertIn("larger than", err)

    def test_a_context_with_no_dockerfile_fails(self):
        code, _, err = self.ran("--before", self.before, "--after", self.commit(), "--directory", "nowhere")
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)


if __name__ == "__main__":
    unittest.main()
