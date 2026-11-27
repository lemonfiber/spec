#!/usr/bin/env python3
"""`upstream_pins.py` and the `upstream-pins` and `upstream-pin` workflows: which tag is
taken, what moves and on which branch, what the pull request says, and what rides along.

Stdlib unittest and PyYAML. No registry is asked and no container is run.
Run:  python3 scripts/test_upstream_pins.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

import yaml

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pin_bump  # noqa: E402
import upstream_pins  # noqa: E402

WORKFLOWS = SCRIPTS.parent / ".github/workflows"
DIGEST, LATER = "sha256:" + "a" * 64, "sha256:" + "b" * 64
OLD = "sha256:" + "0" * 64
BOTH = {("linux", "amd64"), ("linux", "arm64")}
AMD64 = {("linux", "amd64")}
UNPACKERR_NEXT = "release-0.15.2"
SONARR_BUILD, SONARR_NEXT_BUILD = "4.0.20.3014-ls326", "4.0.21.3020-ls327"
IMAGE = "lscr.io/linuxserver/sonarr"
GUARDED_BODY = "only the runner may read this"
MOVE = {
    "image": "lscr.io/linuxserver/sonarr",
    "services": ["sonarr"],
    "branch": "upstream-pin/sonarr",
    "from": {"tag": SONARR_BUILD, "digest": OLD},
    "to": {"tag": SONARR_NEXT_BUILD, "digest": DIGEST},
    "proofs": {"moved": [], "held": []},
}
MANIFEST = f'''schema_version = 1

[[service]]
id     = "sonarr"
image  = "lscr.io/linuxserver/sonarr"
digest = "{OLD}"
tag    = "{SONARR_BUILD}"

[[service]]
id     = "sonarr-adapter"
image  = "ghcr.io/lemonfiber/sonarr-adapter"
digest = "{OLD}"
tag    = "main-000000000000"
'''


class Choice(unittest.TestCase):
    """Which tag is taken from a registry's list, and how a tag is read."""

    PUBLISHED = (
        "latest",
        "4.0.15",
        "4.0.20",
        "4.0.21-develop",
        "4.0.20.3014-ls300",
        "5.0.0",
        "v3.41.3",
        "3.99.0",
        "10.11.11",
        "12.1",
        "12.0-rc7",
        UNPACKERR_NEXT,
        "release-1.0.0",
        "V3.1.4",
        "V4.0.0",
        "0.64.2",
        "0.65.0",
        SONARR_BUILD,
        SONARR_NEXT_BUILD,
        "5.0.0.4000-ls1",
        "4.0.21.3020",
        "5.2.4_v2.0.15-ls479",
        "5.2.5_v2.0.15-ls480",
        "5.2.5-libtorrentv1",
        "1.6.3-ls370",
    )

    def test_the_newest_tag_of_the_spelling_and_major_is_taken(self):
        for current, wanted in (
            ("4.0.15", "4.0.20"),
            ("v3.40.0", "v3.41.3"),
            ("10.10.3", "10.11.11"),
            ("release-0.14.5", UNPACKERR_NEXT),
            ("V3.0.4", "V3.1.4"),
            ("0.64.0", "0.65.0"),
            ("4.0.20", "4.0.20"),
            ("12.1", "12.1"),
            ("nightly", "nightly"),
            (SONARR_BUILD, SONARR_NEXT_BUILD),
            ("4.0.20.3014-ls400", SONARR_NEXT_BUILD),
            ("5.2.4_v2.0.15-ls479", "5.2.5_v2.0.15-ls480"),
            ("v1.6.2-ls366", "v1.6.2-ls366"),
        ):
            with self.subTest(current=current):
                self.assertEqual(upstream_pins.newest_in_major(current, list(self.PUBLISHED)), wanted)

    def test_the_tags_of_the_spelling_and_major_are_read_newest_first_ending_with_the_pin(self):
        self.assertEqual(
            upstream_pins.in_major("4.0.15", ["4.0.16", "4.0.20", "5.0.0", "4.0.14", "4.0.15", "4.0"]),
            ["4.0.20", "4.0.16", "4.0.15"],
        )
        self.assertEqual(upstream_pins.in_major("nightly", ["4.0.20"]), ["nightly"])

    def test_a_later_build_of_the_same_release_is_taken(self):
        self.assertEqual(
            upstream_pins.newest_in_major("4.0.20.3014-ls300", [SONARR_BUILD, "4.0.20.3014"]), SONARR_BUILD
        )

    def test_a_tag_is_read_as_prefix_numbers_and_suffix(self):
        for tag, wanted in (
            ("v3.40.0", ("v", (3, 40, 0), "")),
            ("4.5.5.1234-ls200", ("", (4, 5, 5, 1234), "-ls200")),
            ("12.0-rc7", ("", (12, 0), "-rc7")),
            ("1.2.", ("", (1, 2), ".")),
            (UNPACKERR_NEXT, ("release-", (0, 15, 2), "")),
            ("latest", None),
        ):
            with self.subTest(tag=tag):
                self.assertEqual(upstream_pins.version_of(tag), wanted)

    def test_only_lemonfibers_own_images_are_left_to_their_releases(self):
        for image, wanted in (
            ("ghcr.io/lemonfiber/door", False),
            ("ghcr.io/lemonfiber-x/y", True),
            ("ghcr.io/seerr-team/seerr", True),
        ):
            with self.subTest(image=image):
                self.assertEqual(upstream_pins.upstream(image), wanted)


