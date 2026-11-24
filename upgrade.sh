#!/usr/bin/env bash
#
# upgrade.sh: upgrade a CoPilot Docker Compose deployment, its MySQL included.
#
# `docker compose pull && docker compose up -d` updates CoPilot's own images, but moving MySQL to
# a new major version upgrades its data in place, and that can't be undone. This script runs the
# whole upgrade in a safe order:
#
#   1. checks the deployment: Docker, the Compose file, MySQL's version, MySQL Shell's upgrade
#      checker, disk space, and that docker-compose.yml can be pointed at the new MySQL
#   2. downloads every new image while CoPilot keeps running
#   3. stops the services that use the database, dumps every database, and shuts MySQL down cleanly
#   4. archives MySQL's data directory as it was (the rollback point), then upgrades the data:
#      MySQL 5.7 goes through 8.0 first, since 8.4 can't upgrade 5.7 data directly
#   5. points docker-compose.yml's copilot-mysql at the new MySQL, with the flags CoPilot needs,
#      removes the containers of services CoPilot no longer has (copilot-mcp), starts everything,
#      and waits for the backend to finish its database migrations
#
# Run it from the directory that holds docker-compose.yml and .env:
#
#   ./upgrade.sh --check      look at the deployment and say what an upgrade would do; changes nothing
#   ./upgrade.sh              upgrade (asks before it stops anything)
#   ./upgrade.sh --rollback   put back the MySQL data and version from before the last upgrade
#
# See --help for the options. Docs: docs/getting-started/install-upgrade.mdx.

set -Eeuo pipefail

TARGET_MYSQL_IMAGE="mysql:8.4.13"
HOP_MYSQL_IMAGE="mysql:8.0.46" # MySQL 8.4 can't upgrade 5.7 data: 5.7 is upgraded to this first
TARGET_FLAGS=("--restrict-fk-on-non-standard-key=OFF" "--mysql-native-password=ON")
MYSQL_SERVICE="copilot-mysql"
BACKEND_SERVICE="copilot-backend"
DB_CLIENT_SERVICES=("copilot-backend" "copilot-mcp") # stopped before MySQL, started again after
# Services docker-compose.yml no longer has. `docker compose up -d` leaves the container an older
# compose file started for one running, so the upgrade stops it with the services that use the
# database and removes it before CoPilot starts again. (copilot-mcp stays in DB_CLIENT_SERVICES for a
# compose file that still has it: then it is stopped and started again like the backend.)
RETIRED_SERVICES=("copilot-mcp")
DATADIR="/var/lib/mysql"

# --- options ---------------------------------------------------------------------------------

MODE="upgrade"
ASSUME_YES=0
PULL=1
DATA_ARCHIVE=1
EDIT_GIT_COMPOSE=0
RUN_CHECKER=1
PROJECT_DIR=""
BACKUP_DIR=""
ROLLBACK_RUN=""
MYSQL_TIMEOUT=1800
BACKEND_TIMEOUT=900

usage() {
    cat <<'EOF'
Usage: ./upgrade.sh [options]
       ./upgrade.sh --rollback [RUN_DIR] [options]

Upgrades a CoPilot Docker Compose deployment, including the one-way upgrade of its MySQL data to
MySQL 8.4 (5.7 data goes through 8.0 first). Nothing is stopped before every check has passed and
you have confirmed.

Modes:
  --check                 Check the deployment and print the plan. Changes nothing.
  --rollback [RUN_DIR]    Stop CoPilot, put back the MySQL data archived by an upgrade run and the
                          MySQL version it had, and start CoPilot again. RUN_DIR defaults to the
                          newest run that archived MySQL's data.

Options:
  -y, --yes               Don't ask for confirmation.
  --dir DIR               The directory holding docker-compose.yml and .env (default: the current
                          directory, else the script's own).
  --backup-dir DIR        Where to write dumps, archives and logs (default: DIR/backups).
  --no-data-archive       Don't archive MySQL's data directory before upgrading it. Saves disk space,
                          but leaves only the SQL dump to go back with, and --rollback needs the archive.
  --no-pull               Use the images already on this host.
  --skip-checker          Don't run MySQL Shell's upgrade checker.
  --edit-compose          Edit docker-compose.yml even when it is tracked by git (by default the script
                          asks you to `git pull` the new one instead).
  --mysql-timeout SEC     How long MySQL may take to start and upgrade its data (default 1800).
  --backend-timeout SEC   How long the backend may take to start (default 900).
  -h, --help              Show this help.

Environment:
  COPILOT_MYSQL_ROOT_PASSWORD   MySQL's root password, if it no longer matches the container's
                                MYSQL_ROOT_PASSWORD (the password .env had when MySQL was created).
EOF
}

# --- output ------------------------------------------------------------------------------------

if [ -t 1 ]; then
    BOLD=$'\033[1m' RED=$'\033[31m' YELLOW=$'\033[33m' GREEN=$'\033[32m' RESET=$'\033[0m'
else
    BOLD="" RED="" YELLOW="" GREEN="" RESET=""
fi

stamp() { date '+%H:%M:%S'; }
step() { printf '\n%s==> %s%s\n' "$BOLD" "$*" "$RESET"; }
info() { printf '[%s] %s\n' "$(stamp)" "$*"; }
ok() { printf '[%s] %s%s%s\n' "$(stamp)" "$GREEN" "$*" "$RESET"; }
warn() { printf '[%s] %sWARNING:%s %s\n' "$(stamp)" "$YELLOW" "$RESET" "$*" >&2; }
die() {
    printf '[%s] %sERROR:%s %s\n' "$(stamp)" "$RED" "$RESET" "$*" >&2
    exit 1
}

confirm() {
    [ "$ASSUME_YES" = 1 ] && return 0
    [ -t 0 ] || die "Not running interactively: pass --yes to confirm."
    local answer
    printf '%s [y/N] ' "$1"
    read -r answer
    case $answer in y | Y | yes | YES) return 0 ;; *) return 1 ;; esac
}

# --- docker helpers ----------------------------------------------------------------------------

COMPOSE=()
detect_compose() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE=(docker-compose)
    else
        die "Docker Compose isn't installed (neither 'docker compose' nor 'docker-compose')."
    fi
}

compose() { "${COMPOSE[@]}" "$@"; }

service_defined() { compose config --services 2>/dev/null | grep -qx "$1"; }

# The service's container, running or not (empty when it has none).
service_container() { compose ps -a -q "$1" 2>/dev/null | head -n1; }

# The container this project still has for a service its compose file doesn't define, left by an
# older compose file (empty when there is none, or when the service is defined). Compose labels its
# containers with the project's name, read here from the backend's container.
leftover_container() {
    local backend project
    service_defined "$1" && return 0
    backend=$(service_container "$BACKEND_SERVICE")
    [ -n "$backend" ] || return 0
    project=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$backend" 2>/dev/null) || return 0
    [ -n "$project" ] || return 0
    docker ps -aq --filter "label=com.docker.compose.project=$project" --filter "label=com.docker.compose.service=$1" 2>/dev/null | head -n1 || true
}

