#!/usr/bin/env python3
"""Coverage tests for the plugin gate — OPS-R67, OPS-R68, OPS-R72, Q-R66.

A gate is worth what it refuses, so most of what follows is a refusal: a registry
that is missing, unreadable or declares nothing; an entry missing a field; a
repository nobody created; a manifest that is absent, unreadable, silent about its
schema, or pinned to a generation that has moved; a reader pin that is absent,
incomplete or not a full commit; a reader that was not fetched, writes nothing,
does not finish, or fetches a release of its own rather than proving the
candidate; a proof report that is unreadable, run against another version, empty,
failing or unrun, or that says a proof fails as declared without saying on what
and why.

The pinned reader here is a stand-in that does what the real one does with a
release already in its cache: reads `targets.toml`, finds the binary at
`.lemonfiber/<version>/<build>/lemonfiber`, and writes `proofs.json` naming that
version. What it writes is what the test put in `answer.json`. Each plugin also
carries a reader of its own, which must never run.

The one outcome besides passed that it accepts is failing as declared, and it is
named every time and never counted as passed.

The one that matters most is the repository nobody created, because it is the shape
this codebase keeps finding: the answer is true about what was looked at and silent
about the rest, and silence reads as a pass.

Stdlib unittest, no dependencies. Run:  python3 scripts/test_plugins.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_plugins  # noqa: E402

#: Where a reader sits, in the template and in every plugin.
AT = ".github/reader/reader.py"

PIN = f"""schema = 1

[reader]
repo = "plugin-template"
commit = "{"a" * 40}"
path = "{AT}"
"""

ENTRY = PIN + """
[[plugin]]
id = "komga"
repo = "plugin-komga"
manifest = "plugin.toml"
targets = "targets.toml"
report = "proofs.json"
ref = "main"
"""

#: A plugin's own reader. The gate runs the pinned one, so this never runs; if it
#: did, it would leave a mark and pass whatever it was asked.
OWN = """import pathlib
root = pathlib.Path(__file__).resolve().parents[2]
(root.parent / "own-reader-ran").write_text("yes")
(root / "proofs.json").write_text('{"lemonfiber": "0.16.0", "proofs": [{"id": "x", "outcome": "passed"}]}')
"""

#: The build the candidate is, as the gate is told it.
BUILD = "x86_64-unknown-linux-gnu"

#: What the real reader does once the release is in its cache, and no more: the
#: report names the version `targets.toml` does, holds what `answer.json` says,
#: and the exit is 1 where a proof is neither passed nor failing as declared.
READER = """
import json, pathlib, sys, tomllib
root = pathlib.Path(__file__).resolve().parents[2]
version = tomllib.loads((root / "targets.toml").read_text())["lemonfiber"]
if not list((root / ".lemonfiber" / version).glob("*/lemonfiber")):
    print(f"::error::no release {version} is held")
    sys.exit(1)
