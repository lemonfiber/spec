#!/usr/bin/env python3
"""Coverage tests for what a version cuts: the repositories it tags and searches,
the images it builds and the pins it records — manifest_repos, check_image_pins,
train_step and submodule_pins.

They share the workspace and the in-process runner of `test_release_train.py`,
and live apart from it so that suite stays within the size cap.
Run:  python3 scripts/test_release_images.py
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tomllib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_image_pins  # noqa: E402
import manifest_repos  # noqa: E402
import submodule_pins  # noqa: E402
import train_step  # noqa: E402
from test_release_train import Workspace, run_main  # noqa: E402


class ManifestReposTests(Workspace):
    """What a version cuts and where its goals were satisfied — OPS-R58."""

    def toml(self, name, body):
        pathlib.Path(f"70-operations/versions/{name}.toml").write_text(body, encoding="utf-8")

    def test_a_manifest_that_says_nothing_is_searched_where_it_cuts(self):
        """Every manifest written before this existed says nothing, and searching
        none of them would report every goal unmet for a reason that is not true."""
        data = {"repos": ["lf", "ms"]}
        self.assertEqual(manifest_repos.searched(data), ["lf", "ms"])
        self.assertEqual(manifest_repos.cut(data), ["lf", "ms"])

    def test_where_it_says_the_two_lists_are_different_answers(self):
        data = {"repos": ["lf"], "satisfied_in": ["lf", "web"]}
        self.assertEqual(manifest_repos.cut(data), ["lf"], "naming it does not tag it")
        self.assertEqual(manifest_repos.searched(data), ["lf", "web"])

    def test_an_empty_list_is_not_an_instruction_to_search_nowhere(self):
        data = {"repos": ["lf"], "satisfied_in": []}
        self.assertEqual(manifest_repos.searched(data), ["lf"])

    def test_main_prints_each_list_one_per_line(self):
        self.toml("0.2.0", 'version = "0.2.0"\nrepos = ["lf"]\nsatisfied_in = ["lf", "web"]\n')
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "cut"])
        self.assertEqual((code, out), (0, "lf\n"))
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "searched"])
        self.assertEqual((code, out), (0, "lf\nweb\n"))

    def test_main_refuses_what_it_cannot_answer(self):
        self.assertEqual(run_main(manifest_repos, ["--version", "9.9.9", "--for", "cut"])[0], 1)
        with self.assertRaises(SystemExit):
            manifest_repos.manifest_for("not-semver")
        # A version that cuts nothing is a manifest somebody has not finished,
        # said here rather than left for a `while read` over an empty file.
        self.toml("0.3.0", 'version = "0.3.0"\nrepos = []\n')
        self.assertEqual(run_main(manifest_repos, ["--version", "0.3.0", "--for", "cut"])[0], 1)


class ImageReposTests(Workspace):
    """Which streams a version tags before the core, read from the registry — ADR-0033 §4."""

    def setUp(self):
        super().setUp()
        self.registry = {"repo": [{"name": "lf"}, {"name": "lemonfiber-decline", "service": "decline"},
                                  {"name": "lemonfiber-request-gate", "service": "request-gate"}]}

    def write_registry(self, body):
        pathlib.Path("30-repos").mkdir(exist_ok=True)
        pathlib.Path("30-repos/repos.toml").write_text(body, encoding="utf-8")

    def test_a_repository_the_registry_gives_a_service_is_tagged_first(self):
        data = {"repos": ["lf", "lemonfiber-decline", "ms"]}
        self.assertEqual(manifest_repos.images(data, self.registry),
                         [("lemonfiber-decline", "decline", "ghcr.io/lemonfiber/decline")])
        self.assertEqual(manifest_repos.others(data, self.registry), ["lf", "ms"])

    def test_a_service_the_version_does_not_cut_is_not_tagged(self):
        data = {"repos": ["lf"]}
        self.assertEqual(manifest_repos.images(data, self.registry), [])
        self.assertEqual(manifest_repos.others(data, self.registry), ["lf"])

    def test_a_repository_named_against_its_service_is_refused(self):
        """Skipped, it would be cut with the core in one step."""
        with self.assertRaises(SystemExit) as caught:
            manifest_repos.image_repos({"repo": [{"name": "decline-service", "service": "decline"}]})
        self.assertIn("names it lemonfiber-decline", str(caught.exception))

    def test_a_service_that_is_not_a_service_id_is_refused(self):
        """It becomes part of a reference handed to docker."""
        for service in ("Decline", "--output=x", "a--b", "", "decline/x"):
            with self.assertRaises(SystemExit) as caught:
                manifest_repos.image_repos({"repo": [{"name": f"lemonfiber-{service}",
                                                      "service": service}]})
            self.assertIn("is not a service id", str(caught.exception))

    def test_main_prints_both_halves_of_the_cut(self):
        self.write_registry('[[repo]]\nname = "lf"\n\n'
                            '[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n')
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lf", "lemonfiber-decline"]\n', encoding="utf-8")
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "images"])
        self.assertEqual((code, out), (0, "lemonfiber-decline\tdecline\tghcr.io/lemonfiber/decline\n"))
        code, out = run_main(manifest_repos, ["--version", "0.2.0", "--for", "others"])
        self.assertEqual((code, out), (0, "lf\n"))

    def test_an_empty_half_is_an_answer_not_a_refusal(self):
        """Most versions build no image, and the workflow reads an empty list as one step."""
        self.write_registry('[[repo]]\nname = "lf"\n')
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lf"]\n', encoding="utf-8")
        self.assertEqual(run_main(manifest_repos, ["--version", "0.2.0", "--for", "images"]), (0, ""))

    def test_the_registry_this_repository_holds_reads_cleanly(self):
        """Every `service` the real registry gives is one the train can act on."""
        registry = tomllib.loads((HERE.parent / "30-repos/repos.toml").read_text(encoding="utf-8"))
        built = manifest_repos.image_repos(registry)
        self.assertEqual(built, {"lemonfiber-decline": "decline",
                                 "lemonfiber-request-gate": "request-gate"})


class TrainImages(Workspace):
    """A registry building `decline`, a manifest cutting it, and a stubbed registry."""

    DIGEST = "sha256:" + "a" * 64
    OTHER = "sha256:" + "b" * 64

    #: Stands in for `docker buildx imagetools inspect`. Prints DOCKER_REPLY as
    #: the index descriptor, unless the reference is named in DOCKER_MISSING.
    DOCKER = """#!/bin/sh