container_running() { [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]; }

ROOT_PW=""
# Run a command inside a MySQL container with MySQL's root password in MYSQL_PWD. The password
# goes in on stdin, so it never appears in a process list.
mysql_exec() {
    local cid=$1
    shift
    printf '%s\n' "$ROOT_PW" | docker exec -i "$cid" sh -c 'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"' sh "$@"
}

# Print a query's rows, tab-separated, without headers.
sql() { mysql_exec "$1" mysql -uroot -N -B -e "$2"; }

read_root_password() {
    local cid=$1 file
    if [ -n "${COPILOT_MYSQL_ROOT_PASSWORD:-}" ]; then
        ROOT_PW=$COPILOT_MYSQL_ROOT_PASSWORD
        return
    fi
    ROOT_PW=$(docker exec "$cid" printenv MYSQL_ROOT_PASSWORD 2>/dev/null || true)
    if [ -z "$ROOT_PW" ]; then
        file=$(docker exec "$cid" printenv MYSQL_ROOT_PASSWORD_FILE 2>/dev/null || true)
        [ -n "$file" ] && ROOT_PW=$(docker exec "$cid" cat "$file" 2>/dev/null || true)
    fi
    [ -n "$ROOT_PW" ] || die "Can't find MySQL's root password in the $MYSQL_SERVICE container. Set COPILOT_MYSQL_ROOT_PASSWORD and run again."
}

# Wait until the MySQL server in the container answers queries. Fails as soon as the container stops.
wait_mysql() {
    local cid=$1 label=$2 deadline last=0 now
    deadline=$(($(date +%s) + MYSQL_TIMEOUT))
    while :; do
        if ! container_running "$cid"; then
            warn "$label stopped. Its last log lines:"
            docker logs --tail 40 "$cid" >&2 2>&1 || true
            return 1
        fi
        if sql "$cid" "SELECT 1" >/dev/null 2>&1; then
            return 0
        fi
        now=$(date +%s)
        if [ "$now" -ge "$deadline" ]; then
            warn "$label didn't answer within ${MYSQL_TIMEOUT}s. Its last log lines:"
            docker logs --tail 40 "$cid" >&2 2>&1 || true
            return 1
        fi
        if [ $((now - last)) -ge 30 ]; then
            info "Waiting for $label (it can take a while when MySQL upgrades its data)..."
            last=$now
        fi
        sleep 3
    done
}

server_version() { sql "$1" "SELECT VERSION()" | head -n1; }

# 8.0.46 -> 80046, 5.7.44-log -> 50744
version_num() {
    local v=${1%%-*} major minor patch
    IFS=. read -r major minor patch <<EOF
$v
EOF
    printf '%d%02d%02d' "${major:-0}" "${minor:-0}" "${patch:-0}"
}

# Shut MySQL down with a full purge and change-buffer merge, the state an in-place upgrade wants,
# and check that it ended cleanly. $2 is the command that stops the container.
slow_shutdown() {
    local cid=$1
    shift
    sql "$cid" "SET GLOBAL innodb_fast_shutdown = 0" >/dev/null
    "$@" >/dev/null
    local code
    code=$(docker inspect -f '{{.State.ExitCode}}' "$cid")
    [ "$code" = 0 ] || die "MySQL didn't shut down cleanly (exit code $code). Its last log lines:
$(docker logs --tail 20 "$cid" 2>&1)"
}

# The -v options that give another container the same mounts as this one.
MOUNT_ARGS=()
DATA_MOUNT=""
read_mounts() {
    local cid=$1 type src dest rw
    MOUNT_ARGS=()
    DATA_MOUNT=""
    while IFS='|' read -r type src dest rw; do
        [ -n "$type" ] || continue
        case $type in volume | bind) ;; *) continue ;; esac
        if [ "$rw" = "true" ]; then
            MOUNT_ARGS+=(-v "$src:$dest")
        else
            MOUNT_ARGS+=(-v "$src:$dest:ro")
        fi
        [ "$dest" = "$DATADIR" ] && DATA_MOUNT="$type:$src"
    done <<EOF
$(docker inspect -f '{{range .Mounts}}{{.Type}}|{{if eq .Type "volume"}}{{.Name}}{{else}}{{.Source}}{{end}}|{{.Destination}}|{{.RW}}{{"\n"}}{{end}}' "$cid")
EOF
    [ -n "$DATA_MOUNT" ] || die "The $MYSQL_SERVICE container keeps $DATADIR on no volume or bind mount, so its data would be lost when the container is replaced. Back it up and move it onto a volume first."
}

data_mount_arg() { printf '%s:%s' "${DATA_MOUNT#*:}" "$DATADIR"; }

# Whether the backend in this container answers HTTP, i.e. has finished starting (its migrations
# included): uvicorn takes connections only after the app's startup. Its log can't say so reliably:
# uvicorn's "Application startup complete" goes missing whenever migrations ran, since Alembic's
# logging setup turns uvicorn's loggers off.
backend_answers() {
    docker exec "$1" python3 -c '
import urllib.error, urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:5000/", timeout=5)
except urllib.error.HTTPError:
    pass
' >/dev/null 2>&1
}

# The containers that upgrade MySQL's data carry this label, with the project directory as its value.
HOP_LABEL="com.socfortress.copilot.upgrade"

# Stop (cleanly: one may be in the middle of upgrading the data) and remove this project's upgrade
# containers, keeping their logs in $1 when given.
remove_hop_containers() {
    local c name
    for c in $(docker ps -aq --filter "label=$HOP_LABEL=$PROJECT_DIR" 2>/dev/null); do
        name=$(docker inspect -f '{{.Name}}' "$c" 2>/dev/null || echo "$c")
        docker stop -t 900 "$c" >/dev/null 2>&1 || true
        [ -n "${1:-}" ] && docker logs "$c" >"$1/${name#/}.log" 2>&1
        docker rm -f "$c" >/dev/null 2>&1 || true
    done
}

# --- the compose file ------------------------------------------------------------------------

COMPOSE_FILE_PATH=""
OVERRIDE_FILE=""
find_compose_file() {
    local f
    for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
        if [ -f "$f" ]; then
            COMPOSE_FILE_PATH="$PWD/$f"
            break
        fi
    done
    [ -n "$COMPOSE_FILE_PATH" ] || return 1
    for f in compose.override.yaml compose.override.yml docker-compose.override.yaml docker-compose.override.yml; do
        if [ -f "$f" ]; then
            OVERRIDE_FILE="$PWD/$f"
            break
        fi
    done
    return 0
}