class Registry:
    """A registry answering from a table, as `registry.tags` and `registry.resolve` do."""

    def __init__(self, tags=None, resolved=None):
        self.listed = tags or {}
        self.resolved = resolved or {}

    def tags(self, image):
        return self.listed.get(image, ([], f"{image} unknown"))

    def resolve(self, image, tag):
        return self.resolved.get((image, tag), ("", set(), f"{tag} unknown"))


class Planning(unittest.TestCase):
    """What moves, on which branch, and what is named rather than moved."""

    def registry(self, **answers) -> Registry:
        fake = Registry(**answers)
        patched = mock.patch.multiple(upstream_pins.registry, tags=fake.tags, resolve=fake.resolve)
        patched.start()
        self.addCleanup(patched.stop)
        return fake

    def manifest(self, text: str = MANIFEST) -> dict:
        return upstream_pins.tomllib.loads(text)

    def test_an_upstream_image_moves_on_a_branch_named_after_its_service_and_lemonfibers_does_not(self):
        image = "lscr.io/linuxserver/sonarr"
        self.registry(
            tags={image: ([SONARR_NEXT_BUILD], "")}, resolved={(image, SONARR_NEXT_BUILD): (DIGEST, BOTH, "")}
        )
        moves, problems, skipped = upstream_pins.plan(self.manifest())
        self.assertEqual((problems, skipped), ([], []))
        self.assertEqual(
            moves,
            [
                {
                    "image": image,
                    "services": ["sonarr"],
                    "branch": "upstream-pin/sonarr",
                    "from": {"tag": SONARR_BUILD, "digest": OLD},
                    "to": {"tag": SONARR_NEXT_BUILD, "digest": DIGEST},
                }
            ],
        )

    def test_a_rebuild_under_the_same_tag_moves_and_an_unchanged_pin_does_not(self):
        image = "lscr.io/linuxserver/sonarr"
        self.registry(tags={image: ([SONARR_BUILD], "")}, resolved={(image, SONARR_BUILD): (LATER, BOTH, "")})
        moves, _, _ = upstream_pins.plan(self.manifest())
        self.assertEqual(moves[0]["to"], {"tag": SONARR_BUILD, "digest": LATER})
        self.registry(tags={image: ([SONARR_BUILD], "")}, resolved={(image, SONARR_BUILD): (OLD, BOTH, "")})
        self.assertEqual(upstream_pins.plan(self.manifest()), ([], [], []))

    def test_what_could_not_be_read_or_taken_is_named_and_not_moved(self):
        image = "lscr.io/linuxserver/sonarr"
        for answers, said in (
            ({}, "its tags could not be listed"),
            ({"tags": {image: ([SONARR_NEXT_BUILD], "")}}, "could not be resolved"),
            (
                {
                    "tags": {image: ([SONARR_NEXT_BUILD], "")},
                    "resolved": {
                        (image, SONARR_NEXT_BUILD): (DIGEST, AMD64, ""),
                        (image, SONARR_BUILD): (OLD, AMD64, ""),
                    },
                },
                f"no tag from {SONARR_BUILD} on publishes every platform, so it stays",
            ),
        ):
            with self.subTest(said=said):
                self.registry(**answers)
                moves, problems, _ = upstream_pins.plan(self.manifest())
                self.assertEqual(moves, [])
                self.assertIn(said, problems[0])

    def test_a_newer_tag_publishing_too_few_platforms_is_passed_over_and_named(self):
        image = "lscr.io/linuxserver/sonarr"
        between = "4.0.20.3020-ls327"
        self.registry(
            tags={image: ([SONARR_BUILD, between, SONARR_NEXT_BUILD], "")},
            resolved={
                (image, SONARR_NEXT_BUILD): (DIGEST, AMD64, ""),
                (image, between): (LATER, BOTH, ""),
            },
        )
        moves, problems, skipped = upstream_pins.plan(self.manifest())
        self.assertEqual(problems, [])
        self.assertEqual(moves[0]["to"], {"tag": between, "digest": LATER})
        self.assertEqual(
            skipped,
            [f"{image}: {SONARR_NEXT_BUILD} does not publish linux/arm64, so it is not taken (F2-R6)"],
        )

    def test_a_pin_stays_where_only_newer_tags_publish_too_few_platforms(self):
        image = "lscr.io/linuxserver/sonarr"
        self.registry(
            tags={image: ([SONARR_NEXT_BUILD], "")},
            resolved={
                (image, SONARR_NEXT_BUILD): (DIGEST, AMD64, ""),
                (image, SONARR_BUILD): (OLD, BOTH, ""),
            },
        )
        moves, problems, skipped = upstream_pins.plan(self.manifest())
        self.assertEqual((moves, problems), ([], []))
        self.assertEqual(len(skipped), 1)
        self.assertIn(SONARR_NEXT_BUILD, skipped[0])

    def test_services_pinned_apart_or_a_service_id_that_names_no_branch_are_not_moved(self):
        apart = (
            MANIFEST
            + f'\n[[service]]\nid = "again"\nimage = "lscr.io/linuxserver/sonarr"\ndigest = "{LATER}"\ntag = "4"\n'
        )
        self.registry()
        twice = (
            apart
            + '\n[[service]]\nid = "third"\nimage = "lscr.io/linuxserver/sonarr"\ndigest = "x"\ntag = "5"\n'
        )
        self.assertEqual(
            upstream_pins.plan(self.manifest(twice)),
            ([], ["lscr.io/linuxserver/sonarr: its services are pinned apart, so it is moved by hand"], []),
        )
        moves, problems, _ = upstream_pins.plan(
            self.manifest(MANIFEST.replace('id     = "sonarr"', 'id     = "Sonarr!"'))
        )
        self.assertEqual(moves, [])
        self.assertIn("is not a service id", problems[0])

    def test_only_the_image_asked_for_is_read_or_named(self):
        fake = self.registry()
        apart = (
            MANIFEST
            + f'\n[[service]]\nid = "again"\nimage = "lscr.io/linuxserver/sonarr"\ndigest = "{LATER}"\ntag = "4"\n'
        )
        for text in (MANIFEST, apart):
            moves, problems, _ = upstream_pins.plan(self.manifest(text), "elsewhere")
            self.assertEqual((moves, problems, fake.listed), ([], [], {}))


