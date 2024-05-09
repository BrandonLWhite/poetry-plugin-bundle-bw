from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from poetry_plugin_bundle.console.commands.bundle.bundle_command import BundleCommand


if TYPE_CHECKING:
    from poetry_plugin_bundle.bundlers.zip_bundler import ZipBundler


class BundleZipCommand(BundleCommand):
    name = "bundle zip"
    description = "Bundle the current project into a ZIP file artifact"

    arguments = [
        argument("path", "The output path for the generated ZIP file.")
    ]

    options = [
        *BundleCommand._group_dependency_options(),
        option(
            "python",
            "p",
            "The Python executable to use to create the virtual environment. "
            "Defaults to the current Python executable",
            flag=False,
            value_required=True,
        )
    ]

    bundler_name = "zip"

    def configure_bundler(self, bundler: ZipBundler) -> None:  # type: ignore[override]
        bundler.set_path(Path(self.argument("path")))
        bundler.set_executable(self.option("python"))
        bundler.set_activated_groups(self.activated_groups)

        tool_config = self.poetry.pyproject.data.get('tool', {})
        bundle_config = tool_config.get('poetry-bundle', {})
        bundle_zip_config = bundle_config.get('zip', {})
        bundler.set_zip_config(bundle_zip_config)