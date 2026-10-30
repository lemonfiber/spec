#!/usr/bin/env python3
"""Coverage tests for which step of the train a run is on and the submodules a tag
embeds — train_step and submodule_pins. They share the workspace and the in-process
runner of `test_release_train.py` and the train images of `test_release_images.py`.

Run:  python3 scripts/test_train_step.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import submodule_pins  # noqa: E402
import train_step  # noqa: E402
from test_release_images import TrainImages  # noqa: E402
from test_release_train import Workspace, run_main  # noqa: E402


class TrainStepTests(TrainImages):
    """Which step a run is on, read from the repositories — ADR-0033 §4."""

    def stream(self, name, tagged=()):
        """A remote for `name`, holding `tagged`, and its clone under checkouts/."""
        self.repo(f"remotes/{name}", trailer="Spec: B1-R4")
        for tag in tagged:
            subprocess.run(
                ["git", "-C", f"remotes/{name}", "-c", "tag.gpgsign=false", "tag", tag],
                check=True,
                capture_output=True,
            )
        subprocess.run(
            ["git", "clone", "-q", f"remotes/{name}", f"checkouts/{name}"], check=True, capture_output=True
        )

    def step(self, version="0.2.0", tag="v0.2.0"):
        out = pathlib.Path(self.tmp, "output")
        out.unlink(missing_ok=True)
        os.environ["GITHUB_OUTPUT"] = str(out)
        code, said = run_main(train_step, ["--version", version, "--tag", tag])
        return (
            code,
            said,
            out.read_text(encoding="utf-8") if out.exists() else "",
            pathlib.Path("tagging.txt").read_text(encoding="utf-8") if code == 0 else "",
            pathlib.Path("declaring.txt").read_text(encoding="utf-8") if code == 0 else "",
        )

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

    def test_a_pre_release_tags_no_image_repository(self):
        """It is a first-party plugin, tagged at the version by the release alone (OPS-R86)."""
        self.stream("lemonfiber-decline")
        self.stream("lf")
        code, _, output, tagging, declaring = self.step(tag="v0.2.0-pre.1")
        self.assertEqual((code, output, tagging, declaring), (0, "step=streams\n", "lf\n", "lf\n"))
        self.assertEqual(self.step()[2], "step=images\n")

    def test_a_plugin_is_tagged_in_the_first_step_beside_the_images(self):
        pathlib.Path("30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lf"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n\n'
            '[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
            encoding="utf-8",
        )
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber-decline", "lf", "plugin-jellyfin"]\n', encoding="utf-8"
        )
        self.stream("lemonfiber-decline", tagged=("v0.2.0",))
        self.stream("plugin-jellyfin")
        self.stream("lf")
        code, _, output, tagging, declaring = self.step()
        self.assertEqual((code, output, tagging), (0, "step=images\n", "plugin-jellyfin\n"))
        self.assertEqual(declaring, "plugin-jellyfin\nlf\n")

    def test_a_pre_release_holds_every_plugin_back(self):
        pathlib.Path("30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lf"\n\n[[repo]]\nname = "lemonfiber-decline"\nservice = "decline"\n\n'
            '[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
            encoding="utf-8",
        )
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber-decline", "lf", "plugin-jellyfin"]\n', encoding="utf-8"
        )
        self.stream("lemonfiber-decline")
        self.stream("plugin-jellyfin")
        self.stream("lf")
        code, _, output, tagging, declaring = self.step(tag="v0.2.0-pre.1")
        self.assertEqual((code, output, tagging, declaring), (0, "step=streams\n", "lf\n", "lf\n"))

    def test_a_version_cutting_the_core_without_its_plugin_settles_no_step(self):
        pathlib.Path("30-repos/repos.toml").write_text(
            '[[repo]]\nname = "lemonfiber"\n\n[[repo]]\nname = "plugin-jellyfin"\nplugin = "jellyfin"\nimage = true\n',
            encoding="utf-8",
        )
        pathlib.Path("70-operations/versions/0.2.0.toml").write_text(
            'version = "0.2.0"\nrepos = ["lemonfiber"]\n', encoding="utf-8"
        )
        code, said = run_main(train_step, ["--version", "0.2.0", "--tag", "v0.2.0"])
        self.assertEqual(code, 1)
        self.assertIn("cuts lemonfiber and not plugin-jellyfin", said)

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
        for repo, tag in (
            ("--upload-pack=x", "v0.2.0"),
            ("..", "v0.2.0"),
            ("lf", "-v0.2.0"),
            ("lf", "v0.2.0 x"),
        ):
            with self.assertRaises(SystemExit) as caught:
                train_step.carries(repo, tag)
            self.assertIn("is not a lookup", str(caught.exception))

    def test_main_refuses_what_it_cannot_settle(self):
        self.assertEqual(self.step(version="0.9.0", tag="v0.9.0")[0], 1)
        self.assertEqual(self.step(tag="v0.2.0-rc.1")[0], 1)


class SubmodulePinsTests(Workspace):
    """Every submodule a tag embeds, named as a manifest pins it — OPS-R35."""

    #: Two submodules, as the core's `.gitmodules` declares them.
    GITMODULES = (
        '[submodule "assets/web"]\n'
        "\tpath = assets/web\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-web.git\n"
        '[submodule "assets/plugins"]\n'
        "\tpath = assets/plugins\n"
        "\turl = https://github.com/lemonfiber/lemonfiber-plugins.git\n"
    )

    def test_a_tag_with_two_submodules_yields_both(self):
        code, out = run_main(submodule_pins, [], stdin=self.GITMODULES)
        self.assertEqual(code, 0)
        self.assertEqual(out, "lemonfiber-web\tassets/web\nlemonfiber-plugins\tassets/plugins\n")

    def test_a_pin_is_named_for_the_repository_not_the_path(self):
        """The basename of the url, and the name a reader can look up."""
        for url in (
            "https://github.com/lemonfiber/lemonfiber-web.git",
            "https://github.com/lemonfiber/lemonfiber-web/",
            "git@github.com:lemonfiber/lemonfiber-web.git",
        ):
            self.assertEqual(submodule_pins.named(url), "lemonfiber-web")

    def test_settings_that_are_not_a_submodule_are_passed_over(self):
        declared = submodule_pins.declared(
            "# a comment\n" + self.GITMODULES + "\tbranch = main\n\tshallow = true\n"
        )
        self.assertEqual(
            declared, [("lemonfiber-web", "assets/web"), ("lemonfiber-plugins", "assets/plugins")]
        )

    def test_a_value_keeps_no_surrounding_whitespace(self):
        """Taken to the end of the line and trimmed here, rather than by a lazy
        pattern closed with a trailing `\\s*$` that backtracks."""
        self.assertEqual(
            submodule_pins.declared(
                '[submodule "assets/web"]\n'
                "  path =   assets/web   \n"
                "  url = https://github.com/lemonfiber/lemonfiber-web.git  \n"
            ),
            [("lemonfiber-web", "assets/web")],
        )

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
