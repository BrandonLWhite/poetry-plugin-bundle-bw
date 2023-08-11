from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List

if TYPE_CHECKING:
    from pathlib import Path
    from cleo.io.io import IO
    from poetry.poetry import Poetry

from poetry_plugin_bundle.bundlers.bundler import Bundler

class ZipBundler(Bundler):
    name = "zip"

    DEFAULT_FILE_EXCLUSIONS = [
        '**/tests/**'
    ]

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

    @property
    def file_exclusions(self) -> List[str]:
        append_defaults = self._bundle_zip_config.get('append-default-file-exclusions', True)
        custom_exclusions = self._bundle_zip_config.get('file-exclusions', [])
        return self.DEFAULT_FILE_EXCLUSIONS + custom_exclusions if append_defaults else custom_exclusions

    def bundle(self, poetry: Poetry, io: IO) -> bool:
        from pathlib import Path
        from contextlib import ExitStack
        from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
        from tempfile import NamedTemporaryFile, TemporaryDirectory
        from poetry.utils.env import VirtualEnv
        from cleo.io.io import Verbosity

        with TemporaryDirectory() as temp_virtual_env:
            temp_virtual_env_path = Path(temp_virtual_env)

            if not self._bundle_virtualenv(poetry, io, temp_virtual_env_path):
                return False

            zip_src_root_path = VirtualEnv(temp_virtual_env_path).site_packages.path
            project_files = self._get_project_files(poetry, zip_src_root_path)
            if self.strip_binaries:
                self._strip_binaries(io, zip_src_root_path)

            file_paths = self._generate_file_paths(zip_src_root_path)

            with ExitStack() as exit_stack:
                zip_output_file = exit_stack.enter_context(ZipFile(str(self._path), mode='w', compression=ZIP_DEFLATED))

                io.write_line(f'Generating ZIP artifact: {self._path}')

                def add_file(zipfile: ZipFile, file: Path):
                    arcname = file.relative_to(zip_src_root_path)
                    io.write_line(f'Adding {arcname} to {zipfile.filename}', Verbosity.VERBOSE)
                    zipfile.write(str(file), arcname=arcname)

                if self.inner_zip_dependencies:
                    temp_requirements_zip = exit_stack.enter_context(NamedTemporaryFile())
                    with ZipFile(temp_requirements_zip, mode='w', compression=ZIP_DEFLATED) as requirements_zip:
                        for file in file_paths:
                            if file not in project_files:
                                add_file(requirements_zip, file)

                    inner_zip_arcname = '.requirements.zip'
                    io.write_line(f'Adding {inner_zip_arcname} to {zip_output_file.filename}', Verbosity.VERBOSE)
                    zip_output_file.write(temp_requirements_zip.name, arcname=inner_zip_arcname, compress_type=ZIP_STORED)

                    unzip_stub_path = Path(__file__).parent / 'unzip_requirements.py'
                    io.write_line(f'Adding {unzip_stub_path.name} to {zip_output_file.filename}', Verbosity.VERBOSE)
                    zip_output_file.write(str(unzip_stub_path), arcname=unzip_stub_path.name)
                    files_to_add = project_files
                else:
                    files_to_add = file_paths

                for file in files_to_add:
                    add_file(zip_output_file, file)

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

    def _strip_binaries(self, io: IO, root_path: Path):
        import subprocess
        from cleo.io.io import Verbosity
        io.write_line('Stripping binaries')
        for lib_file in root_path.rglob('*.so'):
            if not lib_file.is_file():
                continue
            io.write_line(f'Stripping {lib_file}', Verbosity.VERBOSE)
            subprocess.run(['strip', str(lib_file)])

    def _generate_file_paths(self, root_path: Path) -> Iterator[Path]:
        for file in root_path.rglob('*'):
            if self._is_file_included(file):
                yield file

    def _is_file_included(self, file: Path) -> bool:
        from fnmatch import fnmatchcase
        for pattern in self.file_exclusions:
            # Path.match does not work as expected with "**"" so it is not very useful.
            if fnmatchcase(str(file), pattern):
                return False

        return True
