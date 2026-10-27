"""`first-party-image.yml`'s own steps: which event proves and which publishes, that a push
changing nothing but a pin publishes nothing, and how the manifest's service is run under
its posture."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import unittest

import workflow_steps

TOOLING = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = TOOLING / ".github/workflows/first-party-image.yml"
IMAGE = "ghcr.io/lemonfiber/door"
DIGEST = "sha256:" + "a" * 64
GIT = ("git", "-c", "user.name=test", "-c", "user.email=test@invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null")



def step(job: str, named: str) -> str:
    return workflow_steps.step(WORKFLOW, job, named)


def embedded(job: str, named: str) -> str:
    return workflow_steps.embedded(WORKFLOW, job, named)


class Settle(workflow_steps.Scratch):
    """A pull request proves; main publishes `main-<12 hex>`; a train tag publishes itself."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=self.root, check=True)
        (self.root / "plugin.toml").write_text('schema_version = 1\n[plugin]\nversion = "0.18.0"\n')
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "c"], cwd=self.root, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.root)], cwd=self.root, check=True)
        self.sha = self.head()
        self.before = ""

    def head(self) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def settled(self, event: str, kind: str, ref: str, name: str, image: str = "door",
                pinned_in: str = "") -> tuple[int, dict]:
        output = self.root / ".output"
        output.unlink(missing_ok=True)
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), "GITHUB_EVENT_NAME": event,
               "GITHUB_SHA": self.sha, "REGISTRY": "ghcr.io/lemonfiber", "IMAGE_NAME": image,
               "DIRECTORY": ".", "PINNED_IN": pinned_in, "PINNED": ".pinned",
               "KIND": kind, "REF": ref, "NAME": name, "BEFORE": self.before,
               "TOOLING": str(TOOLING)}
        done = subprocess.run(["bash", "-c", step("settle", "A pull request proves; main and a train tag publish")],
                              cwd=self.root, env=env, capture_output=True, text=True)
        said = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
        return done.returncode, said

    def test_a_pull_request_proves_and_publishes_nothing(self):
        code, said = self.settled("pull_request", "branch", "refs/pull/1/merge", "1/merge")
        self.assertEqual((code, said["mode"], said["tag"]), (0, "prove", ""))

    def test_main_publishes_its_commit(self):
        code, said = self.settled("push", "branch", "refs/heads/main", "main")
        self.assertEqual((code, said["mode"], said["tag"], said["image"]),
                         (0, "publish", f"main-{self.sha[:12]}", IMAGE))

    def test_main_publishes_nothing_from_a_push_changing_nothing_but_a_pin(self):
        for path, mode in (("recordings/door/a.json", "none"), ("Dockerfile", "publish")):
            with self.subTest(path=path):
                self.before = self.head()
                (self.root / path).parent.mkdir(parents=True, exist_ok=True)
                (self.root / path).write_text(path)
                (self.root / "plugin.toml").write_text((self.root / "plugin.toml").read_text() + "# moved\n")
                subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
                subprocess.run([*GIT, "commit", "--quiet", "-m", "after"], cwd=self.root, check=True)
                self.sha = self.head()
                code, said = self.settled("push", "branch", "refs/heads/main", "main")
                self.assertEqual((code, said["mode"]), (0, mode))

    def test_no_other_branch_publishes(self):
        self.assertNotEqual(self.settled("push", "branch", "refs/heads/feature", "feature")[0], 0)

    def test_a_train_tag_publishes_at_the_version_the_manifest_declares(self):
        code, said = self.settled("push", "tag", "refs/tags/v0.18.0", "v0.18.0")
        self.assertEqual((code, said["tag"]), (0, "v0.18.0"))
        self.assertNotEqual(self.settled("push", "tag", "refs/tags/v0.19.0", "v0.19.0")[0], 0)
        self.assertNotEqual(self.settled("push", "tag", "refs/tags/v0.18.0-rc1", "v0.18.0-rc1")[0], 0)

    def test_the_image_is_the_plugins_id_where_none_is_named(self):
        (self.root / "plugin.toml").write_text('schema_version = 1\n[plugin]\nid = "door"\nversion = "0.18.0"\n')
        code, said = self.settled("push", "branch", "refs/heads/main", "main", "")
        self.assertEqual((code, said["image"], said["name"]), (0, IMAGE, "door"))

    def test_an_image_another_plugin_runs_publishes_what_changes_its_inputs_on_main_and_no_tag(self):
        (self.root / ".pinned").mkdir()
        (self.root / ".pinned/plugin.toml").write_text('schema_version = 1\n[plugin]\nid = "caddy"\n')
        (self.root / "Dockerfile").write_text("FROM scratch\nCOPY bin /bin\n")
        subprocess.run(["git", "add", "Dockerfile"], cwd=self.root, check=True)
        subprocess.run([*GIT, "commit", "--quiet", "-m", "image"], cwd=self.root, check=True)
        for path, mode in (("README.md", "none"), ("recordings/a.json", "none"), ("bin/tool", "publish"),
                           ("Dockerfile", "publish")):
            with self.subTest(path=path):
                self.before = self.head()
                (self.root / path).parent.mkdir(parents=True, exist_ok=True)
                (self.root / path).write_text(f"FROM scratch\n# {path}\n")
                subprocess.run(["git", "add", path], cwd=self.root, check=True)
                subprocess.run([*GIT, "commit", "--quiet", "-m", "after"], cwd=self.root, check=True)
                self.sha = self.head()
                code, said = self.settled("push", "branch", "refs/heads/main", "main", "", "plugin-caddy")
                self.assertEqual((code, said["mode"], said["image"]), (0, mode, "ghcr.io/lemonfiber/caddy"))
        self.assertNotEqual(self.settled("push", "tag", "refs/tags/v0.18.0", "v0.18.0", "caddy", "plugin-caddy")[0], 0)
        for named in ("Plugin-Caddy", "plugin/../caddy", "-caddy"):
            with self.subTest(named=named):
                self.assertNotEqual(self.settled("pull_request", "branch", "r", "n", "caddy", named)[0], 0)

    def test_an_image_name_that_is_not_one_is_refused(self):
        for image in ("Door", "door/../x", "-door"):
            with self.subTest(image=image):
                self.assertNotEqual(self.settled("pull_request", "branch", "r", "n", image)[0], 0)


