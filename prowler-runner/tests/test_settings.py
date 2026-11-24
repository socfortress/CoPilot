"""Settings from the environment: commands are absolute paths, numbers are bounded."""

import pytest

from runner.settings import Settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    for name in ("PROWLER_RUNNER_TOKEN", "PROWLER_MAX_CONCURRENT", "HTTPS_PROXY", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults(env):
    settings = Settings.from_env()
    assert settings.token is None
    assert settings.token_configured is False
    assert settings.max_concurrent == 2
    assert settings.scan_timeout == 14400
    assert settings.passthrough_env == {}


def test_only_proxy_settings_pass_through(env):
    env.setenv("HTTPS_PROXY", "http://proxy.internal:3128")
    env.setenv("AWS_SECRET_ACCESS_KEY", "never-passed")
    assert Settings.from_env().passthrough_env == {"HTTPS_PROXY": "http://proxy.internal:3128"}


def test_a_short_token_is_no_token(env):
    env.setenv("PROWLER_RUNNER_TOKEN", "x" * 31)
    assert Settings.from_env().token_configured is False
    env.setenv("PROWLER_RUNNER_TOKEN", "x" * 32)
    assert Settings.from_env().token_configured is True


def test_no_setting_chooses_what_the_runner_executes(env):
    env.setenv("PROWLER_BIN", "/bin/sh")
    env.setenv("PROWLER_PYTHON", "/bin/sh")
    settings = Settings.from_env()
    assert settings.prowler_cmd == ("/home/prowler/.venv/bin/prowler",)
    assert settings.prowler_python_cmd == ("/home/prowler/.venv/bin/python",)


@pytest.mark.parametrize(
    ("name", "value"),
    [("PROWLER_MAX_CONCURRENT", "0"), ("PROWLER_MAX_CONCURRENT", "two"), ("PROWLER_SCAN_TIMEOUT", "50000")],
)
def test_numbers_out_of_bounds(env, name, value):
    env.setenv(name, value)
    with pytest.raises(ValueError):
        Settings.from_env()
