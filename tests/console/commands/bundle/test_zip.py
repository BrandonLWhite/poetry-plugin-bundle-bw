from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.console.application import Application

from poetry_plugin_bundle.bundlers.zip_bundler import ZipBundler


if TYPE_CHECKING:
    from cleo.testers.application_tester import ApplicationTester
    from pytest_mock import MockerFixture


def test_zip_calls_zip_bundler(
    app_tester: ApplicationTester, mocker: MockerFixture
) -> None:
    mock = mocker.patch(
        "poetry_plugin_bundle.bundlers.zip_bundler.ZipBundler.bundle",
        side_effect=[True, False, False, False],
    )

    set_path = mocker.spy(ZipBundler, "set_path")
    set_executable = mocker.spy(ZipBundler, "set_executable")
    set_activated_groups = mocker.spy(ZipBundler, "set_activated_groups")
    set_zip_config = mocker.spy(ZipBundler, "set_zip_config")

    app_tester.application.catch_exceptions(False)
    assert app_tester.execute("bundle zip /foo") == 0
    assert (
        app_tester.execute("bundle zip /foo --python python3.8 --with dev")
        == 1
    )
    assert app_tester.execute("bundle zip /foo --only dev") == 1
    assert app_tester.execute("bundle zip /foo --without main --with dev") == 1

    assert isinstance(app_tester.application, Application)
    assert [
        mocker.call(app_tester.application.poetry, mocker.ANY),
        mocker.call(app_tester.application.poetry, mocker.ANY),
        mocker.call(app_tester.application.poetry, mocker.ANY),
        mocker.call(app_tester.application.poetry, mocker.ANY),
    ] == mock.call_args_list

    assert set_path.call_args_list == [
        mocker.call(mocker.ANY, Path("/foo")),
        mocker.call(mocker.ANY, Path("/foo")),
        mocker.call(mocker.ANY, Path("/foo")),
        mocker.call(mocker.ANY, Path("/foo")),
    ]
    assert set_executable.call_args_list == [
        mocker.call(mocker.ANY, None),
        mocker.call(mocker.ANY, "python3.8"),
        mocker.call(mocker.ANY, None),
        mocker.call(mocker.ANY, None),
    ]
    assert set_zip_config.call_args_list == [
        mocker.call(mocker.ANY, {}),
        mocker.call(mocker.ANY, {}),
        mocker.call(mocker.ANY, {}),
        mocker.call(mocker.ANY, {}),
    ]
    assert set_activated_groups.call_args_list == [
        mocker.call(mocker.ANY, {"main"}),
        mocker.call(mocker.ANY, {"main", "dev"}),
        mocker.call(mocker.ANY, {"dev"}),
        mocker.call(mocker.ANY, {"dev"}),
    ]