class Described(unittest.TestCase):
    """What the pull request says, and whether it may merge itself, from what the
    committing job read itself."""

    LOG = "https://github.com/lemonfiber/plugin-sonarr/actions/runs/1"

    def test_a_bump_leaving_no_recording_behind_names_the_release_and_may_merge(self):
        title, body, clean = upstream_pins.described(MOVE, [], self.LOG)
        self.assertEqual(title, f"chore(pins): sonarr {SONARR_BUILD} -> {SONARR_NEXT_BUILD}")
        self.assertTrue(clean)
        self.assertIn("newest release in the major", body)
        self.assertIn("recorded again from it by `lemonfiber plugin record`", body)
        self.assertTrue(body.endswith(f"{upstream_pins.CITED}\n{pin_bump.SIGNED}"))
        self.assertNotIn("not armed", body)

    def test_a_rebuild_says_so(self):
        rebuilt = {**MOVE, "to": {"tag": SONARR_BUILD, "digest": DIGEST}}
        title, body, _ = upstream_pins.described(rebuilt, [], self.LOG)
        self.assertEqual(title, f"chore(pins): sonarr {SONARR_BUILD} rebuilt")
        self.assertIn("published again", body)

    def test_a_recording_left_naming_the_old_image_keeps_it_open_and_names_each(self):
        left = [f"recordings/sonarr/{n}.json" for n in range(pin_bump.STALE_LISTED + 2)]
        _, body, clean = upstream_pins.described(MOVE, left, self.LOG)
        self.assertFalse(clean)
        self.assertIn(f"the record job's log says why: {self.LOG}", body)
        self.assertIn("- `recordings/sonarr/0.json`", body)
        self.assertIn("- and 2 more", body)
        self.assertIn("not armed to merge", body)


class InDirectory(unittest.TestCase):
    """A working directory of its own, as every workflow step has, and a secret-looking
    file outside it that nothing may read."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.outside = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(shutil.rmtree, self.outside, True)
        self.guarded = self.outside / "guarded-file"
        self.guarded.write_text(GUARDED_BODY)
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)

    def put(self, relative: str, body) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body if isinstance(body, str) else json.dumps(body))
        return path


JELLYFIN = f'''schema_version = 1

[[service]]
id     = "jellyfin"
image  = "docker.io/jellyfin/jellyfin"
digest = "{OLD}"
tag    = "10.11.11"

[[service]]
id     = "jellyfin-adapter"
image  = "ghcr.io/lemonfiber/jellyfin-adapter"
digest = "{OLD}"
tag    = "main-000000000000"
speaks = ["identity.source@1", "../escape@1"]
fronts = "jellyfin"

[[proof]]
id      = "jellyfin.identifies"
service = "jellyfin"
fixture = "fixtures/system-info-public.json"
'''
JELLYFIN_IMAGE = "docker.io/jellyfin/jellyfin"
SONARR_MANIFEST = (
    MANIFEST
    + """
[[claim]]
capability = "library.curate"