# awk functions shared by the readers of compose files below. starts_service(line) is true only
# for the copilot-mysql key directly under the top-level `services:`, never for a mention of it
# deeper down (a `depends_on:` map has one). Call it with every line that isn't blank or a comment.
AWK_SERVICES='
    function ind(s) { match(s, /^ */); return RLENGTH }
    function starts_service(line,   i) {
        i = ind(line)
        if (i == 0) { in_services = (line ~ /^services:[ ]*(#.*)?$/); service_ind = -1; return 0 }
        if (!in_services) return 0
        if (service_ind < 0) service_ind = i
        return i == service_ind && line ~ ("^[ ]*" SVC ":[ ]*(#.*)?$")
    }
'

# Print the copilot-mysql service's image and command as written in a compose file:
#   found=1 / image=... / command=<tokens>
# The command's tokens are space-separated, quotes dropped, whether it is a list or a string.
compose_mysql_state() {
    awk -v SVC="$MYSQL_SERVICE" "$AWK_SERVICES"'
        function value(s) { sub(/^[^:]*:[ ]*/, "", s); sub(/[ ]+#.*$/, "", s); gsub(/["\047]/, "", s); return s }
        {
            line = $0; sub(/\r$/, "", line)
            if (line ~ /^[ ]*(#.*)?$/) next
            if (in_svc && ind(line) <= svc_ind) in_svc = 0
            if (!in_svc) {
                if (starts_service(line) && !found) { in_svc = 1; found = 1; svc_ind = ind(line); key_ind = -1 }
                next
            }
            if (key_ind < 0) key_ind = ind(line)
            if (ind(line) == key_ind) {
                in_cmd = 0
                if (line ~ /^[ ]*image:/) image = value(line)
                if (line ~ /^[ ]*command:/) { in_cmd = 1; v = value(line); gsub(/[\[\],]/, " ", v); command = command " " v }
                next
            }
            if (in_cmd) { v = line; sub(/^[ ]*-[ ]*/, "", v); sub(/[ ]+#.*$/, "", v); gsub(/["\047]/, "", v); command = command " " v }
        }
        END { printf "found=%d\nimage=%s\ncommand=%s\n", found, image, command }
    ' "$1"
}

state_value() { printf '%s\n' "$1" | sed -n "s/^$2=//p" | head -n1; }

# Whether a command string is exactly the flags CoPilot needs, in any order.
command_is_ours() {
    local tokens=" $1 " t
    for t in "${TARGET_FLAGS[@]}"; do
        case $tokens in *" $t "*) tokens=${tokens/ $t / } ;; *) return 1 ;; esac
    done
    [ -z "${tokens// /}" ]
}

# Write the compose file with copilot-mysql's image set to $2 and, when $3 is "add", the command
# flags added after it (the same lines as the repository's docker-compose.yml), or, when $3 is
# "remove", its command block taken out.
compose_mysql_rewrite() {
    awk -v SVC="$MYSQL_SERVICE" -v IMAGE="$2" -v CMD="$3" "$AWK_SERVICES"'
        function pad(n,   p) { p = ""; while (n-- > 0) p = p " "; return p }
        {
            raw = $0; line = $0; sub(/\r$/, "", line)
            blank = (line ~ /^[ ]*(#.*)?$/)
            if (skipping) {
                if (blank || ind(line) > key_ind) next
                skipping = 0
            }
            if (in_svc && !blank && ind(line) <= svc_ind) in_svc = 0
            if (!in_svc) {
                if (!blank && starts_service(line) && !found) { in_svc = 1; found = 1; svc_ind = ind(line); key_ind = -1 }
                print raw
                next
            }
            if (!blank) {
                if (key_ind < 0) key_ind = ind(line)
                if (ind(line) == key_ind && line ~ /^[ ]*image:/) {
                    print pad(key_ind) "image: " IMAGE
                    if (CMD == "add") {
                        step = key_ind - svc_ind; if (step < 2) step = 2
                        item = pad(key_ind + step)
                        print pad(key_ind) "command:"
                        print item "# CoPilot'"'"'s foreign keys to agents.agent_id (and, until migration 38c2e85a670a, to"
                        print item "# customers.customer_code) point at non-unique indexes, which MySQL 8.4 otherwise"
                        print item "# refuses to create, or to ALTER the tables of (backend/app/db/mysql_compat.py;"
                        print item "# migrations also switch it off themselves)."
                        print item "- --restrict-fk-on-non-standard-key=OFF"
                        print item "# Databases first created by this stack'"'"'s mysql:5.7 image (until September 2024) still"
                        print item "# have users on mysql_native_password, which MySQL 8.4 no longer loads by default."
                        print item "- --mysql-native-password=ON"
                    }
                    next
                }
                if (CMD == "remove" && ind(line) == key_ind && line ~ /^[ ]*command:/) { skipping = 1; next }
            }
            print raw
        }
    ' "$1"
}

# Print the copilot-mysql block of `docker compose config` for the given compose files.
effective_mysql_block() {
    local args=() f
    for f in "$@"; do args+=(-f "$f"); done
    compose "${args[@]}" config 2>/dev/null | awk -v SVC="$MYSQL_SERVICE" "$AWK_SERVICES"'
        $0 ~ /^[ ]*(#.*)?$/ { next }
        in_svc && ind($0) <= svc_ind { exit }
        in_svc { print; next }
        starts_service($0) { in_svc = 1; svc_ind = ind($0) }
    '
}

# Whether a copilot-mysql block runs image $2 with every flag CoPilot needs.
effective_block_ok() {
    local block=$1 image=$2 t
    printf '%s\n' "$block" | grep -Fxq "image: $image" ||
        printf '%s\n' "$block" | sed 's/^[[:space:]]*//' | grep -Fxq "image: $image" || return 1
    for t in "${TARGET_FLAGS[@]}"; do
        printf '%s\n' "$block" | grep -q -- "$t" || return 1
    done
}

# --- run directory and state ---------------------------------------------------------------

RUN_DIR=""
STATE_FILE=""
LOCK_DIR=""

set_state() {
    local key=$1 value=$2 tmp
    tmp="$STATE_FILE.tmp"
    { grep -v "^$key=" "$STATE_FILE" 2>/dev/null || true; printf '%s=%s\n' "$key" "$value"; } >"$tmp"
    mv "$tmp" "$STATE_FILE"
}

get_state() { sed -n "s/^$2=//p" "$1" | tail -n1; }

take_lock() {
    mkdir -p "$BACKUP_DIR"
    LOCK_DIR="$BACKUP_DIR/.upgrade.lock"
    mkdir "$LOCK_DIR" 2>/dev/null || die "Another upgrade.sh seems to be running ($LOCK_DIR exists). If none is, remove that directory and run again."
}

PHASE="checks"
PATCHED_TMP=""
on_exit() {
    local code=$?
    if [ -n "$LOCK_DIR" ]; then rmdir "$LOCK_DIR" 2>/dev/null || true; fi
    if [ -n "$PATCHED_TMP" ]; then rm -f "$PATCHED_TMP"; fi
    [ "$code" = 0 ] && return
    [ "$MODE" = "upgrade" ] || return
    remove_hop_containers "$RUN_DIR"
    printf '\n%sThe upgrade stopped during: %s.%s\n' "$RED" "$PHASE" "$RESET" >&2
    case $PHASE in
        checks | "pulling images")
            echo "Nothing was changed: CoPilot is still running as before." >&2
            ;;
        "stopping CoPilot" | "dumping the databases" | "stopping MySQL")
            echo "MySQL's data is unchanged. Start CoPilot again with: ${COMPOSE[*]} up -d" >&2
            ;;
        "archiving MySQL's data" | "upgrading MySQL's data" | "updating docker-compose.yml" | "starting MySQL")
            echo "MySQL's data may be partly upgraded, and CoPilot is stopped." >&2
            if [ "$DATA_ARCHIVE" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/mysql-data.tar.gz" ]; then
                echo "To go back to where you started: ./upgrade.sh --rollback $RUN_DIR" >&2
            else
                echo "There is no data archive to roll back to; the SQL dump is in ${RUN_DIR:-the backup directory}." >&2
            fi
            ;;
        *)
            echo "MySQL has been upgraded. Check the stack with: ${COMPOSE[*]} ps; ${COMPOSE[*]} logs $BACKEND_SERVICE" >&2
            [ -n "$RUN_DIR" ] && echo "To go back to where you started: ./upgrade.sh --rollback $RUN_DIR" >&2
            ;;
    esac
    [ -n "$RUN_DIR" ] && echo "Log of this run: $RUN_DIR/upgrade.log" >&2
}

# Sourced (as the tests do): stop here, with the functions defined.
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
    return 0
fi

# --- main ------------------------------------------------------------------------------------

while [ $# -gt 0 ]; do
    case $1 in
        --check) MODE="check" ;;
        --rollback)
            MODE="rollback"
            if [ $# -gt 1 ] && [ "${2#-}" = "$2" ]; then
                ROLLBACK_RUN=$2
                shift
            fi
            ;;
        -y | --yes) ASSUME_YES=1 ;;
        --dir)
            PROJECT_DIR=${2:?--dir needs a directory}
            shift
            ;;
        --backup-dir)
            BACKUP_DIR=${2:?--backup-dir needs a directory}
            shift
            ;;
        --no-data-archive) DATA_ARCHIVE=0 ;;
        --no-pull) PULL=0 ;;
        --skip-checker) RUN_CHECKER=0 ;;
        --edit-compose) EDIT_GIT_COMPOSE=1 ;;
        --mysql-timeout)
            MYSQL_TIMEOUT=${2:?--mysql-timeout needs seconds}
            shift
            ;;
        --backend-timeout)
            BACKEND_TIMEOUT=${2:?--backend-timeout needs seconds}
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1 (see --help)" >&2
            exit 2
            ;;
    esac
    shift
