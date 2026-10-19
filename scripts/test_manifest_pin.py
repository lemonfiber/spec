"""`manifest_pin.py` and `manifest-pin.yml`: which rolling branch a pin goes on, what moves,
what the job holding the token admits, and what the pull request says.

Stdlib unittest and PyYAML. No lemonfiber is built and no container is run.
Run:  python3 scripts/test_manifest_pin.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import shutil
import tempfile
import tomllib
import unittest
from typing import ClassVar

import manifest_pin
import pin_bump
import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/manifest-pin.yml"
IMAGE = "ghcr.io/lemonfiber/door"
DIGEST, OLD, LATER = "sha256:" + "a" * 64, "sha256:" + "0" * 64, "sha256:" + "b" * 64
RECORDING = "recordings/door/answers.json"
MANIFEST = f'''schema_version = 1

[[service]]
id     = "door"
image  = "{IMAGE}"
digest = "{OLD}"
tag    = "main-000000000000"

[[service]]
id     = "other"
image  = "caddy"
digest = "sha256:{"1" * 64}"
tag    = "2.11.6"

[[proof]]
id      = "door.answers"
fixture = "{RECORDING}"
'''
LOG = "https://github.com/lemonfiber/plugin-door/actions/runs/1"


class Moved(unittest.TestCase):
    """Every service running the image moves to what was published, on the branch its
    kind of publish has."""

    def test_main_pins_its_commit_tag_on_the_commit_branch(self):
        written, move = manifest_pin.moved(MANIFEST, IMAGE, "main-0123456789ab", DIGEST, "branch")
        self.assertEqual(move, {"image": IMAGE, "services": ["door"], "branch": "release/image-commit-pin",
                                "published": "main-0123456789ab",
                                "to": {"tag": "main-0123456789ab", "digest": DIGEST}})
        services = {one["id"]: one for one in tomllib.loads(written)["service"]}
        self.assertEqual((services["door"]["digest"], services["door"]["tag"]), (DIGEST, "main-0123456789ab"))
        self.assertEqual(services["other"]["tag"], "2.11.6")

    def test_a_train_tag_pins_without_its_v_on_the_tag_branch(self):
        _, move = manifest_pin.moved(MANIFEST, IMAGE, "v0.18.0", DIGEST, "tag")
        self.assertEqual((move["branch"], move["published"], move["to"]["tag"]),
                         ("release/image-pin", "v0.18.0", "0.18.0"))

    def test_a_manifest_running_no_service_of_the_image_moves_nothing(self):
        self.assertEqual(manifest_pin.moved(MANIFEST, f"{IMAGE}-x", "v0.18.0", DIGEST, "tag"), (MANIFEST, None))

    def test_an_image_lemonfiber_does_not_publish_or_another_kind_of_ref_is_refused(self):
        for image, ref_type, said in (("caddy", "tag", "not an image lemonfiber publishes"),
                                      (IMAGE, "pull", "publishes no pin")):
            with self.subTest(image=image, ref_type=ref_type), self.assertRaisesRegex(manifest_pin.Refused, said):
                manifest_pin.moved(MANIFEST, image, "v0.18.0", DIGEST, ref_type)


class Described(unittest.TestCase):
    """What the pull request says, and whether it came out clean, from what the committing
    job read itself."""

    MOVE: ClassVar[dict] = {"image": IMAGE, "services": ["door"], "branch": "release/image-pin",
                            "published": "v0.18.0", "to": {"tag": "0.18.0", "digest": DIGEST}}

    def test_a_pin_leaving_no_recording_behind_names_the_image_and_is_clean(self):
        title, body, clean = manifest_pin.described(self.MOVE, [], LOG)
        self.assertEqual(title, "chore(manifest): the image at v0.18.0")
        self.assertTrue(body.startswith(f"Every service of plugin.toml running {IMAGE} runs the image v0.18.0 "
                                        f"published, at {DIGEST}."))
        self.assertIn("recorded again from it by `lemonfiber plugin record`", body)
        self.assertTrue(body.endswith(f"{manifest_pin.CITED}\n{pin_bump.SIGNED}"))
        self.assertTrue(clean)

    def test_a_recording_left_behind_is_named_and_not_clean(self):
        _, body, clean = manifest_pin.described(self.MOVE, [RECORDING], LOG)
        self.assertFalse(clean)
        self.assertIn(f"- `{RECORDING}`", body)
        self.assertIn(LOG, body)


class Command(unittest.TestCase):
    """Each step's command, from the workspace, through the record job and into the
    checkout the job holding the token makes."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        here = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, here)
        self.put("plugin/plugin.toml", MANIFEST)
        self.put("checkout/plugin.toml", MANIFEST)
        self.output = self.root / "output"
        os.environ["GITHUB_OUTPUT"] = str(self.output)
        self.addCleanup(os.environ.pop, "GITHUB_OUTPUT")

    def put(self, relative: str, body) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body if isinstance(body, str) else json.dumps(body))

    def ran(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = manifest_pin.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def published(self, manifest: str = "plugin/plugin.toml", digest: str = DIGEST) -> tuple[str, ...]:
        return ("--manifest", manifest, "--image", IMAGE, "--tag", "v0.18.0", "--digest", digest,
                "--ref-type", "tag")

    def recorded(self, digest: str = DIGEST) -> None:
        """What the record job does: move the pin, take the recording again, and stage."""
        self.put("main.toml", MANIFEST)
        code, out, _ = self.ran("apply", *self.published(digest=digest))
        self.assertEqual(code, 0)
        self.put("move.json", out)
        self.put(f"plugin/{RECORDING}", {"recorded_from": f"{IMAGE}@{digest}"})
        self.put("plugin/proofs.json", {"proofs": []})
        with contextlib.redirect_stdout(io.StringIO()):
            pin_bump.main(["stage", "--manifest", "plugin/plugin.toml", "--main", "main.toml", "--move", "move.json",
                           "--out", "bump"])

    def admit(self) -> tuple[int, str, str]:
        return self.ran("admit", *self.published("checkout/plugin.toml"), "--bump", "bump", "--move-out", "moved.json")

    def test_the_move_travels_into_the_checkout_and_is_said_clean(self):
        self.recorded()
        code, out, _ = self.admit()
        self.assertEqual((code, out.splitlines()), (0, ["plugin.toml", "proofs.json", RECORDING]))
        self.assertIn('tag    = "0.18.0"', (self.root / "checkout/plugin.toml").read_text())
        self.assertEqual(json.loads((self.root / "moved.json").read_text())["branch"], "release/image-pin")
        code, out, _ = self.ran("message", "--move", "moved.json", "--log", LOG, "--root", "checkout")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("chore(manifest): the image at v0.18.0\n\n"))
        self.assertRegex(self.output.read_text(), r"(?m)^clean<<value_[0-9a-f]{32}\nyes\nvalue_[0-9a-f]{32}$")

    def test_a_bump_for_another_digest_than_the_one_published_is_refused(self):
        self.recorded(LATER)
        code, _, err = self.admit()
        self.assertEqual(code, 1)
        self.assertIn("is not main's with", err)
        self.assertNotIn(DIGEST, (self.root / "checkout/plugin.toml").read_text())

    def test_a_recording_still_of_the_old_pin_stays_behind_and_is_named(self):
        self.recorded()
        os.remove(self.root / "bump" / RECORDING)
        self.put(f"checkout/{RECORDING}", {"recorded_from": f"{IMAGE}@{OLD}"})
        self.assertEqual(self.admit()[0], 0)
        _, out, _ = self.ran("message", "--move", "moved.json", "--log", LOG, "--root", "checkout")
        self.assertIn(f"- `{RECORDING}`", out)
        self.assertIn("clean<<", self.output.read_text())
        self.assertRegex(self.output.read_text(), r"(?m)^no$")

    def test_a_main_running_no_service_of_the_image_admits_nothing(self):
        self.recorded()
        self.put("checkout/plugin.toml", MANIFEST.replace(IMAGE, "ghcr.io/lemonfiber/elsewhere"))
        code, _, err = self.admit()
        self.assertEqual(code, 1)
        self.assertIn(f"main's manifest runs no service of {IMAGE}", err)

    def test_apply_with_no_service_of_the_image_writes_nothing_and_one_it_cannot_move_fails(self):
        self.put("plugin/plugin.toml", MANIFEST.replace(IMAGE, "ghcr.io/lemonfiber/elsewhere"))
        self.assertEqual(self.ran("apply", *self.published())[:2], (0, "null\n"))
        broken = MANIFEST.replace('tag    = "main-000000000000"\n', "")
        self.put("plugin/plugin.toml", broken)
        code, _, err = self.ran("apply", *self.published())
        self.assertEqual(code, 1)
        self.assertIn("does not declare `tag` once", err)
        self.assertEqual((self.root / "plugin/plugin.toml").read_text(), broken)


class Workflow(unittest.TestCase):
    """The jobs around the script: both read main, and the pull request is never armed."""

    JOBS = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]

    def test_both_jobs_read_main(self):
        for job in ("record", "commit"):
            with self.subTest(job=job):
                self.assertEqual(self.JOBS[job]["steps"][0]["with"]["ref"], "main")

    def test_the_pull_request_is_disarmed_where_it_is_not_clean_and_never_armed(self):
        called = self.JOBS["pull-request"]["with"]
        self.assertEqual(called["disarm"], "${{ needs.commit.outputs.clean != 'yes' }}")
        self.assertNotIn("auto-merge", called)

    def test_one_run_at_a_time_moves_each_rolling_branch(self):
        self.assertEqual(self.JOBS["commit"]["concurrency"],
                         {"group": "manifest-pin-${{ github.repository }}-${{ github.ref_type }}",
                          "cancel-in-progress": False})


if __name__ == "__main__":
    unittest.main()