[[claim.probe]]
id      = "wanted"
fixture = "recordings/sonarr/library-curate-wanted.json"
"""
)


class Staged(InDirectory):
    """What the job that ran the image hands on, and what the job holding the token admits."""

    def setUp(self):
        super().setUp()
        self.answer(SONARR_NEXT_BUILD, DIGEST)

    def answer(self, tag: str, digest: str, published: list[str] | None = None) -> None:
        """The registry the token job asks, as it answers now."""
        fake = Registry(
            tags={IMAGE: (published or [tag], ""), JELLYFIN_IMAGE: (["10.11.12"], "")},
            resolved={(IMAGE, tag): (digest, BOTH, ""), (JELLYFIN_IMAGE, "10.11.12"): (DIGEST, BOTH, "")},
        )
        patched = mock.patch.multiple(upstream_pins.registry, tags=fake.tags, resolve=fake.resolve)
        patched.start()
        self.addCleanup(patched.stop)

    def staged(self, manifest: str, image: str, recordings: dict[str, str]) -> tuple[dict, list[str]]:
        """A plugin whose pin moved and was recorded again, staged as `record` stages it."""
        self.put("plugin/plugin.toml", manifest)
        self.put("main.toml", manifest)
        move = {
            "image": image,
            "to": {"tag": "10.11.12" if image == JELLYFIN_IMAGE else SONARR_NEXT_BUILD, "digest": DIGEST},
        }
        written, _ = upstream_pins.plugin_pin.pinned(manifest, image, move["to"]["tag"], DIGEST)
        self.put("plugin/plugin.toml", written)
        self.put("plugin/proofs.json", {"proofs": []})
        for relative, digest in recordings.items():
            self.put(f"plugin/{relative}", {"recorded_from": f"{image}@{digest}"})
        staged = pin_bump.stage(self.root / "plugin", manifest, move, self.root / "bump")
        return move, staged

    def admit(self, manifest: str, image: str) -> tuple[dict, dict]:
        return upstream_pins.admitted(manifest, image, self.root / "bump")

    def test_the_manifest_proofs_and_new_recordings_travel_and_nothing_else(self):
        _, staged = self.staged(
            SONARR_MANIFEST,
            IMAGE,
            {
                "recordings/sonarr/library-curate-wanted.json": DIGEST,
                "recordings/sonarr/unnamed.json": DIGEST,
            },
        )
        self.assertEqual(
            staged, ["plugin.toml", "proofs.json", "recordings/sonarr/library-curate-wanted.json"]
        )
        move, files = self.admit(SONARR_MANIFEST, IMAGE)
        self.assertEqual(move["branch"], "upstream-pin/sonarr")
        self.assertEqual(move["from"], {"tag": SONARR_BUILD, "digest": OLD})
        self.assertEqual(
            sorted(files), ["plugin.toml", "proofs.json", "recordings/sonarr/library-curate-wanted.json"]
        )

    def test_a_recording_still_of_the_old_pin_stays_behind(self):
        _, staged = self.staged(SONARR_MANIFEST, IMAGE, {"recordings/sonarr/library-curate-wanted.json": OLD})
        self.assertNotIn("recordings/sonarr/library-curate-wanted.json", staged)

    def test_jellyfins_fixtures_and_conformance_cases_travel(self):
        _, staged = self.staged(
            JELLYFIN,
            JELLYFIN_IMAGE,
            {
                "fixtures/system-info-public.json": DIGEST,
                "conformance/identity.source@1/create_admin-answers.json": DIGEST,
                "conformance/identity.source@1/Not A Case.json": DIGEST,
            },
        )
        self.assertIn("conformance/identity.source@1/create_admin-answers.json", staged)
        self.assertIn("fixtures/system-info-public.json", staged)
        self.assertNotIn("conformance/identity.source@1/Not A Case.json", staged)
        self.assertEqual(len(self.admit(JELLYFIN, JELLYFIN_IMAGE)[1]), 4)
        self.assertEqual(upstream_pins.artifact_of(JELLYFIN, JELLYFIN_IMAGE), "upstream-pin-jellyfin")

    def refused(self, why: str, manifest: str = SONARR_MANIFEST, image: str = IMAGE) -> None:
        with self.assertRaisesRegex(upstream_pins.Refused, why):
            self.admit(manifest, image)

    def test_an_extra_path_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {"recordings/sonarr/library-curate-wanted.json": DIGEST})
        self.put("bump/.github/workflows/evil.yml", "on: push")
        self.refused(r"\.github/workflows/evil\.yml is not a recording the manifest names")

    def test_a_fixture_main_names_outside_the_recordings_shape_is_refused(self):
        for fixture in (".github/workflows/evil.yml", ".github/evil.json", "notes.txt"):
            with self.subTest(fixture=fixture):
                shutil.rmtree(self.root / "bump", True)
                named = SONARR_MANIFEST.replace("recordings/sonarr/library-curate-wanted.json", fixture)
                self.staged(named, IMAGE, {})
                self.put(f"bump/{fixture}", {"recorded_from": f"{IMAGE}@{DIGEST}"})
                self.refused("is not a recording the manifest names", manifest=named)

    def test_a_changed_line_outside_the_block_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {})
        bumped = (self.root / "bump/plugin.toml").read_text()
        self.put(
            "bump/plugin.toml", bumped.replace('capability = "library.curate"', 'capability = "anything"')
        )
        self.refused("is not main's with .* and nothing else")

    def test_a_recording_naming_another_digest_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {"recordings/sonarr/library-curate-wanted.json": DIGEST})
        self.put("bump/recordings/sonarr/library-curate-wanted.json", {"recorded_from": f"{IMAGE}@{LATER}"})
        self.refused("is not a recording taken from")

    def test_a_manifest_or_recording_that_is_a_link_to_a_secret_is_refused_with_nothing_read(self):
        for relative in ("plugin.toml", "recordings/sonarr/library-curate-wanted.json"):
            with self.subTest(relative=relative):
                shutil.rmtree(self.root / "bump", True)
                self.staged(SONARR_MANIFEST, IMAGE, {"recordings/sonarr/library-curate-wanted.json": DIGEST})
                (self.root / "bump" / relative).unlink()
                os.symlink(self.guarded, self.root / "bump" / relative)
                self.guarded.chmod(0)
                try:
                    self.refused(f"not a plain file: {re.escape(relative)}")
                finally:
                    self.guarded.chmod(0o600)

    def test_the_pin_is_what_the_registry_answers_now_never_what_the_bump_says(self):
        for answer, why in (
            ((SONARR_NEXT_BUILD, LATER), "is not main's with .* moved to"),
            (
                ("4.0.22.3030-ls328", DIGEST, [SONARR_BUILD, "4.0.22.3030-ls328"]),
                "moved to 4.0.22.3030-ls328",
            ),
            ((SONARR_BUILD, OLD), "moves .* nowhere now"),
        ):
            with self.subTest(answer=answer):
                shutil.rmtree(self.root / "bump", True)
                self.answer(SONARR_NEXT_BUILD, DIGEST)
                self.staged(SONARR_MANIFEST, IMAGE, {"recordings/sonarr/library-curate-wanted.json": DIGEST})
                self.answer(*answer)
                self.refused(why)

    def test_a_bump_naming_a_tag_outside_the_major_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {})
        outside, _ = upstream_pins.plugin_pin.pinned(SONARR_MANIFEST, IMAGE, "5.0.0.4000-ls1", DIGEST)
        self.put("bump/plugin.toml", outside)
        self.refused("is not main's with .* moved to 4.0.21.3020-ls327")

    def test_a_bump_that_is_not_one_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {})
        self.put("bump/proofs.json", ["no"])
        self.refused("is not a report")
        (self.root / "bump/plugin.toml").unlink()
        self.refused("holds no plugin.toml")

    def test_an_image_main_does_not_run_at_one_pin_or_names_no_branch_is_refused(self):
        self.staged(SONARR_MANIFEST, IMAGE, {})
        self.refused("moves elsewhere nowhere now", image="elsewhere")
        unnamed = SONARR_MANIFEST.replace('id     = "sonarr"', 'id     = "Sonarr!"')
        with self.assertRaisesRegex(upstream_pins.Refused, "at no one pin under a service id"):
            upstream_pins.artifact_of(unnamed, IMAGE)


class Main(InDirectory):
    """The command, as each workflow step runs it, from the workspace."""

    def setUp(self):
        super().setUp()
        self.put("plugin.toml", MANIFEST)
        self.output = self.root / "output"
        patched = mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(self.output)})
        patched.start()
        self.addCleanup(patched.stop)

    def ran(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = upstream_pins.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def answering(self, tag: str, digest: str, problem: str = ""):
        fake = Registry(tags={IMAGE: ([tag], problem)}, resolved={(IMAGE, tag): (digest, BOTH, "")})
        patched = mock.patch.multiple(upstream_pins.registry, tags=fake.tags, resolve=fake.resolve)
        patched.start()
        self.addCleanup(patched.stop)

    def test_plan_prints_the_moves_and_the_problems(self):
        self.answering(SONARR_NEXT_BUILD, DIGEST)
        code, out, _ = self.ran("plan", "--manifest", "plugin.toml")
        self.assertEqual(code, 0)
        self.assertEqual([move["branch"] for move in json.loads(out)["moves"]], ["upstream-pin/sonarr"])

    def test_apply_moves_the_one_image_through_the_shared_rewrite(self):
        self.answering(SONARR_NEXT_BUILD, DIGEST)
        code, out, _ = self.ran("apply", "--manifest", "./plugin.toml", "--image", IMAGE)
        self.assertEqual((code, json.loads(out)["to"]["digest"]), (0, DIGEST))
        written = (self.root / "plugin.toml").read_text(encoding="utf-8")
        self.assertIn(f'tag    = "{SONARR_NEXT_BUILD}"', written)
        self.assertIn('tag    = "main-000000000000"', written)

    def test_apply_with_nothing_to_move_writes_nothing_and_fails_only_where_it_could_not_read(self):
        self.answering(SONARR_BUILD, OLD)
        self.assertEqual(self.ran("apply", "--manifest", "plugin.toml", "--image", IMAGE)[:2], (0, "null\n"))
        self.answering(SONARR_BUILD, OLD, problem="registry answered 500")
        code, _, err = self.ran("apply", "--manifest", "plugin.toml", "--image", IMAGE)
        self.assertEqual(code, 1)
        self.assertIn(f"::warning::{IMAGE}: its tags could not be listed", err)
        self.assertEqual((self.root / "plugin.toml").read_text(encoding="utf-8"), MANIFEST)

    def test_artifact_names_the_bump_after_its_first_service(self):
        self.assertEqual(
            self.ran("artifact", "--manifest", "plugin.toml", "--image", IMAGE)[:2],
            (0, "name=upstream-pin-sonarr\n"),
        )

    def test_stage_then_admit_carries_the_move_into_another_checkout(self):
        self.answering(SONARR_NEXT_BUILD, DIGEST)
        self.put("main.toml", MANIFEST)
        self.put("move.json", self.ran("apply", "--manifest", "plugin.toml", "--image", IMAGE)[1])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pin_bump.main(
                [
                    "stage",
                    "--manifest",
                    "plugin.toml",
                    "--main",
                    "main.toml",
                    "--move",
                    "move.json",
                    "--out",
                    "scratch/bump",
                ]
            )
        out = out.getvalue()
        self.assertEqual((code, out), (0, "plugin.toml\n"))
        self.put("checkout/plugin.toml", MANIFEST)
        code, out, _ = self.ran(
            "admit",
            "--manifest",
            "checkout/plugin.toml",
            "--image",
            IMAGE,
            "--bump",
            "scratch/bump",
            "--move-out",
            "scratch/move.json",
        )
        self.assertEqual((code, out), (0, "plugin.toml\n"))
        self.assertIn(DIGEST, (self.root / "checkout/plugin.toml").read_text())
        self.assertEqual(
            json.loads((self.root / "scratch/move.json").read_text())["branch"], "upstream-pin/sonarr"
        )

    def test_a_manifest_path_that_names_no_manifest_or_goes_through_a_link_is_refused(self):
        os.symlink(self.root, self.root / "linked")
        for manifest, why in (
            ("main.toml", "is not a plugin.toml"),
            ("linked/plugin.toml", "passes through a link"),
        ):
            with self.subTest(manifest=manifest):
                code, _, err = self.ran("plan", "--manifest", manifest)
                self.assertEqual(code, 1)
                self.assertIn(why, err)

    def test_message_writes_the_commit_and_the_pull_request(self):
        self.put("move.json", MOVE)
        self.put("recordings/sonarr/old.json", {"recorded_from": f"{IMAGE}@{OLD}"})
        code, out, _ = self.ran(
            "message", "--move", "move.json", "--log", "https://x.test/run\x1b[31m", "--root", "."
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith(f"chore(pins): sonarr {SONARR_BUILD} -> {SONARR_NEXT_BUILD}\n\n"))
        self.assertIn("https://x.test/run??31m", out)
        self.assertIn("- `recordings/sonarr/old.json`", out)
        written = self.output.read_text(encoding="utf-8")
        self.assertRegex(written, r"(?m)^clean<<value_[0-9a-f]{32}\nno\nvalue_[0-9a-f]{32}$")
        self.assertIn("title<<", written)

    def test_an_unreadable_file_fails_naming_it(self):
        (self.root / "plugin.toml").unlink()
        code, _, err = self.ran("plan", "--manifest", "plugin.toml")
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)


CONFIGARR_IMAGE = "ghcr.io/raydak-labs/configarr"
CONFIGARR = f"""schema_version = 1

