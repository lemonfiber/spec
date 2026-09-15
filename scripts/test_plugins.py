#!/usr/bin/env python3
"""Coverage tests for the plugin gate — OPS-R67, OPS-R68, OPS-R69, Q-R66.

A gate is worth what it refuses, so most of what follows is a refusal: a registry
that is missing, unreadable or declares nothing; an entry missing a field; a
repository nobody created; a manifest that is absent, unreadable, silent about its
schema, or pinned to a generation that has moved; a proof report that is absent,
unreadable, run against another version, empty, failing or unrun.

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

ENTRY = """schema = 1

[[plugin]]
id = "komga"
repo = "plugin-komga"
manifest = "plugin.toml"
targets = "targets.toml"
report = "proofs.json"
ref = "main"
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

    def manifest(self, schema: int | None = 1) -> None:
        body = "" if schema is None else f"schema_version = {schema}\n"
        (self.plugin / "plugin.toml").write_text(body + '[plugin]\nid = "komga"\n', encoding="utf-8")

    def targets(self, release: str | None = "0.16.0") -> None:
        body = "" if release is None else f'lemonfiber = "{release}"\n'
        (self.plugin / "targets.toml").write_text(body, encoding="utf-8")

    def report(self, **over) -> None:
        body = {"plugin": "komga", "lemonfiber": "0.16.0",
                "proofs": [{"id": "answers", "outcome": "passed"}]}
        body.update(over)
        (self.plugin / "proofs.json").write_text(json.dumps(body), encoding="utf-8")

    def gate(self, version: str = "0.16.0", schema: int = 1, checkout: bool = True):
        argv = ["--version", version, "--schema", str(schema), "--registry", str(self.registry)]
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
        self.report(lemonfiber="0.15.0")
        code, said = self.gate(version="0.15.0")
        self.assertEqual(code, 0, said)
        self.assertIn("1 of 1 ride 0.15.0", said)

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
        code, said = run(["--version", "0.16.0", "--schema", "1",
                          "--registry", str(self.registry), "--checkout", "nope"])
        self.assertEqual(code, 2)
        self.assertIn("wants repo=path", said)

    def test_a_path_outside_the_working_tree_is_refused(self):
        code, said = run(["--version", "0.16.0", "--schema", "1",
                          "--registry", str(self.registry),
                          "--checkout", "plugin-komga=/etc"])
        self.assertEqual(code, 2)
        self.assertIn("escapes the working directory", said)

    def test_a_version_that_is_not_a_version_cannot_answer(self):
        code, said = run(["--version", "0.16", "--schema", "1", "--registry", str(self.registry)])
        self.assertEqual(code, 2)
        self.assertIn("wants X.Y.Z", said)

    # A half-written registry entry.

    def test_an_entry_missing_fields_names_them_together(self):
        self.registry.write_text('schema = 1\n\n[[plugin]]\nid = "komga"\n', encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("komga declares no repo, manifest, targets, report", said)

    def test_an_entry_with_no_id_is_named_by_its_position(self):
        self.registry.write_text('schema = 1\n\n[[plugin]]\nrepo = "x"\n', encoding="utf-8")
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

    def test_an_absent_report_fails(self):
        self.targets()
        self.manifest()
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("has no proof report at", said)

    def test_an_unreadable_report_fails(self):
        self.targets()
        self.manifest()
        (self.plugin / "proofs.json").write_text("{", encoding="utf-8")
        code, said = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("cannot be read", said)

    def test_a_report_run_against_another_version_fails(self):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
