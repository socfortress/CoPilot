"""upgrade.sh's compose-file editing and parsing, without Docker.

The script edits a customer's docker-compose.yml with awk, so these source its functions (under
every bash on this machine, 3.2 included) and check them against the compose file the repository
shipped before MySQL 8.4 (`fixtures/upgrade_script/`, docker-compose.yml at 3478661d) and the one it
ships now. The upgrade itself, against real MySQL servers, is tests/e2e/upgrade_script_e2e.py.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "upgrade.sh"
CURRENT = REPO / "docker-compose.yml"
BEFORE = Path(__file__).parent / "fixtures" / "upgrade_script" / "docker-compose.before-mysql-8.4.yml"
OLD_IMAGE = "mysql:8.0.46-debian"
FLAGS = ["--restrict-fk-on-non-standard-key=OFF", "--mysql-native-password=ON"]

BASHES = sorted({path for path in ("/bin/bash", shutil.which("bash")) if path and Path(path).exists()})


def run(bash: str, snippet: str, *args) -> str:
    """Run a snippet with the script's functions defined; $1… are `args`."""
    result = subprocess.run(
        [bash, "-c", f'source "$1"; shift; set +eu; {snippet}', "upgrade-test", str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def state(bash: str, path: Path) -> dict:
    return dict(line.split("=", 1) for line in run(bash, 'compose_mysql_state "$1"', path).splitlines())


def tokens(command: str) -> list:
    return command.split()


@pytest.fixture(params=BASHES)
def bash(request):
    return request.param


def test_sourcing_defines_the_functions_and_runs_nothing(bash):
    assert run(bash, "type compose_mysql_rewrite >/dev/null && echo defined").strip() == "defined"


def test_the_script_targets_what_docker_compose_yml_runs(bash):
    out = run(bash, 'echo "$TARGET_MYSQL_IMAGE"; printf "%s\\n" "${TARGET_FLAGS[@]}"').splitlines()
    mysql = yaml.safe_load(CURRENT.read_text())["services"]["copilot-mysql"]
    assert out[0] == mysql["image"]
    assert out[1:] == mysql["command"] == FLAGS


def test_the_retired_services_are_gone_from_docker_compose_yml(bash):
    retired = run(bash, 'printf "%s\\n" "${RETIRED_SERVICES[@]}"').split()
    assert "copilot-mcp" in retired
    assert not set(retired) & set(yaml.safe_load(CURRENT.read_text())["services"])
    # A compose file from before the removal still has it: stopped and started like the backend.
    assert "copilot-mcp" in yaml.safe_load(BEFORE.read_text())["services"]
    assert "copilot-mcp" in run(bash, 'printf "%s\\n" "${DB_CLIENT_SERVICES[@]}"').split()


# compose and docker stand in for Docker: the compose file defines only the backend, whose container
# belongs to the project "copilot", and that project still has a copilot-mcp container.
LEFTOVER_FAKES = (
    'compose() { case "$*" in "config --services") echo copilot-backend ;; "ps -a -q copilot-backend") echo backend-id ;; esac; }; '
    'docker() { case "$1" in '
    'inspect) [ "$4" = backend-id ] && echo copilot ;; '
    'ps) [ "$4 $6" = "label=com.docker.compose.project=copilot label=com.docker.compose.service=copilot-mcp" ] && echo mcp-id ;; '
    "esac; return 0; }; "
)


def test_a_container_left_for_a_service_the_compose_file_dropped(bash):
    snippet = LEFTOVER_FAKES + 'echo "[$(leftover_container copilot-mcp)] [$(leftover_container copilot-backend)]"'
    assert run(bash, snippet).strip() == "[mcp-id] []"


def test_no_leftover_without_a_backend_container(bash):
    snippet = LEFTOVER_FAKES + 'compose() { [ "$*" = "config --services" ] && echo copilot-backend; return 0; }; '
    snippet += 'echo "[$(leftover_container copilot-mcp)]"'
    assert run(bash, snippet).strip() == "[]"


def test_state_of_the_compose_files(bash, tmp_path):
    before = state(bash, BEFORE)
    assert before["found"] == "1"
    assert before["image"] == OLD_IMAGE
    assert tokens(before["command"]) == []
    current = state(bash, CURRENT)
    assert current["image"] == "mysql:8.4.13"
    assert sorted(tokens(current["command"])) == sorted(FLAGS)
    missing = tmp_path / "compose.yml"
    missing.write_text("services:\n  copilot-backend:\n    image: x\n")
    assert state(bash, missing)["found"] == "0"


def test_adding_the_flags_to_the_old_file_gives_the_new_mysql_service_and_nothing_else(bash, tmp_path):
    patched = yaml.safe_load(run(bash, 'compose_mysql_rewrite "$1" "$2" add', BEFORE, "mysql:8.4.13"))
    current = yaml.safe_load(CURRENT.read_text())
    before = yaml.safe_load(BEFORE.read_text())
    assert patched["services"]["copilot-mysql"] == current["services"]["copilot-mysql"]
    before["services"]["copilot-mysql"] = current["services"]["copilot-mysql"]
    assert patched == before
    # The edited file reads back as ours.
    path = tmp_path / "docker-compose.yml"
    path.write_text(run(bash, 'compose_mysql_rewrite "$1" "$2" add', BEFORE, "mysql:8.4.13"))
    edited = state(bash, path)
    assert edited["image"] == "mysql:8.4.13"
    assert run(bash, 'command_is_ours "$1" && echo yes || echo no', edited["command"]).strip() == "yes"


def test_removing_them_from_the_new_file_gives_the_old_mysql_service_back(bash):
    restored = yaml.safe_load(run(bash, 'compose_mysql_rewrite "$1" "$2" remove', CURRENT, OLD_IMAGE))
    current = yaml.safe_load(CURRENT.read_text())
    before = yaml.safe_load(BEFORE.read_text())
    assert restored["services"]["copilot-mysql"] == before["services"]["copilot-mysql"]
    current["services"]["copilot-mysql"] = before["services"]["copilot-mysql"]
    assert restored == current


TWO_SPACES = """\
services:
  copilot-backend:
    image: ghcr.io/socfortress/copilot-backend:latest
  copilot-mysql:   # the database
    environment:
      MYSQL_DATABASE: copilot

    image: "mysql:8.0.38-debian"   # pinned
    volumes:
      - mysql-data:/var/lib/mysql
  copilot-mysql-exporter:
    image: prom/mysqld-exporter
volumes:
  mysql-data:
"""


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_another_layout_keeps_everything_but_the_image_and_command(bash, tmp_path, newline):
    path = tmp_path / "docker-compose.yml"
    path.write_bytes(TWO_SPACES.replace("\n", newline).encode())
    found = state(bash, path)
    assert (found["found"], found["image"], tokens(found["command"])) == ("1", "mysql:8.0.38-debian", [])
    patched = yaml.safe_load(run(bash, 'compose_mysql_rewrite "$1" "$2" add', path, "mysql:8.4.13"))
    original = yaml.safe_load(TWO_SPACES)
    assert patched["services"]["copilot-mysql"] == {**original["services"]["copilot-mysql"], "image": "mysql:8.4.13", "command": FLAGS}
    assert patched["services"]["copilot-mysql-exporter"] == {"image": "prom/mysqld-exporter"}
    assert patched["services"]["copilot-backend"] == original["services"]["copilot-backend"]
    assert patched["volumes"] == original["volumes"]


# What `docker compose config` prints: depends_on as a map, so `copilot-mysql:` comes up first
# inside copilot-backend.
NORMALIZED = """\
name: copilot
services:
  copilot-backend:
    depends_on:
      copilot-mysql:
        condition: service_started
        required: true
    image: ghcr.io/socfortress/copilot-backend:latest
  copilot-minio:
    command:
      - server
      - /data
    image: ghcr.io/socfortress/minio:release.2024-09-13t20-26-02z
  copilot-mysql:
    command:
      - --restrict-fk-on-non-standard-key=OFF
      - --mysql-native-password=ON
    image: mysql:8.4.13
    restart: always
volumes:
  mysql-data:
    name: copilot_mysql-data
"""


def test_a_depends_on_map_is_not_the_service(bash, tmp_path):
    path = tmp_path / "docker-compose.yml"
    path.write_text(
        NORMALIZED.replace("mysql:8.4.13", "mysql:8.0.46-debian").replace(
            "    command:\n      - --restrict-fk-on-non-standard-key=OFF\n      - --mysql-native-password=ON\n",
            "",
        ),
    )
    found = state(bash, path)
    assert (found["found"], found["image"], tokens(found["command"])) == ("1", "mysql:8.0.46-debian", [])
    patched = yaml.safe_load(run(bash, 'compose_mysql_rewrite "$1" "$2" add', path, "mysql:8.4.13"))
    original = yaml.safe_load(path.read_text())
    assert patched["services"]["copilot-backend"] == original["services"]["copilot-backend"]
    assert patched["services"]["copilot-minio"] == original["services"]["copilot-minio"]
    assert patched["services"]["copilot-mysql"] == {"image": "mysql:8.4.13", "command": FLAGS, "restart": "always"}


def test_reading_the_effective_config(bash, tmp_path):
    path = tmp_path / "config.yml"
    path.write_text(NORMALIZED)
    # compose stands in for `docker compose config` (effective_mysql_block's own locals shadow short names).
    snippet = 'normalized_config="$1"; compose() { cat "$normalized_config"; }; block=$(effective_mysql_block x); printf "%s\\n" "$block"; '
    snippet += 'effective_block_ok "$block" mysql:8.4.13 && echo OK; effective_block_ok "$block" mysql:8.0.46 || echo NOT-8.0'
    out = run(bash, snippet, path).splitlines()
    assert out[0].strip() == "command:" and "image: mysql:8.4.13" in [line.strip() for line in out]
    assert "condition: service_started" not in "\n".join(out)
    assert out[-2:] == ["OK", "NOT-8.0"]


@pytest.mark.parametrize(
    "command, ours",
    [
        ("command: --restrict-fk-on-non-standard-key=OFF --mysql-native-password=ON", True),
        ('command: ["--mysql-native-password=ON", "--restrict-fk-on-non-standard-key=OFF"]', True),
        ("command:\n      - '--mysql-native-password=ON'   # 5.7 users\n      - --restrict-fk-on-non-standard-key=OFF", True),
        ("command: --default-authentication-plugin=mysql_native_password", False),
        ("command:\n      - --restrict-fk-on-non-standard-key=OFF", False),
        ("command:\n      - --restrict-fk-on-non-standard-key=OFF\n      - --mysql-native-password=ON\n      - --sql-mode=", False),
    ],
)
def test_reading_a_command(bash, tmp_path, command, ours):
    path = tmp_path / "docker-compose.yml"
    path.write_text(f"services:\n  copilot-mysql:\n    image: mysql:8.4.13\n    {command}\n    restart: always\n")
    found = state(bash, path)
    assert run(bash, 'command_is_ours "$1" && echo yes || echo no', found["command"]).strip() == ("yes" if ours else "no")


def test_an_empty_command_is_not_ours(bash):
    assert run(bash, 'command_is_ours "" && echo yes || echo no').strip() == "no"


@pytest.mark.parametrize(
    "version, number",
    [("5.7.44", "50744"), ("5.7.44-log", "50744"), ("8.0.46", "80046"), ("8.0.4-rc", "80004"), ("8.4.13", "80413"), ("9.7.4", "90704")],
)
def test_version_numbers(bash, version, number):
    assert run(bash, 'version_num "$1"', version) == number