class Plan(workflow_steps.Scratch):
    """The service running the image is run as the manifest says."""

    def planned(self, manifest: str, files: dict[str, str] | None = None, prepare: str = "") -> tuple[int, dict, str]:
        (self.root / "plugin.toml").write_text(manifest, encoding="utf-8")
        for path, content in (files or {}).items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(content, encoding="utf-8")
        plan = self.root / "run.json"
        env = {"PATH": os.environ["PATH"], "IMAGE": IMAGE, "IMAGE_NAME": "door", "MANIFEST": str(self.root),
               "PREPARE": prepare, "RUN_PLAN": str(plan), "CONFIG_COPY": str(self.root / "copy"),
               "MOUNT_TREE": str(self.root / "mounts")}
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
    WRITABLE = '\n[[service.mount]]\nfrom = "data"\nto = "/data"\n\n[[service.mount]]\nfrom = "state/config"\nto = "/config"\n'

    def test_a_writable_mount_is_an_empty_directory_of_its_own_mount_tree(self):
        code, plan, _ = self.planned(self.SERVICE + self.WRITABLE, {"config/door/data/kept": "x"})
        self.assertEqual(code, 0)
        tree = self.root / "mounts/door"
        self.assertIn(f"{tree / 'data'}:/data", plan["args"])
        self.assertIn(f"{tree / 'state/config'}:/config", plan["args"])
        self.assertEqual([*(tree / "data").iterdir(), *(tree / "state/config").iterdir()], [])
        self.assertEqual((self.root / "copy/data/kept").read_text(), "x")

    def test_a_read_only_mount_is_of_its_own_mount_tree_and_left_to_the_engine(self):
        code, plan, said = self.planned(self.SERVICE + self.MOUNTED, {"config/door/Caddyfile": ":8080\n"})
        self.assertEqual(code, 0)
        self.assertIn(f"{self.root / 'mounts/door/Caddyfile'}:/etc/caddy/Caddyfile:ro", plan["args"])
        self.assertFalse((self.root / "mounts/door/Caddyfile").exists())
        self.assertIn("the engine makes it an empty directory", said)

    def test_a_source_outside_its_own_tree_or_inside_another_is_refused(self):
        for source in ("../../etc", "/etc", "a/./b", "a//b", "", "${HOME}", "Caddyfile/inner"):
            with self.subTest(source=source):
                manifest = self.SERVICE + self.MOUNTED + self.MOUNTED.replace('"Caddyfile"', f'"{source}"', 1).replace(
                    "/etc/caddy/Caddyfile", "/elsewhere")
                code, plan, _ = self.planned(manifest)
                self.assertNotEqual(code, 0)
                self.assertEqual(plan, {})

    def test_a_target_a_mount_may_not_land_at_is_refused(self):
        for target, takes_data in (("/", False), ("relative", False), ("/a/../b", False), ("/data/x", True),
                                   ("/etc/caddy/Caddyfile", False)):
            with self.subTest(target=target):
                manifest = self.SERVICE + ("takes_data = true\n" if takes_data else "") + self.MOUNTED + (
                    self.MOUNTED.replace('"Caddyfile"', '"other"', 1).replace("/etc/caddy/Caddyfile", target))
                self.assertNotEqual(self.planned(manifest)[0], 0)

    def test_a_target_in_the_data_mount_is_held_only_where_it_takes_data(self):
        self.assertEqual(self.planned(self.SERVICE + self.WRITABLE)[0], 0)
        self.assertNotEqual(self.planned(self.SERVICE + "takes_data = true\n" + self.WRITABLE)[0], 0)

    def test_posture_prepare_is_run_where_the_plugin_holds_one_and_none_is_named(self):
        self.assertEqual(self.planned(self.SERVICE, {"posture/prepare": "#!/bin/sh\n"})[1]["prepare"], "posture/prepare")
        self.assertEqual(self.planned(self.SERVICE, prepare="other/prepare")[1]["prepare"], "other/prepare")
        (self.root / "posture/prepare").unlink()
        self.assertEqual(self.planned(self.SERVICE)[1]["prepare"], "")

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



class Pinned(unittest.TestCase):
    """An image another plugin runs is proved and pinned against that plugin's manifest."""

    def test_its_manifest_is_that_plugins_and_the_pin_is_moved_there(self):
        import yaml

        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        for job in ("settle", "posture"):
            with self.subTest(job=job):
                checkout = next(step for step in jobs[job]["steps"]
                                if step.get("name") == "The plugin that runs the image, where it is built apart from it")
                self.assertEqual(checkout["if"], "inputs.pinned_in != ''")
                self.assertEqual(checkout["with"]["repository"],
                                 "${{ github.repository_owner }}/${{ inputs.pinned_in }}")
                self.assertEqual(checkout["with"]["ref"], "main")
        self.assertEqual(jobs["pin"]["with"]["repository"], "${{ inputs.pinned_in }}")
        self.assertEqual(jobs["pin"]["with"]["directory"],
                         "${{ inputs.pinned_in != '' && '.' || inputs.directory }}")

if __name__ == "__main__":
    unittest.main()