done

trap on_exit EXIT
trap 'exit 130' INT TERM

# --- setup ---------------------------------------------------------------------------------

command -v docker >/dev/null 2>&1 || die "Docker isn't installed."
docker info >/dev/null 2>&1 || die "Can't reach the Docker daemon (are you in the docker group, or root?)."
detect_compose

if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR=$PWD
    if ! (cd "$PROJECT_DIR" && find_compose_file); then
        PROJECT_DIR=$(cd "$(dirname "$0")" && pwd -P)
    fi
fi
cd "$PROJECT_DIR" || die "Can't enter $PROJECT_DIR"
find_compose_file || die "No docker-compose.yml in $PROJECT_DIR. Run this from your CoPilot directory, or pass --dir."
[ -f .env ] || die "No .env in $PROJECT_DIR. Run this from your CoPilot directory (the one CoPilot runs from), or pass --dir."
[ -n "$BACKUP_DIR" ] || BACKUP_DIR="$PROJECT_DIR/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_DIR=$(cd "$BACKUP_DIR" && pwd -P)

# ===========================================================================================
# Rollback
# ===========================================================================================

if [ "$MODE" = "rollback" ]; then
    if [ -z "$ROLLBACK_RUN" ]; then
        # The newest run that upgraded MySQL's data, i.e. that has an archive to go back to. The
        # names sort by time, and a glob expands sorted.
        runs=("$BACKUP_DIR"/upgrade-*)
        i=$((${#runs[@]} - 1))
        while [ "$i" -ge 0 ]; do
            if [ -f "${runs[$i]}/state" ] && [ -f "${runs[$i]}/mysql-data.tar.gz" ]; then
                ROLLBACK_RUN=${runs[$i]}
                break
            fi
            i=$((i - 1))
        done
        [ -n "$ROLLBACK_RUN" ] || die "No upgrade run with a data archive under $BACKUP_DIR."
    fi
    ROLLBACK_RUN=$(cd "$ROLLBACK_RUN" && pwd -P) || die "No such run directory: $ROLLBACK_RUN"
    STATE=$ROLLBACK_RUN/state
    [ -f "$STATE" ] || die "$ROLLBACK_RUN has no state file: it isn't an upgrade.sh run."
    OLD_IMAGE=$(get_state "$STATE" OLD_IMAGE)
    OLD_VERSION=$(get_state "$STATE" OLD_VERSION)
    DATA_MOUNT=$(get_state "$STATE" DATA_MOUNT)
    COMPOSE_PATCHED=$(get_state "$STATE" COMPOSE_PATCHED)
    COMPOSE_BEFORE=$ROLLBACK_RUN/$(basename "$COMPOSE_FILE_PATH").before
    ARCHIVE=$ROLLBACK_RUN/mysql-data.tar.gz
    [ -f "$ARCHIVE" ] || die "$ROLLBACK_RUN has no data archive (the run used --no-data-archive, or stopped before taking it). Restore the SQL dump in that directory by hand: docs/getting-started/install-upgrade.mdx."
    [ -n "$OLD_IMAGE" ] && [ -n "$DATA_MOUNT" ] || die "The state file in $ROLLBACK_RUN is incomplete."

    step "Rollback"
    info "Run:            $ROLLBACK_RUN"
    info "MySQL goes back to $OLD_IMAGE (MySQL $OLD_VERSION) with the data archived before the upgrade."
    warn "Everything written to CoPilot's database since that upgrade started is lost."
    confirm "Stop CoPilot and replace MySQL's data with the archive?" || die "Stopped: nothing was changed."
    take_lock
    LOG=$ROLLBACK_RUN/rollback.log
    exec > >(tee -a "$LOG") 2>&1

    step "Stopping the services that use the database, and MySQL"
    for s in "${DB_CLIENT_SERVICES[@]}"; do
        service_defined "$s" && compose stop -t 60 "$s" >/dev/null
    done
    remove_hop_containers "$ROLLBACK_RUN"
    compose stop -t 900 "$MYSQL_SERVICE" >/dev/null

    step "Putting MySQL's data back"
    helper_image=$TARGET_MYSQL_IMAGE
    docker image inspect "$helper_image" >/dev/null 2>&1 || docker pull "$helper_image" >/dev/null
    docker run --rm -v "$(data_mount_arg)" -v "$ROLLBACK_RUN:/backup:ro" --entrypoint sh "$helper_image" -c \
        "find $DATADIR -mindepth 1 -delete && tar -C $DATADIR --numeric-owner -xzpf /backup/mysql-data.tar.gz"
    ok "Restored $DATADIR from $(basename "$ARCHIVE")."

    step "Pointing $(basename "$COMPOSE_FILE_PATH") back at $OLD_IMAGE"
    cp -p "$COMPOSE_FILE_PATH" "$ROLLBACK_RUN/$(basename "$COMPOSE_FILE_PATH").at-rollback"
    if [ "$COMPOSE_PATCHED" = 1 ] && [ -f "$COMPOSE_BEFORE" ]; then
        cat "$COMPOSE_BEFORE" >"$COMPOSE_FILE_PATH"
        info "Restored the compose file as it was before the upgrade."
    else
        state=$(compose_mysql_state "$COMPOSE_FILE_PATH")
        if command_is_ours "$(state_value "$state" command)"; then
            compose_mysql_rewrite "$COMPOSE_FILE_PATH" "$OLD_IMAGE" remove >"$COMPOSE_FILE_PATH.rollback-tmp"
        else
            compose_mysql_rewrite "$COMPOSE_FILE_PATH" "$OLD_IMAGE" keep >"$COMPOSE_FILE_PATH.rollback-tmp"
        fi
        cat "$COMPOSE_FILE_PATH.rollback-tmp" >"$COMPOSE_FILE_PATH"
        rm -f "$COMPOSE_FILE_PATH.rollback-tmp"
        info "Set $MYSQL_SERVICE's image to $OLD_IMAGE (the file as it was is kept in the run directory)."
    fi

    step "Starting CoPilot"
    compose up -d "$MYSQL_SERVICE" >/dev/null
    cid=$(service_container "$MYSQL_SERVICE")
    read_root_password "$cid"
    wait_mysql "$cid" "MySQL" || die "MySQL didn't start after the rollback."
    ok "MySQL $(server_version "$cid") is up."
    compose up -d >/dev/null
    ok "Rolled back. CoPilot is starting; follow it with: ${COMPOSE[*]} logs -f $BACKEND_SERVICE"
    exit 0
fi

# ===========================================================================================
# Checks (both --check and the upgrade run them; neither changes anything here)
# ===========================================================================================

step "Checking the deployment in $PROJECT_DIR"
info "Compose file:   $COMPOSE_FILE_PATH${OVERRIDE_FILE:+ (+ $(basename "$OVERRIDE_FILE"))}"
info "Compose:        $("${COMPOSE[@]}" version --short 2>/dev/null || echo unknown) (${COMPOSE[*]})"
compose config -q || die "docker compose can't read the compose file (see above)."

HAS_MYSQL=0
service_defined "$MYSQL_SERVICE" && HAS_MYSQL=1
service_defined "$BACKEND_SERVICE" || die "The compose file has no $BACKEND_SERVICE service: is this a CoPilot directory?"

# "service container" for each retired service an older compose file left a container for.
LEFTOVERS=()
for s in ${RETIRED_SERVICES[@]+"${RETIRED_SERVICES[@]}"}; do
    c=$(leftover_container "$s")
    if [ -n "$c" ]; then LEFTOVERS+=("$s $c"); fi
done

HOPS=()
NEEDS_COMPOSE_EDIT=0
NEW_IMAGE=""
CUR_VERSION=""
OLD_IMAGE=""
DATADIR_KB=0

if [ "$HAS_MYSQL" = 0 ]; then
    warn "No $MYSQL_SERVICE service: CoPilot uses a MySQL server of your own, which this script leaves alone. To move that server to MySQL 8.4, see 'Running CoPilot on your own MySQL server' in docs/getting-started/install-upgrade.mdx."
else
    MYSQL_CID=$(service_container "$MYSQL_SERVICE")
    [ -n "$MYSQL_CID" ] || die "$MYSQL_SERVICE has no container yet: start CoPilot once (${COMPOSE[*]} up -d) before upgrading it."
    if ! container_running "$MYSQL_CID"; then
        die "$MYSQL_SERVICE isn't running ($(docker inspect -f '{{.State.Status}}' "$MYSQL_CID")). The script needs it running to back it up. Its last log lines:
$(docker logs --tail 15 "$MYSQL_CID" 2>&1)
If those lines say MySQL can't upgrade or downgrade its data, set $MYSQL_SERVICE's image in $(basename "$COMPOSE_FILE_PATH") back to the version it ran before (often mysql:8.0.46-debian, mysql:8.0.38-debian or mysql:5.7), run '${COMPOSE[*]} up -d $MYSQL_SERVICE', and run this script again."
    fi
    read_root_password "$MYSQL_CID"
    if ! login=$(sql "$MYSQL_CID" "SELECT 1" 2>&1); then
        case $login in
            *"Access denied"*) die "Can't log in to MySQL as root with the container's MYSQL_ROOT_PASSWORD. If root's password was changed since MySQL was created, set COPILOT_MYSQL_ROOT_PASSWORD and run again." ;;
        esac
        info "MySQL isn't answering yet; waiting for it..."
        wait_mysql "$MYSQL_CID" "MySQL" || die "MySQL doesn't answer: $login"
    fi
    CUR_VERSION=$(server_version "$MYSQL_CID")
    OLD_IMAGE=$(docker inspect -f '{{.Config.Image}}' "$MYSQL_CID")
    read_mounts "$MYSQL_CID"
    info "MySQL:          $CUR_VERSION ($OLD_IMAGE), data on ${DATA_MOUNT%%:*} ${DATA_MOUNT#*:}"

    case $CUR_VERSION in *MariaDB* | *mariadb*) die "$MYSQL_SERVICE runs MariaDB, which this script doesn't upgrade." ;; esac
    cur=$(version_num "$CUR_VERSION")
    target=$(version_num "${TARGET_MYSQL_IMAGE#*:}")
    NEW_IMAGE=$TARGET_MYSQL_IMAGE
    if [ "$cur" -lt 50709 ]; then
        die "MySQL $CUR_VERSION is too old to upgrade in place (it needs 5.7.9 or later)."
    elif [ "$cur" -lt 80000 ]; then
        HOPS=("$HOP_MYSQL_IMAGE" "$TARGET_MYSQL_IMAGE")
    elif [ "$cur" -lt "$target" ]; then
        HOPS=("$TARGET_MYSQL_IMAGE")
    elif [ "$cur" -lt 80500 ]; then
        [ "$cur" -gt "$target" ] && NEW_IMAGE=$OLD_IMAGE # already on a newer 8.4: keep it
    else
        die "MySQL $CUR_VERSION is newer than the MySQL 8.4 this script moves CoPilot to; nothing for it to do."
    fi

    # The compose file: does it already point at the new MySQL with the flags, and if not, can we edit it?
    effective=$(effective_mysql_block "$COMPOSE_FILE_PATH" ${OVERRIDE_FILE:+"$OVERRIDE_FILE"})
    if effective_block_ok "$effective" "$NEW_IMAGE"; then
        info "Compose file:   already runs $NEW_IMAGE with CoPilot's flags."
    else
        NEEDS_COMPOSE_EDIT=1
        if [ -n "${COMPOSE_FILE:-}" ] || grep -q '^COMPOSE_FILE=' .env 2>/dev/null; then
            die "COMPOSE_FILE is set, so the script can't tell which file to edit. Set the image of $MYSQL_SERVICE to $TARGET_MYSQL_IMAGE and add its command flags (${TARGET_FLAGS[*]}) yourself, then run again."
        fi
        state=$(compose_mysql_state "$COMPOSE_FILE_PATH")
        [ "$(state_value "$state" found)" = 1 ] || die "$(basename "$COMPOSE_FILE_PATH") doesn't define $MYSQL_SERVICE itself, so the script can't edit it. Set its image to $TARGET_MYSQL_IMAGE and add the flags ${TARGET_FLAGS[*]} yourself, then run again."
        cmd=$(state_value "$state" command)
        if [ -n "${cmd// /}" ] && ! command_is_ours "$cmd"; then
            die "$MYSQL_SERVICE has its own command in $(basename "$COMPOSE_FILE_PATH") ($cmd). Some MySQL options were removed in 8.4, so the script won't guess: make it '${TARGET_FLAGS[*]}' plus the options you still need, set the image to $TARGET_MYSQL_IMAGE, and run again."
        fi
        if [ "$EDIT_GIT_COMPOSE" = 0 ] && command -v git >/dev/null 2>&1 &&
            git ls-files --error-unmatch -- "$(basename "$COMPOSE_FILE_PATH")" >/dev/null 2>&1; then
            die "$(basename "$COMPOSE_FILE_PATH") is the one from your git checkout of CoPilot, and it doesn't run $TARGET_MYSQL_IMAGE yet. Run 'git pull' to get the new one (don't run '${COMPOSE[*]} up' yet), then run ./upgrade.sh again. To have the script edit the file instead, pass --edit-compose."
        fi
        add=add
        [ -n "${cmd// /}" ] && add=keep
        PATCHED_TMP="$PROJECT_DIR/.$(basename "$COMPOSE_FILE_PATH").upgrade-tmp"
        compose_mysql_rewrite "$COMPOSE_FILE_PATH" "$NEW_IMAGE" "$add" >"$PATCHED_TMP"
        effective=$(effective_mysql_block "$PATCHED_TMP" ${OVERRIDE_FILE:+"$OVERRIDE_FILE"})
        if ! effective_block_ok "$effective" "$NEW_IMAGE"; then
            hint=""
            [ -n "$OVERRIDE_FILE" ] && hint=" (does $(basename "$OVERRIDE_FILE") set the image or command of $MYSQL_SERVICE?)"
            die "The edited compose file wouldn't run $NEW_IMAGE with CoPilot's flags$hint. Set them yourself, then run again."
        fi
        info "Compose file:   $MYSQL_SERVICE will be set to $NEW_IMAGE with CoPilot's flags (checked with '${COMPOSE[*]} config')."
    fi

    # Disk space: the dump and the archive go to the backup directory; the upgrade needs room in the volume.
    DATADIR_KB=$(docker exec "$MYSQL_CID" du -sk "$DATADIR" | awk '{print $1}')
    data_kb=$(sql "$MYSQL_CID" "SELECT CEIL(COALESCE(SUM(data_length + index_length), 0) / 1024) FROM information_schema.tables WHERE table_schema NOT IN ('mysql', 'sys', 'performance_schema', 'information_schema')")
    need_kb=$((data_kb + 524288))
    [ ${#HOPS[@]} -gt 0 ] && [ "$DATA_ARCHIVE" = 1 ] && need_kb=$((need_kb + DATADIR_KB))
    free_kb=$(df -Pk "$BACKUP_DIR" | awk 'NR == 2 {print $4}')
    volume_free_kb=$(docker exec "$MYSQL_CID" df -Pk "$DATADIR" | awk 'NR == 2 {print $4}')
    info "Disk:           data directory $((DATADIR_KB / 1024)) MB; $((free_kb / 1024)) MB free for backups (needs about $((need_kb / 1024)) MB), $((volume_free_kb / 1024)) MB free in the volume"
    [ "$free_kb" -ge "$need_kb" ] || die "Not enough free space in $BACKUP_DIR for the backups: free some, use --backup-dir, or (losing --rollback) --no-data-archive."
    [ "$volume_free_kb" -ge 524288 ] || die "Less than 512 MB free where MySQL keeps its data: free some space before upgrading it."

    # What the new MySQL will need to know about.
    native=$(sql "$MYSQL_CID" "SELECT GROUP_CONCAT(CONCAT(user, '@', host) SEPARATOR ', ') FROM mysql.user WHERE plugin = 'mysql_native_password' AND user NOT LIKE 'mysql.%'" || true)
    [ -n "$native" ] && [ "$native" != "NULL" ] && info "Users on mysql_native_password (kept working by --mysql-native-password=ON): $native"
    if sql "$MYSQL_CID" "SELECT 1 FROM information_schema.tables WHERE table_schema = 'copilot' AND table_name = 'customers'" | grep -q 1; then
        dups=$(sql "$MYSQL_CID" "SELECT GROUP_CONCAT(customer_code SEPARATOR ', ') FROM (SELECT MIN(customer_code) AS customer_code FROM copilot.customers GROUP BY customer_code HAVING COUNT(*) > 1) d")
        if [ -n "$dups" ] && [ "$dups" != "NULL" ]; then
            warn "copilot.customers has duplicate customer codes ($dups). The upgrade still works, but customer_code stays non-unique until they are resolved (see the backend's migration warning afterwards)."
        fi
    fi
fi

CHECKER_REPORT=""
run_checker() { # run_checker <container> <target version>: MySQL Shell's upgrade checker, as plain text
    printf '%s\n' "$ROOT_PW" | docker run --rm -i --network "container:$1" --entrypoint mysqlsh "$TARGET_MYSQL_IMAGE" \
        --passwords-from-stdin --uri "root@127.0.0.1:3306" -- util check-for-server-upgrade \
        --target-version="$2" --output-format=TEXT 2>&1 | awk '{ gsub(/\033\[[0-9;]*m/, ""); print }'
}

checker_errors() { printf '%s\n' "$1" | sed -n 's/^Errors:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | tail -n1; }

if [ ${#HOPS[@]} -gt 0 ]; then
    if [ "$PULL" = 0 ]; then
        for h in "${HOPS[@]}"; do
            docker image inspect "$h" >/dev/null 2>&1 || die "$h isn't on this host, and --no-pull was given: pull it first (docker pull $h)."
        done
    fi
    if [ "$PULL" = 1 ] || ! docker image inspect "$TARGET_MYSQL_IMAGE" >/dev/null 2>&1; then
        info "Pulling $TARGET_MYSQL_IMAGE (its MySQL Shell runs the upgrade checker)..."
        docker pull -q "$TARGET_MYSQL_IMAGE" >/dev/null || die "Can't pull $TARGET_MYSQL_IMAGE."
    fi
    if [ "$RUN_CHECKER" = 1 ]; then
        first_target=${HOPS[0]#*:}
        info "Running MySQL Shell's upgrade checker for MySQL $first_target..."
        CHECKER_REPORT=$(run_checker "$MYSQL_CID" "$first_target" || true)
        errors=$(checker_errors "$CHECKER_REPORT")
        if [ -z "$errors" ]; then
            printf '%s\n' "$CHECKER_REPORT" | tail -n 20 >&2
            die "The upgrade checker didn't run (see above). Fix that, or pass --skip-checker to upgrade without it."
        fi
        warnings=$(printf '%s\n' "$CHECKER_REPORT" | sed -n 's/^Warnings:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | tail -n1)
        if [ "$errors" != 0 ]; then
            printf '%s\n' "$CHECKER_REPORT" >&2
            die "The upgrade checker found $errors error(s) that would stop MySQL from upgrading (above). Fix them and run again."
        fi
        ok "Upgrade checker: no errors (${warnings:-0} warning(s); the full report is saved with the backups)."
    fi
fi

# --- the plan ----------------------------------------------------------------------------

step "Plan"
if [ "$HAS_MYSQL" = 1 ]; then
    if [ ${#HOPS[@]} -gt 0 ]; then
        path="$CUR_VERSION"
        for h in "${HOPS[@]}"; do path="$path -> ${h#*:}"; done
        echo "  MySQL:   $path (in place, one way: archived first)"
    else
        echo "  MySQL:   stays on $CUR_VERSION"
    fi
    [ "$NEEDS_COMPOSE_EDIT" = 1 ] && echo "  Compose: $MYSQL_SERVICE set to $NEW_IMAGE with ${TARGET_FLAGS[*]} (the old file is kept)"
    echo "  Backups: $BACKUP_DIR/upgrade-<time>/ (SQL dump of every database$([ ${#HOPS[@]} -gt 0 ] && [ "$DATA_ARCHIVE" = 1 ] && echo ", archive of MySQL's data directory"))"
fi
echo "  Images:  $([ "$PULL" = 1 ] && echo "pull the new ones, then recreate the containers that changed" || echo "use the ones on this host")"
for l in ${LEFTOVERS[@]+"${LEFTOVERS[@]}"}; do
    echo "  Remove:  the ${l%% *} container (CoPilot no longer has ${l%% *}; an older compose file started it)"
done
echo "  CoPilot is down from the database dump until the backend has started again."

if [ "$MODE" = "check" ]; then
    [ -n "$CHECKER_REPORT" ] && printf '\n%s\n' "$CHECKER_REPORT" | sed -n '/^Errors:/,$p'
    rm -f "${PATCHED_TMP:-}"
    printf '\n%sChecks passed: run ./upgrade.sh to upgrade.%s\n' "$GREEN" "$RESET"
    exit 0
fi

confirm "Go ahead?" || {
    rm -f "${PATCHED_TMP:-}"
    echo "Stopped: nothing was changed."
    exit 0
}

# ===========================================================================================
# Upgrade
# ===========================================================================================

take_lock
RUN_DIR="$BACKUP_DIR/upgrade-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_DIR"
chmod 700 "$RUN_DIR"
STATE_FILE=$RUN_DIR/state
: >"$STATE_FILE"
exec > >(tee -a "$RUN_DIR/upgrade.log") 2>&1
info "Writing backups and the log to $RUN_DIR"
[ -n "$CHECKER_REPORT" ] && printf '%s\n' "$CHECKER_REPORT" >"$RUN_DIR/upgrade-checker.txt"
cp -p "$COMPOSE_FILE_PATH" "$RUN_DIR/$(basename "$COMPOSE_FILE_PATH").before"
set_state STATUS started
set_state COMPOSE_FILE "$COMPOSE_FILE_PATH"
set_state COMPOSE_PATCHED 0
if [ "$HAS_MYSQL" = 1 ]; then
    set_state OLD_IMAGE "$OLD_IMAGE"
    set_state OLD_VERSION "$CUR_VERSION"
    set_state DATA_MOUNT "$DATA_MOUNT"
fi

PHASE="pulling images"
if [ "$PULL" = 1 ]; then
    step "Pulling the new images (CoPilot keeps running)"
    for h in ${HOPS[@]+"${HOPS[@]}"}; do docker pull -q "$h" >/dev/null || die "Can't pull $h."; done
    compose pull --ignore-buildable 2>/dev/null || compose pull || die "Can't pull the images (see above)."
    ok "Images pulled."
fi

if [ "$HAS_MYSQL" = 1 ]; then
    PHASE="stopping CoPilot"
    step "Stopping the services that use the database"
    for s in "${DB_CLIENT_SERVICES[@]}"; do
        service_defined "$s" || continue
        compose stop -t 60 "$s" >/dev/null
        info "Stopped $s."
    done
    for l in ${LEFTOVERS[@]+"${LEFTOVERS[@]}"}; do
        if docker stop -t 60 "${l#* }" >/dev/null 2>&1; then
            info "Stopped ${l%% *} (removed before CoPilot starts again)."
        else
            warn "Couldn't stop the ${l%% *} container (${l#* })."
        fi
    done

    PHASE="dumping the databases"
    step "Dumping every database"
    dump=$RUN_DIR/mysql-all-databases.sql.gz
    gtid=""
    [ "$(version_num "$CUR_VERSION")" -ge 50606 ] && gtid="--set-gtid-purged=OFF"
    mysql_exec "$MYSQL_CID" mysqldump -uroot --all-databases --single-transaction --routines --events \
        --triggers --hex-blob $gtid | gzip >"$dump"
    gzip -dc "$dump" | tail -n1 | grep -q '^-- Dump completed' || die "The dump didn't complete (see $dump)."
    chmod 600 "$dump"
    set_state DUMP "$dump"
    ok "Dumped to $(basename "$dump") ($(du -k "$dump" | awk '{printf "%d MB", $1 / 1024}'))."

    if [ ${#HOPS[@]} -gt 0 ] || [ "$NEEDS_COMPOSE_EDIT" = 1 ]; then
        PHASE="stopping MySQL"
        step "Shutting MySQL down cleanly"
        slow_shutdown "$MYSQL_CID" compose stop -t 900 "$MYSQL_SERVICE"
        ok "MySQL $CUR_VERSION stopped cleanly."
    fi

    if [ ${#HOPS[@]} -gt 0 ]; then
        if [ "$DATA_ARCHIVE" = 1 ]; then
            PHASE="archiving MySQL's data"
            step "Archiving MySQL's data directory (the rollback point)"
            docker run --rm -v "$(data_mount_arg)" -v "$RUN_DIR:/backup" --entrypoint sh "$TARGET_MYSQL_IMAGE" -c \
                "tar -C $DATADIR --numeric-owner -czf /backup/mysql-data.tar.gz . && chown $(id -u):$(id -g) /backup/mysql-data.tar.gz && chmod 600 /backup/mysql-data.tar.gz"
            gzip -t "$RUN_DIR/mysql-data.tar.gz" || die "The data archive is damaged."
            set_state ARCHIVE "$RUN_DIR/mysql-data.tar.gz"
            ok "Archived to mysql-data.tar.gz ($(du -k "$RUN_DIR/mysql-data.tar.gz" | awk '{printf "%d MB", $1 / 1024}'))."
        fi

        PHASE="upgrading MySQL's data"
        n=0
        for image in "${HOPS[@]}"; do
            n=$((n + 1))
            version=${image#*:}
            step "Upgrading MySQL's data to $version ($n of ${#HOPS[@]})"
            flags=()
            [ "$(version_num "$version")" -ge 80400 ] && flags=("${TARGET_FLAGS[@]}")
            name="copilot-mysql-upgrade-$version-$$"
            hop=$(docker run -d --name "$name" --label "$HOP_LABEL=$PROJECT_DIR" "${MOUNT_ARGS[@]}" \
                "$image" ${flags[@]+"${flags[@]}"})
            if ! wait_mysql "$hop" "MySQL $version"; then
                docker logs "$hop" >"$RUN_DIR/mysql-$version.log" 2>&1 || true
                die "MySQL $version didn't come up on the data (its log: $RUN_DIR/mysql-$version.log)."
            fi
            got=$(server_version "$hop")
            [ "${got%%-*}" = "$version" ] || die "Expected MySQL $version, found $got."
            if [ "$n" -lt ${#HOPS[@]} ] && [ "$RUN_CHECKER" = 1 ]; then
                info "Running the upgrade checker for MySQL ${HOPS[$n]#*:}..."
                report=$(run_checker "$hop" "${HOPS[$n]#*:}" || true)
                printf '%s\n' "$report" >"$RUN_DIR/upgrade-checker-$version.txt"
                errors=$(checker_errors "$report")
                [ "$errors" = 0 ] || die "The upgrade checker found ${errors:-unknown} error(s) on MySQL $version: see $RUN_DIR/upgrade-checker-$version.txt."
            fi
            slow_shutdown "$hop" docker stop -t 900 "$hop"
            docker logs "$hop" >"$RUN_DIR/mysql-$version.log" 2>&1 || true
            docker rm "$hop" >/dev/null
            ok "MySQL's data is now MySQL $version's."
            set_state DATA_VERSION "$version"
        done
    fi

    if [ "$NEEDS_COMPOSE_EDIT" = 1 ]; then
        PHASE="updating docker-compose.yml"
        step "Updating $(basename "$COMPOSE_FILE_PATH")"
        cat "$PATCHED_TMP" >"$COMPOSE_FILE_PATH"
        rm -f "$PATCHED_TMP"
        set_state COMPOSE_PATCHED 1
        ok "$MYSQL_SERVICE now runs $NEW_IMAGE with ${TARGET_FLAGS[*]} (the old file: $RUN_DIR/$(basename "$COMPOSE_FILE_PATH").before)."
    fi

    PHASE="starting MySQL"
    step "Starting MySQL"
    compose up -d --no-deps "$MYSQL_SERVICE" >/dev/null
    MYSQL_CID=$(service_container "$MYSQL_SERVICE")
    wait_mysql "$MYSQL_CID" "MySQL" || die "MySQL didn't start."
    NOW_VERSION=$(server_version "$MYSQL_CID")
    if [ ${#HOPS[@]} -gt 0 ] && [ "${NOW_VERSION%%-*}" != "${HOPS[$((${#HOPS[@]} - 1))]#*:}" ]; then
        die "Expected MySQL ${HOPS[$((${#HOPS[@]} - 1))]#*:}, found $NOW_VERSION."
    fi
    if [ "$(version_num "$NOW_VERSION")" -ge 80400 ]; then
        fk=$(sql "$MYSQL_CID" "SELECT @@GLOBAL.restrict_fk_on_non_standard_key")
        native=$(sql "$MYSQL_CID" "SELECT plugin_status FROM information_schema.plugins WHERE plugin_name = 'mysql_native_password'")
        [ "$fk" = 0 ] || die "MySQL runs without --restrict-fk-on-non-standard-key=OFF."
        [ "$native" = "ACTIVE" ] || die "MySQL runs without --mysql-native-password=ON."
    fi
    set_state NEW_VERSION "$NOW_VERSION"
    ok "MySQL $NOW_VERSION is up."
fi

PHASE="starting CoPilot"
step "Starting CoPilot"
for l in ${LEFTOVERS[@]+"${LEFTOVERS[@]}"}; do
    if docker rm -f "${l#* }" >/dev/null 2>&1; then
        info "Removed the ${l%% *} container: CoPilot no longer has ${l%% *}."
    else
        warn "Couldn't remove the ${l%% *} container. Remove it with: docker rm -f ${l#* }"
    fi
done
since=$(($(date +%s) - 5))
compose up -d
info "Waiting for the backend to start and run its database migrations..."
deadline=$(($(date +%s) + BACKEND_TIMEOUT))
result=""
watched=""
while [ -z "$result" ]; do
    cid=$(service_container "$BACKEND_SERVICE")
    if [ -n "$cid" ]; then
        if container_running "$cid" && backend_answers "$cid"; then
            result="up"
            break
        fi
        result=$(docker logs --since "$since" "$cid" 2>&1 |
            grep -Eo 'Error applying migrations|Application startup failed' | head -n1 || true)
        # A backend that dies before it logs anything useful (a bad .env, say) only restarts.
        restarts=$(docker inspect -f '{{.RestartCount}}' "$cid" 2>/dev/null || echo 0)
        if [ "$cid" != "$watched" ]; then
            watched=$cid
            first_restarts=$restarts
        fi
        [ -z "$result" ] && [ $((restarts - first_restarts)) -ge 3 ] && result="it keeps restarting"
    fi
    if [ -z "$result" ]; then
        [ "$(date +%s)" -lt "$deadline" ] || result="it didn't answer within ${BACKEND_TIMEOUT}s"
        sleep 5
    fi
done
if [ "$result" != "up" ]; then
    warn "The backend's last log lines:"
    docker logs --since "$since" --tail 30 "$cid" >&2 2>&1 || true
    die "The backend didn't start ($result). See: ${COMPOSE[*]} logs $BACKEND_SERVICE"
fi
ok "The backend is up."
migration_warnings=$(docker logs --since "$since" "$cid" 2>&1 | grep -E 'holds duplicate values|left as it is' || true)

PHASE="done"
set_state STATUS completed
step "Done"
if [ "$HAS_MYSQL" = 1 ]; then
    echo "  MySQL $CUR_VERSION -> $(get_state "$STATE_FILE" NEW_VERSION)"
    revision=$(sql "$MYSQL_CID" "SELECT version_num FROM copilot.alembic_version" 2>/dev/null | head -n1 || true)
    [ -n "$revision" ] && echo "  Database migrations at: $revision"
fi
echo "  Backups and log: $RUN_DIR"
if [ -n "$migration_warnings" ]; then
    warn "The backend's migrations left a warning:"
    printf '%s\n' "$migration_warnings" >&2
fi
compose ps
echo
echo "The backups hold CoPilot's data and credentials: keep them safe, and delete them once you no longer need to go back."
[ -f "$RUN_DIR/mysql-data.tar.gz" ] && echo "To go back to where you started: ./upgrade.sh --rollback $RUN_DIR"
exit 0