[[service]]
id     = "configarr"
image  = "{CONFIGARR_IMAGE}"
digest = "{OLD}"
tag    = "1.39.2"

# Configarr 1.39.2 prints its release first.
[[proof]]
id      = "configarr.version"
run     = {{ args = ["sh", "-c", "node index.js | grep -o 'Configarr Version: v[0-9.]*'"] }}
expect  = {{ exit = 0, stdout_starts_with = "Configarr Version: v1.39.2\\n" }}
fixture = "recordings/configarr/version.json"
why     = "1.39.2 is the release pinned, and 11.39.2 and 1.39.20 are not it."

[[proof]]
id      = "configarr.reads-its-configuration"
run     = {{ args = ["sh", "-c", "node index.js"] }}
expect  = {{ exit = 0, stdout_starts_with = "Configarr Version: v1.39.2\\nChecking Recyclarr repo\\n" }}
fixture = "recordings/configarr/reads-its-configuration.json"
why     = "It reads the file it is given."
"""
CONFIGARR_MOVE = {
    "image": CONFIGARR_IMAGE,
    "services": ["configarr"],
    "branch": "upstream-pin/configarr",
    "from": {"tag": "1.39.2", "digest": OLD},
    "to": {"tag": "1.40.0", "digest": DIGEST},
}
TRAEFIK_IMAGE = "docker.io/library/traefik"
TRAEFIK = f"""schema_version = 1

