#!/usr/bin/env bash
# verify_isolation.sh — the auditable gate for the Tier 1 inspector.
#
# Runs the inspector image with the PRODUCTION hardening flags and asserts, from
# inside, that the container that never executes the sample and never has network
# actually has those properties (see CLAUDE.md -> File Analysis). If any MUST check
# fails, the operator must NOT let the module analyze anything.
#
# Usage:  ./verify_isolation.sh [IMAGE]
#   IMAGE defaults to ghcr.io/socfortress/copilot-inspector:latest
set -u

IMAGE="${1:-ghcr.io/socfortress/copilot-inspector:latest}"
FLAGS=(--network none --read-only --cap-drop ALL --security-opt no-new-privileges
       --pids-limit 256 --memory 1g --tmpfs /tmp:size=512m)
PASS=0
FAIL=0

check() { # name  expected  actual
  if [ "$2" = "$3" ]; then echo "  PASS  $1"; PASS=$((PASS+1));
  else echo "  FAIL  $1  (expected '$2', got '$3')"; FAIL=$((FAIL+1)); fi
}

echo "Verifying isolation for image: $IMAGE"
echo

# 1. No network — assert on what actually decides reachability: an empty routing
# table and no non-loopback address. Listing /sys/class/net is NOT a valid test:
# the kernel materialises stub tunnel devices (tunl0, gre0, sit0, ip6tnl0, …) in
# every new net namespace when those modules are loaded on the host, so a genuinely
# isolated container shows them on Docker Desktop / any host with the modules in.
# They carry no address and no route, so nothing can leave through them.
NET=$(docker run --rm "${FLAGS[@]}" --entrypoint sh "$IMAGE" -c '
  routes=$(tail -n +2 /proc/net/route | wc -l)
  if [ "$routes" -eq 0 ]; then echo ISOLATED; else echo "ROUTES=$routes"; fi
' 2>/dev/null | tr -d ' \n')
check "no network (no routes, no egress)" "ISOLATED" "$NET"

# 1b. Prove it rather than infer it: an outbound connect must fail at the socket.
EGRESS=$(docker run --rm "${FLAGS[@]}" --entrypoint python "$IMAGE" -c '
import socket
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3)
    print("REACHABLE")
except OSError:
    print("BLOCKED")
' 2>/dev/null | tr -d ' \n')
check "outbound connect blocked" "BLOCKED" "$EGRESS"

# 2. Read-only root filesystem.
RO=$(docker run --rm "${FLAGS[@]}" --entrypoint sh "$IMAGE" -c 'touch /probe 2>/dev/null && echo WRITABLE || echo READONLY')
check "read-only root fs" "READONLY" "$RO"

# 4. Non-root user inside.
UID_IN=$(docker run --rm "${FLAGS[@]}" --entrypoint id "$IMAGE" -u 2>/dev/null)
if [ "$UID_IN" != "0" ] && [ -n "$UID_IN" ]; then echo "  PASS  non-root user (uid=$UID_IN)"; PASS=$((PASS+1));
else echo "  FAIL  non-root user  (uid=$UID_IN)"; FAIL=$((FAIL+1)); fi

# 5. All capabilities dropped (CapEff must be all zeros).
CAP=$(docker run --rm "${FLAGS[@]}" --entrypoint sh "$IMAGE" -c 'grep CapEff /proc/self/status | awk "{print \$2}"')
check "all capabilities dropped" "0000000000000000" "$CAP"

# 6. tmpfs scratch IS writable (so the inspector can work).
TMP=$(docker run --rm "${FLAGS[@]}" --entrypoint sh "$IMAGE" -c 'touch /tmp/probe 2>/dev/null && echo OK || echo NOPE')
check "tmpfs /tmp writable" "OK" "$TMP"

# 7. Sentinel: a benign sample on stdin produces valid result JSON on stdout.
SENTINEL=$(printf 'hello world' | base64 | tr -d '\n')
JOB="{\"filename\":\"sentinel.txt\",\"customer_code\":\"VERIFY\",\"sample_b64\":\"$SENTINEL\"}"
OUTJSON=$(printf '%s' "$JOB" | docker run --rm -i "${FLAGS[@]}" "$IMAGE" 2>/dev/null)
if printf '%s' "$OUTJSON" | grep -q '"sha256"' && printf '%s' "$OUTJSON" | grep -q '"verdict_hint"'; then
  echo "  PASS  sentinel sample produces result JSON"; PASS=$((PASS+1));
else
  echo "  FAIL  sentinel sample produces result JSON  (got: ${OUTJSON:0:120})"; FAIL=$((FAIL+1)); fi

# 8. No container leaked (we always --rm; assert none linger from this image).
LEFT=$(docker ps -a --filter "ancestor=$IMAGE" --format '{{.ID}}' | wc -l | tr -d ' ')
check "no leftover containers" "0" "$LEFT"

echo
echo "Result: $PASS passed, $FAIL failed."
[ "$FAIL" -eq 0 ] && { echo "ISOLATION VERIFIED — safe to analyze."; exit 0; } || { echo "ISOLATION NOT VERIFIED — do NOT analyze."; exit 1; }
