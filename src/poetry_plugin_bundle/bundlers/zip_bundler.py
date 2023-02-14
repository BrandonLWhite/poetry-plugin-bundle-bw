from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from pathlib import Path
    from cleo.io.io import IO
    from poetry.core.semver.version import Version
    from poetry.poetry import Poetry

from poetry_plugin_bundle.bundlers.bundler import Bundler

# TODO:
# - Config for strip patterns
# - Unit tests!
# - Improve CLI normal operational messages
# - Improve CLI command help/info text.
# - Debug-level output
class ZipBundler(Bundler):
    name = "zip"

    def __init__(self) -> None:
        self._path: Path
        self._executable: str | None = None
        self._activated_groups: set[str] | None = None
        self._bundle_zip_config: dict = {}

    def set_path(self, path: Path) -> ZipBundler:
        self._path = path

        return self

    def set_executable(self, executable: str) -> ZipBundler:
        self._executable = executable

        return self

    def set_activated_groups(self, activated_groups: set[str]) -> ZipBundler:
        self._activated_groups = activated_groups

        return self

    def set_zip_config(self, bundle_zip_config: dict) -> ZipBundler:
        self._bundle_zip_config = bundle_zip_config

        return self

    @property
    def strip_binaries(self) -> bool:
        return self._bundle_zip_config.get('strip-binaries', False)

    @property
    def inner_zip_dependencies(self) -> bool:
        return self._bundle_zip_config.get('inner-zip-dependencies', False)

    def bundle(self, poetry: Poetry, io: IO) -> bool:
        from pathlib import Path
        from contextlib import ExitStack
        from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
        from tempfile import NamedTemporaryFile, TemporaryDirectory
        from poetry.utils.env import VirtualEnv

        with TemporaryDirectory() as temp_virtual_env:
            temp_virtual_env_path = Path(temp_virtual_env)

            if not self._bundle_virtualenv(poetry, io, temp_virtual_env_path):
                return False

            zip_src_root_path = VirtualEnv(temp_virtual_env_path).site_packages.path
            # print('zip_root_path', zip_root_path)

            project_files = self._get_project_files(poetry, zip_src_root_path)

            # print('Include files....')
            # for file in project_files:
            #     print(str(file))

            if self.strip_binaries:
                self._strip_binaries(zip_src_root_path)

            file_paths = self._generate_file_paths(zip_src_root_path)

            with ExitStack() as exit_stack:
                zip_output_file = exit_stack.enter_context(ZipFile(str(self._path), mode='w', compression=ZIP_DEFLATED))

                if self.inner_zip_dependencies:
                    temp_requirements_zip = exit_stack.enter_context(NamedTemporaryFile())
                    with ZipFile(temp_requirements_zip, mode='w', compression=ZIP_DEFLATED) as requirements_zip:
                        for file in file_paths:
                            if file not in project_files:
                                requirements_zip.write(str(file), arcname=file.relative_to(zip_src_root_path))
                    zip_output_file.write(temp_requirements_zip.name, arcname='.requirements.zip', compress_type=ZIP_STORED)
                    unzip_stub_path = Path(__file__).parent / 'unzip_requirements.py'
                    zip_output_file.write(str(unzip_stub_path), arcname=unzip_stub_path.name)
                    files_to_add = project_files
                else:
                    files_to_add = file_paths

                for file in files_to_add:
                    zip_output_file.write(str(file), arcname=file.relative_to(zip_src_root_path))

        return True

    def _bundle_virtualenv(self, poetry: Poetry, io: IO, virtual_env_path: Path) -> bool:
        from .venv_bundler import VenvBundler

        venv_bundler = VenvBundler()

        venv_bundler.set_path(virtual_env_path)
        venv_bundler.set_executable(self._executable)
        venv_bundler.set_activated_groups(self._activated_groups)

        return venv_bundler.bundle(poetry, io)

    def _get_project_files(self, poetry: Poetry, root_path: Path) -> set:
        from poetry.core.masonry.builders.builder import Builder

        return {
            root_path / file.path.relative_to(poetry.file.path.parent)
            for file in Builder(poetry).find_files_to_add()
        }

    def _strip_binaries(self, root_path: Path):
        import subprocess

        for lib_file in root_path.rglob('*.so'):
            if not lib_file.is_file():
                continue
            # print(f'Stripping "{lib_file}"...')
            subprocess.run(['strip', str(lib_file)])

    def _generate_file_paths(self, root_path: Path) -> Iterator[Path]:
        for file in root_path.rglob('*'):
            if self._is_file_included(file):
                yield file

    def _is_file_included(self, file: Path) -> bool:
        exclude = [
            '**/__pycache__*',
            '**/*.py[c|o]',
            '**/tests/'
        ]
        for pattern in exclude:
            if file.match(pattern):
                # print(f'Exclude "{file}"')
                return False
        return True
