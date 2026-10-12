"""`first-party-image.yml`'s own steps: which event proves and which publishes, how the
manifest's service is run under its posture, and what the pin writes."""

from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
import tomllib
import unittest

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/first-party-image.yml"
IMAGE = "ghcr.io/lemonfiber/door"
DIGEST = "sha256:" + "a" * 64
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")


def step(job: str, named: str) -> str:
    """The `run` of one named step of the workflow."""
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][job]["steps"]
    return next(one for one in steps if one.get("name") == named)["run"]


def embedded(job: str, named: str) -> str:
    """The Python a step runs from its heredoc."""
    run = step(job, named)
    return textwrap.dedent(run.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0])


class Scratch(unittest.TestCase):
    """A directory of its own for each test."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)


class Settle(Scratch):
    """A pull request proves; main publishes `main-<12 hex>`; a train tag publishes itself."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        (self.root / "plugin.toml").write_text('schema_version = 1\n[plugin]\nversion = "0.18.0"\n')
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "c"], cwd=self.root, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.root)], cwd=self.root, check=True)
        self.sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True,
                                  text=True, check=True).stdout.strip()

    def settled(self, event: str, kind: str, ref: str, name: str, image: str = "door") -> tuple[int, dict]:
        output = self.root / ".output"
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": event,
               "GITHUB_SHA": self.sha, "REGISTRY": "ghcr.io/lemonfiber", "IMAGE_NAME": image,
               "DIRECTORY": ".", "KIND": kind, "REF": ref, "NAME": name,
               "TAG_PIN_BRANCH": "release/image-pin", "COMMIT_PIN_BRANCH": "release/image-commit-pin"}
        done = subprocess.run(["bash", "-c", step("settle", "A pull request proves; main and a train tag publish")],
                              cwd=self.root, env=env, capture_output=True, text=True)
        said = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
        return done.returncode, said

    def test_a_pull_request_proves_and_publishes_nothing(self):
        code, said = self.settled("pull_request", "branch", "refs/pull/1/merge", "1/merge")
        self.assertEqual((code, said["mode"], said["tag"], said["pin"]), (0, "prove", "", ""))

    def test_main_publishes_its_commit(self):
        code, said = self.settled("push", "branch", "refs/heads/main", "main")
        self.assertEqual((code, said["mode"], said["tag"], said["image"]),
                         (0, "publish", f"main-{self.sha[:12]}", IMAGE))
        self.assertEqual(said["pin"], "release/image-commit-pin")

    def test_no_other_branch_publishes(self):
        self.assertNotEqual(self.settled("push", "branch", "refs/heads/feature", "feature")[0], 0)

    def test_a_train_tag_publishes_at_the_version_the_manifest_declares(self):
        code, said = self.settled("push", "tag", "refs/tags/v0.18.0", "v0.18.0")
        self.assertEqual((code, said["tag"], said["pin"]), (0, "v0.18.0", "release/image-pin"))
        self.assertNotEqual(self.settled("push", "tag", "refs/tags/v0.19.0", "v0.19.0")[0], 0)
        self.assertNotEqual(self.settled("push", "tag", "refs/tags/v0.18.0-rc1", "v0.18.0-rc1")[0], 0)

    def test_an_image_name_that_is_not_one_is_refused(self):
        for image in ("Door", "door/../x", "-door", ""):
            with self.subTest(image=image):
                self.assertNotEqual(self.settled("pull_request", "branch", "r", "n", image)[0], 0)


