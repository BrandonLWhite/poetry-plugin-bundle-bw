from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from pathlib import Path
    from cleo.io.io import IO
    from poetry.core.semver.version import Version
    from poetry.poetry import Poetry

from .venv_bundler import VenvBundler

# TODO : Should the venv directory be a temp location?  Otherwise, how to specify the zip filename.
class ZipBundler(VenvBundler):
    name = "zip"

    def bundle(self, poetry: Poetry, io: IO) -> bool:
        from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
        from tempfile import NamedTemporaryFile
        from poetry.utils.env import VirtualEnv
        from poetry.core.masonry.builders.builder import Builder
        from pathlib import Path

        if not super().bundle(poetry, io):
            return False

        io.write_line('Start ZIP bundler now!')


        zip_root_path = VirtualEnv(self._path).site_packages.path
        print('zip_root_path', zip_root_path)

        project_files = set()
        for file in Builder(poetry).find_files_to_add():
            venv_sub_path = file.path.relative_to(poetry.file.path.parent)
            venv_file_path = zip_root_path / venv_sub_path
            project_files.add(venv_file_path)

        print('Include files....')
        for file in project_files:
            print(str(file))

        # For now just make the zip file be the same name as the venv path, but with .zip extension
        zip_file_path = self._path.with_suffix('.zip')

        self._strip_shared_libs(zip_root_path)
        file_paths = self._strip_unnecessary_files(zip_root_path)

        with NamedTemporaryFile() as temp_requirements_zip:
            with ZipFile(temp_requirements_zip, mode='w', compression=ZIP_DEFLATED) as requirements_zip:
                for file in file_paths:
                    if file not in project_files:
                        requirements_zip.write(str(file), arcname=file.relative_to(zip_root_path))
                    else:
                        print(f'Not writing to zip: {file}')

            with ZipFile(str(zip_file_path), mode='w', compression=ZIP_DEFLATED) as zip_file:
                zip_file.write(temp_requirements_zip.name, arcname='.requirements.zip', compress_type=ZIP_STORED)
                unzip_stub_path = Path(__file__).parent / 'unzip_requirements.py'
                zip_file.write(str(unzip_stub_path), arcname=unzip_stub_path.name)
                for file in project_files:
                    zip_file.write(str(file), arcname=file.relative_to(zip_root_path))

        return True

    def _strip_shared_libs(self, root_path: Path):
        import subprocess

        # TODO : Add config flag to suppress the strip.
        # recursive iterate all .so files.
        for lib_file in root_path.rglob('*.so'):
            if not lib_file.is_file():
                continue
            # print(f'Stripping "{lib_file}"...')
            subprocess.run(['strip', str(lib_file)])

    # TODO Change to generator
    def _strip_unnecessary_files(self, root_path: Path) -> List[Path]:
        included_files = []
        for file in root_path.rglob('*'):
            if self._is_file_included(file):
                included_files.append(file)
        return included_files

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
