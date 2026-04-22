from __future__ import annotations

from .legacy import load


_legacy_output = load("abw_output")


def render(result, *, debug: bool = False, level: str | None = None) -> str:
    return _legacy_output.render(result, debug=debug, level=level)


def configure_stdout() -> None:
    _legacy_output.configure_stdout()


def enforce_runner_output(result):
    return _legacy_output.enforce_runner_output(result)


USER_LEVELS = _legacy_output.USER_LEVELS