class Plan(Scratch):
    """The service running the image is run as the manifest says."""

    def planned(self, manifest: str, files: dict[str, str] | None = None, prepare: str = "") -> tuple[int, dict, str]:
        (self.root / "plugin.toml").write_text(manifest, encoding="utf-8")
        for path, content in (files or {}).items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(content, encoding="utf-8")
        plan = self.root / "run.json"
        env = {"PATH": os.environ["PATH"], "IMAGE": IMAGE, "IMAGE_NAME": "door", "DIRECTORY": str(self.root),
               "PREPARE": prepare, "RUN_PLAN": str(plan), "CONFIG_COPY": str(self.root / "copy")}
        done = subprocess.run(["python3", "-I", "-c", embedded("posture", "How the manifest says it runs")],
                              env=env, capture_output=True, text=True)
        return done.returncode, (json.loads(plan.read_text()) if plan.exists() else {}), done.stdout

    SERVICE = f'''schema_version = 1
[[service]]
id = "door"
image = "{IMAGE}"
port = 8096
user_mode = "uid"
config_path = "/etc/caddy"
config_ro = true
tmpfs = ["/data", "/config"]
health = {{ kind = "tcp", timeout_s = 30 }}
'''

    def test_standard_holds_six_capabilities_and_gains_no_privilege(self):
        code, plan, _ = self.planned(self.SERVICE, {"config/door/Caddyfile": ":8096\n"})
        self.assertEqual(code, 0)
        args = plan["args"]
        added = [args[i + 1] for i, one in enumerate(args) if one == "--cap-add"]
        self.assertEqual(added, ["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID", "KILL"])
        for flag in ("--cap-drop", "no-new-privileges:true", "--pids-limit"):
            self.assertIn(flag, args)
        self.assertNotIn("--read-only", args)
        self.assertIn(f"{self.root / 'copy'}:/etc/caddy:ro", args)
        self.assertEqual(args.count("--tmpfs"), 2)
        self.assertEqual((plan["health"], plan["port"], plan["timeout"]), ("tcp", 8096, 30))
        self.assertEqual((self.root / "copy/Caddyfile").read_text(), ":8096\n")

    def test_confined_holds_nothing_on_a_read_only_root_as_the_operator(self):
        code, plan, _ = self.planned(self.SERVICE.replace('user_mode = "uid"', 'posture = "confined"'))
        self.assertEqual(code, 0)
        self.assertNotIn("--cap-add", plan["args"])
        self.assertIn("--read-only", plan["args"])
        self.assertIn(f"{os.getuid()}:{os.getgid()}", plan["args"])

    def test_constants_and_settings_are_set_and_another_service_is_not(self):
        manifest = self.SERVICE + '''
[service.env]
A = "1"
B = { setting = "door:b", default = "two" }
C = { url_of = "media.serve" }
'''
        code, plan, said = self.planned(manifest)
        self.assertEqual(code, 0)
        self.assertIn("A=1", plan["args"])
        self.assertIn("B=two", plan["args"])
        self.assertFalse(any(one.startswith("C=") for one in plan["args"]))
        self.assertIn("C names another service", said)

    def test_the_service_of_the_plugin_id_says_how_until_one_runs_the_image(self):
        manifest = 'schema_version = 1\n[plugin]\nid = "door"\n' + self.SERVICE.split("\n", 1)[1].replace(IMAGE, "caddy")
        code, plan, said = self.planned(manifest)
        self.assertEqual(code, 0)
        self.assertIn(f"{self.root / 'copy'}:/etc/caddy:ro", plan["args"])
        self.assertEqual((plan["health"], plan["port"]), ("tcp", 8096))
        self.assertIn("so it is run as service door is", said)

    MOUNTED = '\n[[service.mount]]\nfrom = "Caddyfile"\nto = "/etc/caddy/Caddyfile"\nro = true\n'

    def test_a_further_mount_comes_from_the_starting_files(self):
        manifest = self.SERVICE + self.MOUNTED
        code, plan, _ = self.planned(manifest, {"config/door/Caddyfile": ":8080\n"})
        self.assertEqual(code, 0)
        self.assertIn(f"{self.root / 'copy' / 'Caddyfile'}:/etc/caddy/Caddyfile:ro", plan["args"])

    def test_a_mount_the_starting_files_do_not_hold_is_refused(self):
        for source in ("../../etc", "absent"):
            with self.subTest(source=source):
                manifest = self.SERVICE + self.MOUNTED.replace('"Caddyfile"', f'"{source}"')
                self.assertNotEqual(self.planned(manifest, {"config/door/Caddyfile": "x"})[0], 0)

    def test_no_service_yet_is_run_under_standard(self):
        code, plan, said = self.planned('schema_version = 1\n[plugin]\nid = "door"\n')
        self.assertEqual(code, 0)
        self.assertIn("--cap-add", plan["args"])
        self.assertEqual(plan["health"], "container")
        self.assertIn("runs ghcr.io/lemonfiber/door yet", said)

    def test_a_shape_or_an_unknown_posture_or_a_check_with_no_port_is_refused(self):
        for manifest in (self.SERVICE + 'shape = "egress-guard"\n',
                         self.SERVICE.replace('user_mode = "uid"', 'posture = "loose"'),
                         self.SERVICE.replace("port = 8096\n", "")):
            with self.subTest(manifest=manifest[-40:]):
                self.assertNotEqual(self.planned(manifest)[0], 0)

    def test_a_starting_file_that_is_a_link_is_refused(self):
        (self.root / "config/door").mkdir(parents=True)
        os.symlink("/etc/passwd", self.root / "config/door/Caddyfile")
        self.assertNotEqual(self.planned(self.SERVICE)[0], 0)