report = {"lemonfiber": version, **json.loads((root / "answer.json").read_text())}
(root / "proofs.json").write_text(json.dumps(report))
print("  ok   proof  answers")
held = ("passed", "failing-as-declared")
sys.exit(1 if any(p.get("outcome") not in held for p in report.get("proofs", [])) else 0)
"""


def run(argv: list[str]) -> tuple[int, str]:
    """The gate as CI runs it, with what a maintainer would read."""
    said = io.StringIO()
    argv = ["check_plugins.py", *argv]
    with contextlib.redirect_stdout(said):
        kept, sys.argv = sys.argv, argv
        try:
            code = check_plugins.main()
        except SystemExit as stopped:
            code = stopped.code
        finally:
            sys.argv = kept
    return code, said.getvalue()


class PluginGate(unittest.TestCase):
    def setUp(self) -> None:
        # Run from inside the fixture, because the gate refuses a path outside its
        # working directory — the same guard `gate.py` holds its arguments to.
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.addCleanup(lambda: os.chdir(self.cwd))
        self.registry = pathlib.Path("plugins.toml")
        self.registry.write_text(ENTRY, encoding="utf-8")
        self.plugin = pathlib.Path("plugin-komga")
        self.plugin.mkdir()
        self.candidate = pathlib.Path("lemonfiber")
        self.candidate.write_bytes(b"the candidate")
        self.pinned = pathlib.Path("template") / AT
        self.reader()
        own = self.plugin / AT
        own.parent.mkdir(parents=True)
        own.write_text(OWN, encoding="utf-8")

    def reader(self, body: str | None = READER) -> None:
        """The pinned reader, as the workflow fetched it."""
        if body is None:
            self.pinned.unlink()
            return
        self.pinned.parent.mkdir(parents=True, exist_ok=True)
        self.pinned.write_text(body, encoding="utf-8")

    def manifest(self, schema: int | None = 1) -> None:
        body = "" if schema is None else f"schema_version = {schema}\n"
        (self.plugin / "plugin.toml").write_text(body + '[plugin]\nid = "komga"\n', encoding="utf-8")

    def targets(self, release: str | None = "0.16.0") -> None:
        body = "" if release is None else f'lemonfiber = "{release}"\n'
        (self.plugin / "targets.toml").write_text(body, encoding="utf-8")

    def report(self, **over) -> None:
        """What the reader will write, beside the version it is pointed at."""
        body = {"against": "recordings", "proofs": [{"id": "answers", "outcome": "passed"}]}
        body.update(over)
        (self.plugin / "answer.json").write_text(json.dumps(body), encoding="utf-8")

    def written(self) -> dict:
        return json.loads((self.plugin / "proofs.json").read_text(encoding="utf-8"))

    def gate(self, version: str = "0.16.0", schema: int = 1, checkout: bool = True,
             build: str = BUILD, candidate: str = "lemonfiber"):
        argv = ["--version", version, "--schema", str(schema), "--registry", str(self.registry),
                "--candidate", candidate, "--build", build, "--reader", str(self.pinned)]
        if checkout:
            argv += ["--checkout", f"plugin-komga={self.plugin}"]
        return run(argv)

    # Passing, and the two ways of passing that are different sentences.

    def test_a_registered_plugin_that_validates_passes(self):
        self.manifest()
        self.targets()
        self.report()
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn("1 of 1 ride 0.16.0", said)

    def test_a_release_the_plugin_does_not_target_is_not_gated_on_it(self):
        self.targets()
        code, said = self.gate(version="0.15.0")
        self.assertEqual(code, 0, said)
        self.assertIn("targets 0.16.0; 0.15.0 predates it", said)
        self.assertIn("0 of 1", said)

    def test_what_a_plugin_targets_is_read_from_the_plugin(self):
        # The registry states no version, so a plugin that retargets needs no edit
        # here — and cannot disagree with a second copy of the same fact.
        self.manifest()
        self.targets("0.15.0")
        self.report()
        code, said = self.gate(version="0.15.0")
        self.assertEqual(code, 0, said)
        self.assertIn("1 of 1 ride 0.15.0", said)

    # Proved with the candidate, not read from what the plugin committed.

    def test_a_plugin_targeting_the_last_release_is_proved_against_the_one_being_cut(self):
        """The version being cut is published by the run that cuts it, so no plugin
        can have committed a report naming it. The gate's own run names it."""
        self.manifest()
        self.targets("0.16.0")
        self.report()
        code, said = self.gate(version="0.17.0")
        self.assertEqual(code, 0, said)
        self.assertIn("1 of 1 ride 0.17.0, all proved with the candidate", said)
        self.assertEqual(self.written()["lemonfiber"], "0.17.0")

    def test_the_candidate_is_where_the_reader_keeps_the_release_it_targets(self):
        self.manifest()
        self.targets()
        self.report()
        code, said = self.gate(version="0.17.0")
        self.assertEqual(code, 0, said)
        held = self.plugin / ".lemonfiber" / "0.17.0" / BUILD / "lemonfiber"
        self.assertEqual(held.read_bytes(), b"the candidate")
        self.assertEqual((self.plugin / "targets.toml").read_text(encoding="utf-8"),
                         'lemonfiber = "0.17.0"\n')

    def test_the_committed_report_is_never_read_in_place_of_the_run(self):
        """A reader that writes nothing leaves nothing behind that could pass."""
        self.manifest()
        self.targets()
        (self.plugin / "proofs.json").write_text(
            json.dumps({"lemonfiber": "0.17.0", "proofs": [{"id": "answers", "outcome": "passed"}]}),
            encoding="utf-8")
        self.reader('print("::error::lemonfiber read nothing here: no manifest")\nraise SystemExit(1)\n')
        code, said = self.gate(version="0.17.0")
        self.assertEqual(code, 1)
        self.assertIn("::error::komga's proofs could not be run against the candidate: "
                      "lemonfiber read nothing here: no manifest", said)
        self.assertFalse((self.plugin / "proofs.json").exists())

    def test_what_the_reader_prints_is_shown_and_not_acted_on(self):
        self.manifest()
        self.targets()
        self.reader('print("::error::lemonfiber read nothing here")\nraise SystemExit(1)\n')
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("::group::komga's proofs against the candidate", said)
        lines = said.splitlines()
        stop = next(line for line in lines if line.startswith("::stop-commands::"))
        resume = f"::{stop.removeprefix('::stop-commands::')}::"
        self.assertRegex(resume, r"^::[0-9a-f]{32}::$")
        shown = lines[lines.index(stop) + 1:lines.index(resume)]
        self.assertEqual(shown, ["::error::lemonfiber read nothing here"])
        self.assertEqual(lines[lines.index(resume) + 1], "::endgroup::")

    def test_a_reader_that_dies_is_named_by_its_last_word(self):
        self.manifest()
        self.targets()
        self.reader('import sys\nprint("Traceback", file=sys.stderr)\n'
                    'print("KeyError: \'proofs\'", file=sys.stderr)\nsys.exit(1)\n')
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("could not be run against the candidate: KeyError: 'proofs'", said)

    def test_a_reader_that_says_nothing_is_named_by_its_exit(self):
        self.manifest()
        self.targets()
        self.reader("raise SystemExit(3)\n")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("could not be run against the candidate: it exited 3 and said nothing", said)

    def test_a_reader_that_was_not_fetched_cannot_answer(self):
        self.reader(None)
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("::error::no reader at template/.github/reader/reader.py", said)

    # No code from a registered plugin runs.

    def test_the_plugins_own_reader_never_runs(self):
        self.manifest()
        self.targets()
        self.report()
        (self.plugin / ".github" / "reader" / "json.py").write_text(
            "import pathlib\npathlib.Path('shadow-ran').write_text('yes')\n", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertFalse(pathlib.Path("own-reader-ran").exists())
        self.assertFalse((self.plugin / "shadow-ran").exists())
        self.assertEqual([path.name for path in (self.plugin / ".github").rglob("*")],
                         ["reader", "reader.py"])
        self.assertEqual((self.plugin / AT).read_text(encoding="utf-8"), READER)

    def test_a_harness_that_is_a_link_is_removed_and_not_followed(self):
        """A link left in place would carry the reader to wherever it points."""
        self.manifest()
        self.targets()
        self.report()
        shutil.rmtree(self.plugin / ".github")
        elsewhere = pathlib.Path("elsewhere")
        (elsewhere / "reader").mkdir(parents=True)
        (elsewhere / "reader" / "reader.py").write_text(OWN, encoding="utf-8")
        (self.plugin / ".github").symlink_to(elsewhere.resolve(), target_is_directory=True)
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertFalse((self.plugin / ".github").is_symlink())
        self.assertEqual((elsewhere / "reader" / "reader.py").read_text(encoding="utf-8"), OWN)
        self.assertFalse(pathlib.Path("own-reader-ran").exists())

    def test_a_harness_that_is_a_file_is_replaced(self):
        self.manifest()
        self.targets()
        self.report()
        shutil.rmtree(self.plugin / ".github")
        (self.plugin / ".github").write_text("not a directory", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertEqual((self.plugin / AT).read_text(encoding="utf-8"), READER)

    def test_links_the_plugin_committed_are_replaced_and_not_written_through(self):
        self.manifest()
        self.report()
        outside = pathlib.Path("outside")
        outside.mkdir()
        (outside / "targets.toml").write_text('lemonfiber = "0.16.0"\n', encoding="utf-8")
        (self.plugin / "targets.toml").symlink_to((outside / "targets.toml").resolve())
        (self.plugin / ".lemonfiber").symlink_to(outside.resolve(), target_is_directory=True)
        code, said = self.gate(version="0.17.0")
        self.assertEqual(code, 0, said)
        self.assertEqual((outside / "targets.toml").read_text(encoding="utf-8"), 'lemonfiber = "0.16.0"\n')
        self.assertEqual(sorted(path.name for path in outside.iterdir()), ["targets.toml"])
        self.assertFalse((self.plugin / ".lemonfiber").is_symlink())

    def test_a_cache_the_plugin_committed_is_not_read_as_a_fetch(self):
        self.manifest()
        self.targets()
        self.report()
        stale = self.plugin / ".lemonfiber" / "0.16.0" / "aarch64-apple-darwin" / "lemonfiber"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"committed")
        code, said = self.gate()
        self.assertEqual(code, 0, said)

    def test_a_plugin_with_no_harness_is_still_proved(self):
        self.manifest()
        self.targets()
        self.report()
        shutil.rmtree(self.plugin / ".github")
        code, said = self.gate()
        self.assertEqual(code, 0, said)

    # The reader pin.

    def pin(self, table: str) -> tuple[int, str]:
        head, _, rest = ENTRY.partition("[reader]")
        self.registry.write_text(head + table + rest[rest.index("[[plugin]]"):], encoding="utf-8")
        return self.gate()

    def test_a_registry_pinning_no_reader_cannot_answer(self):
        code, said = self.pin("")
        self.assertEqual(code, 2)
        self.assertIn("pins no [reader]; the gate proves every plugin through one", said)

    def test_a_reader_pin_missing_fields_names_them_together(self):
        code, said = self.pin('[reader]\nrepo = "plugin-template"\ncommit = ""\n\n')
        self.assertEqual(code, 2)
        self.assertIn("[reader] declares no commit, path", said)

    def test_a_reader_pinned_to_a_branch_is_not_pinned(self):
        code, said = self.pin(f'[reader]\nrepo = "plugin-template"\ncommit = "main"\npath = "{AT}"\n\n')
        self.assertEqual(code, 2)
        self.assertIn("[reader] pins 'main', which is not a full commit", said)

    def test_a_reader_path_outside_a_repository_is_refused(self):
        for path in ("/etc/reader.py", "../reader.py", ".github/../../reader.py", "reader.py"):
            with self.subTest(path):
                code, said = self.pin(
                    f'[reader]\nrepo = "plugin-template"\ncommit = "{"a" * 40}"\npath = "{path}"\n\n')
                self.assertEqual(code, 2)
                self.assertIn("is not a file inside a repository", said)

    def test_a_reader_that_fetches_a_release_of_its_own_proved_something_else(self):
        """A reader looking for another build than the one it was handed downloads one."""
        self.manifest()
        self.targets()
        self.report()
        self.reader(
            "import pathlib\n"
            "root = pathlib.Path(__file__).resolve().parents[2]\n"
            "own = root / '.lemonfiber' / '0.16.0' / 'aarch64-apple-darwin' / 'lemonfiber'\n"
            "own.parent.mkdir(parents=True)\n"
            "own.write_bytes(b'published')\n"
            + READER)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn(
            "komga's reader fetched .lemonfiber/0.16.0/aarch64-apple-darwin/lemonfiber rather "
            f"than proving the candidate at .lemonfiber/0.16.0/{BUILD}/lemonfiber", said)

    def test_a_reader_that_does_not_finish_fails(self):
        self.manifest()
        self.targets()
        self.reader("import time\ntime.sleep(30)\n")
        kept = check_plugins.PROOFS_TIMEOUT_S
        check_plugins.PROOFS_TIMEOUT_S = 0.5
        self.addCleanup(setattr, check_plugins, "PROOFS_TIMEOUT_S", kept)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("komga's proofs did not finish within 0.5 seconds", said)

    def test_a_reader_failing_over_a_clean_report_is_not_a_pass(self):
        self.manifest()
        self.targets()
        self.report()
        self.reader(READER.rsplit("sys.exit(", 1)[0] + "sys.exit(2)\n")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("komga's reader exited 2 over a report naming no failure", said)

    def test_a_build_name_that_is_not_a_triple_cannot_answer(self):
        for build in ("../../etc", "linux", "x86_64/unknown-linux-gnu"):
            with self.subTest(build):
                code, said = self.gate(build=build)
                self.assertEqual(code, 2)
                self.assertIn("--build wants a target triple", said)

    def test_a_candidate_that_was_not_built_cannot_answer(self):
        self.candidate.unlink()
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("no candidate build at lemonfiber", said)

    def test_a_candidate_outside_the_working_tree_is_refused(self):
        code, said = self.gate(candidate="/bin/sh")
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", said)

    def test_a_plugin_that_cannot_say_what_it_targets_fails(self):
        self.manifest()
        self.report()
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("has no targets.toml at", said)

    def test_a_targets_file_that_cannot_be_read_fails(self):
        self.manifest()
        (self.plugin / "targets.toml").write_text("lemonfiber = \n", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("cannot be read", said)

    def test_a_targets_file_naming_no_release_fails(self):
        self.manifest()
        self.targets(None)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("names no lemonfiber release", said)

    def test_a_target_that_is_not_a_version_fails(self):
        self.manifest()
        self.targets("0.16")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("targets '0.16', which is not X.Y.Z", said)

    # The silences, each refused by name.

    def test_a_missing_registry_cannot_answer(self):
        self.registry.unlink()
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("no plugin registry", said)

    def test_an_unreadable_registry_cannot_answer(self):
        self.registry.write_text("[[plugin]\n", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("cannot be read", said)

    def test_a_registry_declaring_no_plugin_cannot_answer(self):
        self.registry.write_text("schema = 1\n", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 2)
        self.assertIn("declares no [[plugin]]", said)

    def test_a_repository_nobody_created_fails_by_name(self):
        self.targets()
        code, said = self.gate(checkout=False)
        self.assertEqual(code, 1)
        self.assertIn("plugin-komga", said)
        self.assertIn("not a plugin that passed", said)

    def test_a_checkout_argument_without_an_equals_cannot_answer(self):
        code, said = run(["--version", "0.16.0", "--schema", "1", "--registry", str(self.registry),
                          "--candidate", "lemonfiber", "--build", BUILD, "--reader", str(self.pinned),
                          "--checkout", "nope"])
        self.assertEqual(code, 2)
        self.assertIn("wants repo=path", said)

    def test_a_path_outside_the_working_tree_is_refused(self):
        code, said = run(["--version", "0.16.0", "--schema", "1", "--registry", str(self.registry),
                          "--candidate", "lemonfiber", "--build", BUILD, "--reader", str(self.pinned),
                          "--checkout", "plugin-komga=/etc"])
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", said)

    def test_a_version_that_is_not_a_version_cannot_answer(self):
        code, said = run(["--version", "0.16", "--schema", "1", "--registry", str(self.registry),
                          "--candidate", "lemonfiber", "--build", BUILD, "--reader", str(self.pinned)])
        self.assertEqual(code, 2)
        self.assertIn("wants X.Y.Z", said)

    # A half-written registry entry.

    def test_an_entry_missing_fields_names_them_together(self):
        self.registry.write_text(PIN + '\n[[plugin]]\nid = "komga"\n', encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("komga declares no repo, manifest, targets, report", said)

    def test_an_entry_with_no_id_is_named_by_its_position(self):
        self.registry.write_text(PIN + '\n[[plugin]]\nrepo = "x"\n', encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("entry 0 declares no", said)

    # The manifest.

    def test_an_absent_manifest_fails(self):
        self.targets()
        self.report()
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("has no manifest at", said)

    def test_an_unreadable_manifest_fails(self):
        self.targets()
        (self.plugin / "plugin.toml").write_text("[plugin\n", encoding="utf-8")
        self.report()
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("manifest at", said)
        self.assertIn("cannot be read", said)

    def test_a_manifest_with_no_schema_version_fails(self):
        self.targets()
        self.manifest(schema=None)
        self.report()
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("declares no schema_version", said)

    def test_a_manifest_pinning_a_schema_the_release_does_not_carry_fails(self):
        self.targets()
        self.manifest(schema=1)
        self.report()
        code, said = self.gate(schema=2)
        self.assertEqual(code, 1)
        self.assertIn("this release carries 2", said)

    # The proof report.

    def test_an_unreadable_report_fails(self):
        self.targets()
        self.manifest()
        self.reader("import pathlib\n"
                    "(pathlib.Path(__file__).resolve().parents[2] / 'proofs.json').write_text('{')\n")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof report at", said)
        self.assertIn("cannot be read", said)

    def test_a_report_run_against_another_version_fails(self):
        """A reader that kept its own idea of the release rather than reading the
        `targets.toml` the gate wrote."""
        self.targets()
        self.manifest()
        self.report(lemonfiber="0.15.0")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("run against 0.15.0, not 0.16.0", said)

    def test_a_report_stating_no_version_fails(self):
        self.targets()
        self.manifest()
        self.report(lemonfiber=None)
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("nothing stated", said)

    def test_a_report_naming_no_proof_fails(self):
        self.targets()
        self.manifest()
        self.report(proofs=[])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("names no proof", said)

    def test_a_failing_proof_fails(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "answers", "outcome": "failed"}])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof answers is failed", said)

    def test_an_unrun_proof_is_not_a_passing_one(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "answers", "outcome": "unrun"}])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof answers is unrun", said)

    # Failing as declared: named, not failed on, never passed.

    def as_declared(self, **over) -> dict:
        declaration = {
            "fixture": "fixtures/identity-anonymous.json",
            "constraint": "json",
            "place": "/MediaContainer/claimed",
            "held": "false",
            "reason": "Recorded from a server nobody has claimed.",
        }
        declaration.update(over)
        return {"id": "claimed", "outcome": "failing-as-declared", "declared": [declaration]}

    def test_a_proof_failing_as_declared_is_named_and_does_not_fail_the_run(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "answers", "outcome": "passed"}, self.as_declared()])
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn(
            "::notice::komga's proof claimed fails as declared on "
            "fixtures/identity-anonymous.json: json at /MediaContainer/claimed held false. "
            "Recorded from a server nobody has claimed.",
            said,
        )
        self.assertIn("1 proof(s) fail as declared, named above; none is counted as passed", said)

    def test_a_declaration_about_the_answer_as_a_whole_names_no_place(self):
        self.targets()
        self.manifest()
        declared = self.as_declared(constraint="status", held="500")
        del declared["declared"][0]["place"]
        self.report(proofs=[declared])
        code, said = self.gate()
        self.assertEqual(code, 0, said)
        self.assertIn("identity-anonymous.json: status held 500. Recorded", said)

    def test_a_proof_failing_as_declared_is_still_named_when_the_run_fails(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "answers", "outcome": "failed"}, self.as_declared()])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof answers is failed", said)
        self.assertIn("proof claimed fails as declared", said)
        self.assertNotIn("plugins ok", said)

    def test_failing_as_declared_naming_no_declaration_fails(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "claimed", "outcome": "failing-as-declared"}])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof claimed is failing-as-declared and names no declaration", said)

    def test_a_declaration_that_is_not_a_table_names_everything_it_lacks(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{"id": "claimed", "outcome": "failing-as-declared",
                             "declared": ["fixtures/identity-anonymous.json"]}])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("names no fixture, constraint, held, reason", said)

    def test_failing_as_declared_without_a_reason_fails(self):
        self.targets()
        self.manifest()
        self.report(proofs=[self.as_declared(reason="")])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof claimed is failing-as-declared and its declaration names no reason", said)
        self.assertNotIn("::notice::", said)

    def test_failing_as_declared_without_what_the_answer_held_fails(self):
        self.targets()
        self.manifest()
        declared = self.as_declared()
        del declared["declared"][0]["held"]
        self.report(proofs=[declared])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("its declaration names no held", said)

    def test_a_proof_with_no_outcome_and_no_id_is_still_named(self):
        self.targets()
        self.manifest()
        self.report(proofs=[{}])
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("proof (unnamed) is not stated", said)


class TheRegistryThisRepositoryShips(unittest.TestCase):
    """The committed registry parses and every entry in it is complete.

    A registry whose entries are half-written would be found by the gate on release
    day, which is the wrong day. Read from the repository root the same way CI runs
    the gate, so a moved file fails here rather than reading as an empty list.
    """

    def test_it_parses_and_every_entry_is_complete(self):
        registry = HERE.parent / check_plugins.REGISTRY
        entries = check_plugins.load_registry(registry)
        self.assertTrue(entries, "the committed registry declares no plugin")
        for index, entry in enumerate(entries):
            self.assertEqual(check_plugins.malformed(entry, index), [], entry)

    def test_it_pins_the_templates_reader(self):
        pin = check_plugins.load_reader(HERE.parent / check_plugins.REGISTRY)
        self.assertEqual(pin["repo"], "plugin-template")
        self.assertEqual(pin["path"], AT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
