from __future__ import annotations

import shutil
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile
import pytest

from cleo.formatters.style import Style
from cleo.io.buffered_io import BufferedIO
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.puzzle.exceptions import SolverProblemError
from poetry.repositories.repository import Repository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.installation.executor import Executor

from poetry_plugin_bundle.bundlers.zip_bundler import ZipBundler


if TYPE_CHECKING:
    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from poetry.utils.env import VirtualEnv
    from poetry.installation.operations.operation import Operation
    from pytest_mock import MockerFixture


@pytest.fixture()
def io() -> BufferedIO:
    io = BufferedIO()

    io.output.formatter.set_style("success", Style("green", options=["dark"]))
    io.output.formatter.set_style("warning", Style("yellow", options=["dark"]))

    return io


@pytest.fixture()
def poetry(config: Config) -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / "simple_project"
    )
    poetry.set_config(config)

    pool = RepositoryPool()
    repository = Repository("repo")
    repository.add_package(Package("foo", "1.0.0"))
    pool.add_repository(repository)
    poetry.set_pool(pool)

    return poetry


def test_bundler_should_build_zip_file(
    io: BufferedIO, tmpdir: str, poetry: Poetry, mocker: MockerFixture
) -> None:
    shutil.rmtree(tmpdir)

    _execute_operation_orig = Executor._execute_operation

    def mock_execute_operation(self: Executor, operation: Operation, *args, **kwargs):
        if operation.job_type == 'install':
            package_name = operation.package.name
            site_packages = self._env.site_packages

            # If it is the project's wheel being installed from venv_bundler, then let that operation
            # happen as it usually would.  Otherwise we will fake out some files.
            if package_name == poetry.package.name:
                _execute_operation_orig(self, operation)
            else:
                package_dir = Path(package_name)
                site_packages.mkdir(package_dir)
                self._env.site_packages.write_text(package_dir / Path("__init__.py"), "")
                self._env.site_packages.write_text(package_dir / Path("main.py"), "# main.py")

    mocker.patch.object(Executor, "_execute_operation", mock_execute_operation)

    bundler = ZipBundler()
    zip_path = Path(tmpdir) / 'bundle.zip'
    bundler.set_path(zip_path)

    assert bundler.bundle(poetry, io)

    # python_version = ".".join(str(v) for v in sys.version_info[:3])
#     expected = f"""\
#   • Bundling simple-project (1.2.3) into {tmpdir}
#   • Bundling simple-project (1.2.3) into {tmpdir}: Creating a virtual environment using Python {python_version}
#   • Bundling simple-project (1.2.3) into {tmpdir}: Installing dependencies
#   • Bundling simple-project (1.2.3) into {tmpdir}: Installing simple-project (1.2.3)
#   • Bundled simple-project (1.2.3) into {tmpdir}
# """  # noqa: E501
    actual_output = io.fetch_output()
    # assert expected == io.fetch_output()
    assert zip_path.exists()
    zip_file = ZipFile(str(zip_path))
    filenames = set(zip_file.namelist())

    assert "foo/__init__.py" in filenames
    assert "foo/main.py" in filenames
    assert "simple_project/__init__.py" in filenames
    assert "simple_project/main.py" in filenames


# def test_bundler_should_fail_when_installation_fails(
#     io: BufferedIO, tmpdir: str, poetry: Poetry, mocker: MockerFixture
# ) -> None:
#     mocker.patch(
#         "poetry.installation.executor.Executor._do_execute_operation",
#         side_effect=Exception(),
#     )

#     bundler = VenvBundler()
#     bundler.set_path(Path(tmpdir))

#     assert not bundler.bundle(poetry, io)

#     python_version = ".".join(str(v) for v in sys.version_info[:3])
#     expected = f"""\
#   • Bundling simple-project (1.2.3) into {tmpdir}
#   • Bundling simple-project (1.2.3) into {tmpdir}: Removing existing virtual environment
#   • Bundling simple-project (1.2.3) into {tmpdir}: Creating a virtual environment using Python {python_version}
#   • Bundling simple-project (1.2.3) into {tmpdir}: Installing dependencies
#   • Bundling simple-project (1.2.3) into {tmpdir}: Failed at step Installing dependencies
# """  # noqa: E501
#     assert expected == io.fetch_output()


# def test_bundler_should_display_a_warning_for_projects_with_no_module(
#     io: BufferedIO, tmp_venv: VirtualEnv, mocker: MockerFixture, config: Config
# ) -> None:
#     poetry = Factory().create_poetry(
#         Path(__file__).parent.parent / "fixtures" / "simple_project_with_no_module"
#     )
#     poetry.set_config(config)

#     pool = RepositoryPool()
#     repository = Repository("repo")
#     repository.add_package(Package("foo", "1.0.0"))
#     pool.add_repository(repository)
#     poetry.set_pool(pool)

#     mocker.patch("poetry.installation.executor.Executor._execute_operation")

#     bundler = VenvBundler()
#     bundler.set_path(tmp_venv.path)
#     bundler.set_remove(True)

#     assert bundler.bundle(poetry, io)

#     path = str(tmp_venv.path)
#     python_version = ".".join(str(v) for v in sys.version_info[:3])
#     expected = f"""\
#   • Bundling simple-project (1.2.3) into {path}
#   • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
#   • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
#   • Bundling simple-project (1.2.3) into {path}: Installing dependencies
#   • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
#   • Bundled simple-project (1.2.3) into {path}
#   • The root package was not installed because no matching module or package was found.
# """  # noqa: E501
#     assert expected == io.fetch_output()


# def test_bundler_can_filter_dependency_groups(
#     io: BufferedIO, tmpdir: str, poetry: Poetry, mocker: MockerFixture, config: Config
# ) -> None:
#     poetry = Factory().create_poetry(
#         Path(__file__).parent.parent / "fixtures" / "simple_project_with_dev_dep"
#     )
#     poetry.set_config(config)

#     # foo is in the main dependency group
#     # bar is a dev dependency
#     # add a repository for foo but not bar
#     pool = RepositoryPool()
#     repository = Repository("repo")
#     repository.add_package(Package("foo", "1.0.0"))
#     pool.add_repository(repository)
#     poetry.set_pool(pool)

#     mocker.patch("poetry.installation.executor.Executor._execute_operation")

#     bundler = VenvBundler()
#     bundler.set_path(Path(tmpdir))
#     bundler.set_remove(True)

#     # This should fail because there is not repo for bar
#     with pytest.raises(SolverProblemError):
#         assert not bundler.bundle(poetry, io)

#     bundler.set_activated_groups({"main"})
#     io.clear_output()

#     # This succeeds because the dev dependency group is filtered out
#     assert bundler.bundle(poetry, io)

#     path = tmpdir
#     python_version = ".".join(str(v) for v in sys.version_info[:3])
#     expected = f"""\
#   • Bundling simple-project (1.2.3) into {path}
#   • Bundling simple-project (1.2.3) into {path}: Removing existing virtual environment
#   • Bundling simple-project (1.2.3) into {path}: Creating a virtual environment using Python {python_version}
#   • Bundling simple-project (1.2.3) into {path}: Installing dependencies
#   • Bundling simple-project (1.2.3) into {path}: Installing simple-project (1.2.3)
#   • Bundled simple-project (1.2.3) into {path}
# """  # noqa: E501
#     assert expected == io.fetch_output()