class Pin(Scratch):
    """The pin sets the digest and tag of every service running the image, and nothing else."""

    MANIFEST = f'''schema_version = 1

[[service]]
id     = "door"
image  = "{IMAGE}"
digest = "sha256:{"0" * 64}"
tag    = "main-000000000000"

[[service]]
id     = "other"
image  = "caddy"
digest = "sha256:{"1" * 64}"
tag    = "2.11.6"
'''

    def pinned(self, manifest: str) -> tuple[int, str, str]:
        held = {"content": base64.b64encode(manifest.encode()).decode(), "sha": "x"}
        (self.root / "held.json").write_text(json.dumps(held))
        done = subprocess.run(["python3", "-I", "-c", embedded("pin", "Put what this tag or commit published on its rolling branch"),
                               IMAGE, DIGEST, "v0.18.0"], cwd=self.root, capture_output=True, text=True)
        written = (self.root / "plugin.toml").read_text() if (self.root / "plugin.toml").exists() else ""
        pinned = (self.root / "pinned").read_text() if (self.root / "pinned").exists() else None
        return done.returncode, pinned, written

    def test_the_running_service_moves_and_the_other_does_not(self):
        code, pinned, written = self.pinned(self.MANIFEST)
        self.assertEqual((code, pinned), (0, "yes"))
        services = {one["id"]: one for one in tomllib.loads(written)["service"]}
        self.assertEqual((services["door"]["digest"], services["door"]["tag"]), (DIGEST, "0.18.0"))
        self.assertEqual(services["other"]["tag"], "2.11.6")
        self.assertIn('digest = "' + DIGEST, written)

    def said(self, manifest: str) -> tuple[int, str]:
        held = {"content": base64.b64encode(manifest.encode()).decode(), "sha": "x"}
        (self.root / "held.json").write_text(json.dumps(held))
        done = subprocess.run(["python3", "-I", "-c", embedded("pin", "Put what this tag or commit published on its rolling branch"),
                               IMAGE, DIGEST, "v0.18.0"], cwd=self.root, capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_a_running_service_without_a_tag_to_move_is_refused(self):
        code, said = self.said(self.MANIFEST.replace('tag    = "main-000000000000"\n', ""))
        self.assertNotEqual(code, 0)
        self.assertIn("does not declare `tag` once", said)
        self.assertFalse((self.root / "plugin.toml").exists())

    def test_a_pin_the_manifest_does_not_read_back_is_refused(self):
        hidden = self.MANIFEST.replace(
            'digest = "sha256:' + "0" * 64 + '"',
            'why = """\ndigest = "not a field"\n"""\n"digest" = "sha256:' + "0" * 64 + '"', 1)
        code, said = self.said(hidden)
        self.assertNotEqual(code, 0)
        self.assertIn("does not run ghcr.io/lemonfiber/door at", said)
        self.assertFalse((self.root / "plugin.toml").exists())

    def test_a_running_service_written_so_the_pin_cannot_move_it_is_refused(self):
        quoted = self.MANIFEST.replace(f'image  = "{IMAGE}"', f"image  = '{IMAGE}'")
        code, _, written = self.pinned(quoted)
        self.assertNotEqual(code, 0)
        self.assertEqual(written, "")

    def test_a_manifest_naming_no_service_of_the_image_pins_nothing(self):
        code, pinned, written = self.pinned(self.MANIFEST.replace(IMAGE, "elsewhere"))
        self.assertEqual((code, pinned, written), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