case " ${DOCKER_MISSING:-} " in *" $4 "*) echo "ERROR: $4: not found" >&2; exit 1 ;; esac
printf '%s' "${DOCKER_REPLY}"
"""

    def setUp(self):
        super().setUp()
        pathlib.Path("30-repos").mkdir()
        pathlib.Path("30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lf"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n',
            encoding="utf-8")
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber-decline", "lf"]\n', encoding="utf-8")
        pathlib.Path("70-operations/versions/0.3.0.toml").write_text(
            'version = "0.3.0"\nrepos = ["lf"]\n', encoding="utf-8")
        bin_dir = pathlib.Path(self.tmp, "bin")
        bin_dir.mkdir()
        (bin_dir / "docker").write_text(self.DOCKER, encoding="utf-8")
        (bin_dir / "docker").chmod(0o755)
        self.saved_env = dict(os.environ)
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        os.environ["DOCKER_REPLY"] = f'{{"mediaType": "index", "digest": "{self.DIGEST}"}}'
        os.environ.pop("GITHUB_OUTPUT", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved_env)
        super().tearDown()


class CheckImagePinsTests(TrainImages):
    """The embedded stack pins each tagged image at its tag and digest — ADR-0033 §4."""

    def stack(self, tag="v0.2.0", digest=TrainImages.DIGEST, image="ghcr.io/lemonfiber/decline"):
        return {"service": [{"id": "sonarr", "image": "lscr.io/linuxserver/sonarr"},
                            {"id": "decline", "image": image, "tag": tag, "digest": digest}]}

    def write_stack(self, tag):
        pathlib.Path("stack.toml").write_text(
            '[[service]]\nid = "decline"\nimage = "ghcr.io/lemonfiber/decline"\n'
            f'tag = "{tag}"\ndigest = "{self.DIGEST}"\n', encoding="utf-8")

    def check(self, tag, version="0.2.0"):
        return run_main(check_image_pins, ["--version", version, "--tag", tag, "--stack", "stack.toml"])

    def test_a_stack_pinning_the_tag_and_its_digest_passes(self):
        self.assertEqual(check_image_pins.problems(self.stack(), "v0.2.0", {"decline": self.DIGEST}), [])

    def test_each_way_a_pin_can_be_wrong_is_named(self):
        said = check_image_pins.problems(
            self.stack(tag="v0.2.0-pre.1", digest=self.OTHER, image="ghcr.io/else/decline"),
            "v0.2.0", {"decline": self.DIGEST})
        self.assertEqual(len(said), 3)
        self.assertIn("image is 'ghcr.io/else/decline'", said[0])
        self.assertIn("not 'v0.2.0'", said[1])
        self.assertIn("ghcr.io/lemonfiber/decline:v0.2.0 published", said[2])

    def test_a_service_declared_other_than_once_is_refused(self):
        self.assertIn("0 times", check_image_pins.problems(
            self.stack(), "v0.2.0", {"request-gate": self.DIGEST})[0])
        twice = self.stack()
        twice["service"].append(dict(twice["service"][1]))
        self.assertIn("2 times", check_image_pins.problems(twice, "v0.2.0", {"decline": self.DIGEST})[0])

    def test_only_a_tag_the_train_cuts_is_one(self):
        for tag in ("v0.2.0", "v0.2.0-pre.1", "v0.2.0-pre.2.a"):
            self.assertTrue(check_image_pins.cut_by_train(tag, "0.2.0"), tag)
        for tag in ("0.2.0", "v0.2", "v0.3.0", "v0.2.0-rc.1", "v0.2.0-", "v0.2.0-pre..1", "v0.2.0 --push"):
            self.assertFalse(check_image_pins.cut_by_train(tag, "0.2.0"), tag)
        self.assertFalse(check_image_pins.cut_by_train("v0.2", "0.2"), "a version is three numbers")

    def test_a_reference_that_is_not_one_never_reaches_docker(self):
        for reference in ("--output=x", "", "ghcr.io/x:v1 --push"):
            self.assertIn("is not a reference", check_image_pins.digest_of(reference)[1])

    def test_a_stack_outside_the_working_directory_is_refused(self):
        code, said = run_main(check_image_pins, ["--version", "0.2.0", "--tag", "v0.2.0",
                                                 "--stack", "/etc/hosts"])
        self.assertEqual(code, 1)
        self.assertIn("path escapes the working directory", said)

    def test_the_registry_is_asked_for_the_index_digest(self):
        self.assertEqual(check_image_pins.digest_of("ghcr.io/lemonfiber/decline:v0.2.0"), (self.DIGEST, ""))

    def test_each_way_the_registry_can_fail_to_answer_is_named(self):
        os.environ["DOCKER_MISSING"] = "ghcr.io/lemonfiber/decline:v0.2.0"
        self.assertIn("is not published (ERROR", check_image_pins.digest_of("ghcr.io/lemonfiber/decline:v0.2.0")[1])
        for reply, said in (("not json", "not a descriptor"), ("[]", "not a descriptor"),
                            ('{"digest": "sha256:short"}', "which is not one")):
            os.environ["DOCKER_REPLY"] = reply
            self.assertIn(said, check_image_pins.digest_of("ghcr.io/lemonfiber/x:v0.2.0")[1])

    def test_main_passes_a_stack_that_pins_the_tag(self):
        self.write_stack("v0.2.0-pre.1")
        code, out = self.check("v0.2.0-pre.1")
        self.assertEqual(code, 0)
        self.assertIn("decline is pinned at v0.2.0-pre.1", out)

    def test_main_refuses_a_stack_still_on_the_pre_release(self):
        """The pre-release's digests are not the release's, so the core waits for the repin."""
        self.write_stack("v0.2.0-pre.1")
        code, out = self.check("v0.2.0")
        self.assertEqual(code, 1)
        self.assertIn("does not pin what v0.2.0 published", out)

    def test_main_refuses_an_image_the_tag_has_not_published(self):
        self.write_stack("v0.2.0")
        os.environ["DOCKER_MISSING"] = "ghcr.io/lemonfiber/decline:v0.2.0"
        code, out = self.check("v0.2.0")
        self.assertEqual(code, 1)
        self.assertIn("ghcr.io/lemonfiber/decline:v0.2.0 is not published", out)

    def test_main_passes_a_version_that_cuts_no_image(self):
        self.assertEqual(self.check("v0.3.0", version="0.3.0"), (0, "0.3.0 cuts no image the stack has to pin.\n"))

    def test_main_refuses_what_it_cannot_read(self):
        self.assertEqual(self.check("v0.2.0")[0], 1, "no stack")
        self.assertEqual(self.check("v0.9.0", version="0.9.0")[0], 1, "no manifest")
        code, said = run_main(check_image_pins, ["--version", "0.2.0", "--tag", "v0.2.0 x", "--stack", "s"])
        self.assertEqual(code, 1)
        self.assertIn("is not a tag the train cuts", said)


class TrainStepTests(TrainImages):
    """Which step a run is on, read from the repositories — ADR-0033 §4."""

    def stream(self, name, tagged=()):
        """A remote for `name`, holding `tagged`, and its clone under checkouts/."""
        self.repo(f"remotes/{name}", trailer="Spec: B1-R4")
        for tag in tagged:
            subprocess.run(["git", "-C", f"remotes/{name}", "-c", "tag.gpgsign=false", "tag", tag],
                           check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", f"remotes/{name}", f"checkouts/{name}"],
                       check=True, capture_output=True)

    def step(self, version="0.2.0", tag="v0.2.0"):
        out = pathlib.Path(self.tmp, "output")
        out.unlink(missing_ok=True)
        os.environ["GITHUB_OUTPUT"] = str(out)
        code, said = run_main(train_step, ["--version", version, "--tag", tag])
        return (code, said, out.read_text(encoding="utf-8") if out.exists() else "",
                pathlib.Path("tagging.txt").read_text(encoding="utf-8") if code == 0 else "",
                pathlib.Path("declaring.txt").read_text(encoding="utf-8") if code == 0 else "")

    def test_an_untagged_image_makes_it_the_first_step(self):
        """The core is not tagged, and still has to declare the version first."""
        self.stream("lemonfiber-decline")
        self.stream("lf")
        code, _, output, tagging, declaring = self.step()
        self.assertEqual((code, output), (0, "step=images\n"))
        self.assertEqual(tagging, "lemonfiber-decline\n")
        self.assertEqual(declaring, "lemonfiber-decline\nlf\n")

    def test_every_image_tagged_makes_it_the_second_step(self):
        """An image already tagged has published, and its main may have moved on."""
        self.stream("lemonfiber-decline", tagged=("v0.2.0",))
        self.stream("lf")
        code, said, output, tagging, declaring = self.step()
        self.assertEqual((code, output), (0, "step=streams\n"))
        self.assertEqual((tagging, declaring), ("lf\n", "lf\n"))
        self.assertIn("tags lf at v0.2.0", said)

    def test_a_pre_release_tag_is_its_own_first_step(self):
        """The image carries the pre-release; the release still has to publish its own."""
        self.stream("lemonfiber-decline", tagged=("v0.2.0-pre.1",))
        self.stream("lf")
        self.assertEqual(self.step()[2], "step=images\n")
        self.assertEqual(self.step(tag="v0.2.0-pre.1")[2], "step=streams\n")

    def test_a_version_cutting_no_image_is_one_step(self):
        self.stream("lf")
        code, _, output, tagging, _ = self.step(version="0.3.0", tag="v0.3.0")
        self.assertEqual((code, output, tagging), (0, "step=streams\n", "lf\n"))

    def test_without_a_runner_output_it_still_says_the_step(self):
        self.stream("lf")
        os.environ.pop("GITHUB_OUTPUT", None)
        code, said = run_main(train_step, ["--version", "0.3.0", "--tag", "v0.3.0"])
        self.assertEqual(code, 0)
        self.assertIn("step=streams", said)

    def test_a_lookup_that_fails_is_a_refusal_not_an_untagged_image(self):
        """Read as untagged, it would publish an image twice under one tag."""
        self.repo("checkouts/lemonfiber-decline")
        with self.assertRaises(SystemExit) as caught:
            train_step.carries("lemonfiber-decline", "v0.2.0")
        self.assertIn("could not ask lemonfiber-decline", str(caught.exception))

    def test_a_lookup_that_is_not_one_never_reaches_git(self):
        for repo, tag in (("--upload-pack=x", "v0.2.0"), ("..", "v0.2.0"), ("lf", "-v0.2.0"),
                          ("lf", "v0.2.0 x")):
            with self.assertRaises(SystemExit) as caught:
                train_step.carries(repo, tag)
            self.assertIn("is not a lookup", str(caught.exception))

    def test_main_refuses_what_it_cannot_settle(self):
        self.assertEqual(self.step(version="0.9.0", tag="v0.9.0")[0], 1)
        self.assertEqual(self.step(tag="v0.2.0-rc.1")[0], 1)


class SubmodulePinsTests(Workspace):
    """Every submodule a tag embeds, named as a manifest pins it — OPS-R35.

    The fixture is `lemonfiber`'s own `.gitmodules` at `v0.10.0`, the release
    whose manifest recorded the stack and said nothing about `assets/web`.
    """

    #: What `v0.10.0` actually declares.
    GITMODULES = (
        '[submodule "assets/media-stack"]\n'
        "\tpath = assets/media-stack\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-media-stack.git\n"
        '[submodule "assets/web"]\n'
        "\tpath = assets/web\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-web.git\n"
    )

    def test_a_tag_with_two_submodules_yields_both(self):
        """The defect: 0.10.0 embeds the stack and the web app, and the manifest
        named only the stack because the workflow named the path it knew."""
        code, out = run_main(submodule_pins, [], stdin=self.GITMODULES)
        self.assertEqual(code, 0)
        self.assertEqual(out, "lemonfiber-media-stack\tassets/media-stack\n"
                              "lemonfiber-web\tassets/web\n")

    def test_a_pin_is_named_for_the_repository_not_the_path(self):
        """`lemonfiber-media-stack`, which is the naming the manifests already
        use — the basename of the url, and the name a reader can look up."""
        for url in ("https://github.com/lemonfiber/lemonfiber-web.git",
                    "https://github.com/lemonfiber/lemonfiber-web/",
                    "git@github.com:lemonfiber/lemonfiber-web.git"):
            self.assertEqual(submodule_pins.named(url), "lemonfiber-web")

    def test_settings_that_are_not_a_submodule_are_passed_over(self):
        declared = submodule_pins.declared(
            "# a comment\n" + self.GITMODULES + "\tbranch = main\n\tshallow = true\n")
        self.assertEqual(declared, [("lemonfiber-media-stack", "assets/media-stack"),
                                    ("lemonfiber-web", "assets/web")])

    def test_a_value_keeps_no_surrounding_whitespace(self):
        """Taken to the end of the line and trimmed here, rather than by a lazy
        pattern closed with a trailing `\\s*$` that backtracks."""
        self.assertEqual(
            submodule_pins.declared('[submodule "assets/web"]\n'
                                    "  path =   assets/web   \n"
                                    "  url = https://github.com/lemonfiber/lemonfiber-web.git  \n"),
            [("lemonfiber-web", "assets/web")])

    def test_a_stanza_missing_half_of_itself_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            submodule_pins.declared('[submodule "assets/web"]\n\tpath = assets/web\n')
        self.assertIn("wants a path and a url", str(caught.exception))

    def test_a_tag_that_declares_nothing_is_refused(self):
        """Recording no pins at all is the failure being fixed, so it is said
        rather than left for a `while read` over an empty file."""
        self.assertEqual(run_main(submodule_pins, [], stdin="")[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