[[service]]
id     = "traefik"
image  = "{TRAEFIK_IMAGE}"
digest = "{OLD}"
tag    = "v3.7.19"

[[service]]
id     = "traefik-adapter"
image  = "ghcr.io/lemonfiber/traefik-adapter"
digest = "{OLD}"
tag    = "main-000000000000"
fronts = "traefik"

[[proof]]
id      = "traefik.version"
service = "traefik"
run     = {{ args = ["traefik", "version"] }}
expect  = {{ exit = 0, stdout_starts_with = "Version:      3.7.19\\n" }}

[[proof]]
id      = "traefik-adapter.serves"
service = "traefik-adapter"
request = {{ method = "GET", path = "/" }}
expect  = {{ status = 200, body_starts_with = "fronting 3.7.19" }}

[[proof]]
id      = "traefik.longer"
service = "traefik"
request = {{ method = "GET", path = "/" }}
expect  = {{ status = 200, body_starts_with = "13.7.19 and 1.3.7.19 and 3.7.190 and 3.7.19.1" }}
"""
TRAEFIK_MOVE = {
    "image": TRAEFIK_IMAGE,
    "services": ["traefik"],
    "branch": "upstream-pin/traefik",
    "from": {"tag": "v3.7.19", "digest": OLD},
    "to": {"tag": "v3.8.0", "digest": DIGEST},
}


class ReleaseText(unittest.TestCase):
    """The release a proof expects moves with the pin, in its expectation and nowhere else."""

    def moved(self, manifest: str, move: dict) -> tuple[str, dict]:
        return upstream_pins.moved_manifest(manifest, move)

    def changed_lines(self, before: str, after: str) -> list[tuple[str, str]]:
        return [
            (one, two) for one, two in zip(before.splitlines(), after.splitlines(), strict=True) if one != two
        ]

    def test_a_tag_names_its_dotted_numbers_as_written(self):
        for tag, release in (
            ("1.39.2", "1.39.2"),
            ("v3.8.0", "3.8.0"),
            ("4.0.21.3020-ls327", "4.0.21.3020"),
            ("release-0.15.2", "0.15.2"),
            ("2024.01.05", "2024.01.05"),
            ("latest", ""),
        ):
            with self.subTest(tag=tag):
                self.assertEqual(upstream_pins.release_of(tag), release)

    def test_the_expected_release_moves_with_the_pin_whether_the_tag_or_the_output_writes_a_v(self):
        for manifest, move, lines in (
            (
                CONFIGARR,
                CONFIGARR_MOVE,
                [
                    'expect  = { exit = 0, stdout_starts_with = "Configarr Version: v1.40.0\\n" }',
                    'expect  = { exit = 0, stdout_starts_with = "Configarr Version: v1.40.0\\nChecking Recyclarr repo\\n" }',
                ],
            ),
            (
                TRAEFIK,
                TRAEFIK_MOVE,
                ['expect  = { exit = 0, stdout_starts_with = "Version:      3.8.0\\n" }'],
            ),
        ):
            with self.subTest(image=move["image"]):
                pinned, _ = upstream_pins.plugin_pin.pinned(
                    manifest, move["image"], move["to"]["tag"], DIGEST
                )
                written, moved = self.moved(manifest, move)
                self.assertEqual([after for _, after in self.changed_lines(pinned, written)], lines)
                self.assertEqual(moved["proofs"]["held"], [])
                self.assertEqual(len(moved["proofs"]["moved"]), len(lines))

    def test_a_comment_prose_a_longer_number_and_another_service_s_proof_keep_the_old_release(self):
        written, moved = self.moved(CONFIGARR, CONFIGARR_MOVE)
        self.assertIn("# Configarr 1.39.2 prints its release first.", written)
        self.assertIn(
            'why     = "1.39.2 is the release pinned, and 11.39.2 and 1.39.20 are not it."', written
        )
        self.assertEqual(moved["proofs"]["moved"], ["configarr.version", "configarr.reads-its-configuration"])
        written, moved = self.moved(TRAEFIK, TRAEFIK_MOVE)
        self.assertIn('body_starts_with = "fronting 3.7.19"', written)
        self.assertIn('body_starts_with = "13.7.19 and 1.3.7.19 and 3.7.190 and 3.7.19.1"', written)
        self.assertEqual(moved["proofs"], {"moved": ["traefik.version"], "held": []})

    def test_a_rebuild_or_a_tag_naming_no_release_moves_no_expectation(self):
        for to in ("1.39.2", "latest"):
            with self.subTest(to=to):
                move = {**CONFIGARR_MOVE, "to": {"tag": to, "digest": DIGEST}}
                pinned, _ = upstream_pins.plugin_pin.pinned(CONFIGARR, CONFIGARR_IMAGE, to, DIGEST)
                self.assertEqual(
                    self.moved(CONFIGARR, move), (pinned, {**move, "proofs": {"moved": [], "held": []}})
                )

    def test_an_expectation_naming_the_release_twice_or_only_through_an_escape_is_left_and_named(self):
        for old, new in (
            ('"Configarr Version: v1.39.2\\n" }', '"Configarr Version: v1.39.2 (1.39.2)\\n" }'),
            ('"Configarr Version: v1.39.2\\n" }', '"Configarr Version: v\\u0031.39.2\\n" }'),
        ):
            with self.subTest(new=new):
                manifest = CONFIGARR.replace(old, new)
                pinned, _ = upstream_pins.plugin_pin.pinned(manifest, CONFIGARR_IMAGE, "1.40.0", DIGEST)
                written, moved = self.moved(manifest, CONFIGARR_MOVE)
                self.assertIn(new, written)
                self.assertEqual(len(self.changed_lines(pinned, written)), 1)
                self.assertEqual(
                    moved["proofs"],
                    {"moved": ["configarr.reads-its-configuration"], "held": ["configarr.version"]},
                )

    def test_the_pull_request_names_what_moved_and_is_not_armed_where_one_was_left(self):
        moved = {
            **CONFIGARR_MOVE,
            "proofs": {"moved": ["configarr.version", "configarr.reads-its-configuration"], "held": []},
        }
        _, body, clean = upstream_pins.described(moved, [], "https://x.test/run")
        self.assertTrue(clean)
        self.assertIn(
            "`configarr.version` and `configarr.reads-its-configuration` expect the release 1.40.0 where they "
            "expected 1.39.2.",
            body,
        )
        held = {**CONFIGARR_MOVE, "proofs": {"moved": [], "held": ["configarr.version"]}}
        _, body, clean = upstream_pins.described(held, [], "https://x.test/run")
        self.assertFalse(clean)
        self.assertIn("`configarr.version` names the release 1.39.2 where this does not move it", body)
        self.assertIn("It is left as written, and this is not armed to merge", body)


class StagedRelease(InDirectory):
    """A bump moving the release a proof expects, admitted only as the token job writes it."""

    def setUp(self):
        super().setUp()
        fake = Registry(
            tags={CONFIGARR_IMAGE: (["1.40.0"], "")},
            resolved={(CONFIGARR_IMAGE, "1.40.0"): (DIGEST, BOTH, "")},
        )
        patched = mock.patch.multiple(upstream_pins.registry, tags=fake.tags, resolve=fake.resolve)
        patched.start()
        self.addCleanup(patched.stop)
        self.put("plugin/plugin.toml", CONFIGARR)
        self.put("main.toml", CONFIGARR)
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                upstream_pins.main(["apply", "--manifest", "plugin/plugin.toml", "--image", CONFIGARR_IMAGE]),
                0,
            )
        self.move = json.loads(out.getvalue())
        self.put("plugin/proofs.json", {"proofs": []})
        pin_bump.stage(self.root / "plugin", CONFIGARR, self.move, self.root / "bump")

    def test_apply_writes_the_release_the_proofs_expect_and_admit_takes_exactly_that(self):
        self.assertEqual(
            self.move["proofs"]["moved"], ["configarr.version", "configarr.reads-its-configuration"]
        )
        move, files = upstream_pins.admitted(CONFIGARR, CONFIGARR_IMAGE, self.root / "bump")
        self.assertEqual(move["proofs"], self.move["proofs"])
        self.assertIn(b'stdout_starts_with = "Configarr Version: v1.40.0\\n"', files["plugin.toml"])

    def test_a_bump_moving_the_release_anywhere_else_or_not_at_all_is_refused(self):
        staged = (self.root / "bump/plugin.toml").read_text()
        pinned, _ = upstream_pins.plugin_pin.pinned(CONFIGARR, CONFIGARR_IMAGE, "1.40.0", DIGEST)
        for written in (
            staged.replace("# Configarr 1.39.2", "# Configarr 1.40.0"),
            staged.replace('why     = "1.39.2 is', 'why     = "1.40.0 is'),
            pinned,
        ):
            with self.subTest(written=written):
                self.put("bump/plugin.toml", written)
                with self.assertRaisesRegex(upstream_pins.Refused, "is not main's with .* and nothing else"):
                    upstream_pins.admitted(CONFIGARR, CONFIGARR_IMAGE, self.root / "bump")


def steps(workflow: str, job: str) -> list[dict]:
    return yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))["jobs"][job]["steps"]


def run_of(workflow: str, job: str, named: str) -> str:
    return next(one for one in steps(workflow, job) if one.get("name") == named)["run"]


def embedded(workflow: str, job: str, named: str) -> str:
    """The Python a step runs from its heredoc."""
    return textwrap.dedent(run_of(workflow, job, named).split("<<'PY'\n", 1)[1].split("\nPY", 1)[0])


class Workflows(unittest.TestCase):
    """The steps around the script, run as the runner runs them."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.output, self.summary = self.root / ".output", self.root / ".summary"

    def env(self, **more: str) -> dict[str, str]:
        return {
            "PATH": os.environ["PATH"],
            "HOME": str(self.root),
            "GITHUB_OUTPUT": str(self.output),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            **more,
        }

    def test_the_plan_hands_on_each_image_and_counts_what_it_could_not_read(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"moves": [{**MOVE}], "problems": ["x: unread"]}))
        subprocess.run(
            [
                "python3",
                "-c",
                embedded("upstream-pins.yml", "plan", "Which upstream pins would move"),
                str(plan),
            ],
            cwd=self.root,
            env=self.env(),
            check=True,
        )
        self.assertEqual(self.output.read_text(), 'images=["lscr.io/linuxserver/sonarr"]\nproblems=1\n')
        self.assertIn("not read: x: unread", self.summary.read_text())

    def test_a_clean_bump_is_armed_and_any_other_disarmed(self):
        called = yaml.safe_load((WORKFLOWS / "upstream-pin.yml").read_text())["jobs"]["pull-request"]["with"]
        self.assertEqual(called["auto-merge"], "${{ needs.commit.outputs.clean == 'yes' }}")
        self.assertEqual(called["disarm"], "${{ needs.commit.outputs.clean != 'yes' }}")


if __name__ == "__main__":
    unittest.main()
