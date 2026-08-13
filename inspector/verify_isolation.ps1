# verify_isolation.ps1 — Windows/PowerShell version of the Tier 1 isolation gate.
# Runs the inspector image with the PRODUCTION hardening flags and asserts, from
# inside, that the container never has network and never runs as a privileged
# process (see CLAUDE.md -> File Analysis). Same checks as verify_isolation.sh.
#
# Usage:  powershell -ExecutionPolicy Bypass -File inspector\verify_isolation.ps1
#         (optional first arg: image name)
param([string]$Image = "ghcr.io/socfortress/copilot-inspector:latest")

$flags = @(
    '--network', 'none',
    '--read-only',
    '--cap-drop', 'ALL',
    '--security-opt', 'no-new-privileges',
    '--pids-limit', '256',
    '--memory', '1g',
    '--tmpfs', '/tmp:size=512m'
)

$script:pass = 0
$script:fail = 0
function Check($name, $expected, $actual) {
    if ("$actual" -eq "$expected") {
        Write-Host "  PASS  $name" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  FAIL  $name  (expected '$expected', got '$actual')" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "Verifying isolation for image: $Image`n"

# 1. No network — with --network none only loopback exists in the net namespace.
$net = (docker run --rm @flags --entrypoint sh $Image -c 'ls /sys/class/net' | Out-String).Trim() -replace '\s+', ' '
Check "no network (only loopback)" "lo" $net

# 2. Read-only root filesystem.
$ro = (docker run --rm @flags --entrypoint sh $Image -c 'touch /probe 2>/dev/null && echo WRITABLE || echo READONLY' | Out-String).Trim()
Check "read-only root fs" "READONLY" $ro

# 3. Non-root user inside.
$uid = (docker run --rm @flags --entrypoint id $Image -u | Out-String).Trim()
if ($uid -ne "0" -and $uid -ne "") {
    Write-Host "  PASS  non-root user (uid=$uid)" -ForegroundColor Green; $script:pass++
} else {
    Write-Host "  FAIL  non-root user (uid=$uid)" -ForegroundColor Red; $script:fail++
}

# 4. All capabilities dropped (CapEff must be all zeros).
$cap = (docker run --rm @flags --entrypoint sh $Image -c 'grep CapEff /proc/self/status' | Out-String).Trim()
if ($cap -like "*0000000000000000*") {
    Write-Host "  PASS  all capabilities dropped" -ForegroundColor Green; $script:pass++
} else {
    Write-Host "  FAIL  all capabilities dropped  (got '$cap')" -ForegroundColor Red; $script:fail++
}

# 5. tmpfs scratch IS writable (so the inspector can work).
$tmp = (docker run --rm @flags --entrypoint sh $Image -c 'touch /tmp/probe 2>/dev/null && echo OK || echo NOPE' | Out-String).Trim()
Check "tmpfs /tmp writable" "OK" $tmp

# 6. Sentinel: a benign sample on stdin produces valid result JSON on stdout.
$sentinel = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("hello world"))
$job = '{"filename":"sentinel.txt","customer_code":"VERIFY","sample_b64":"' + $sentinel + '"}'
$outjson = ($job | docker run --rm -i @flags $Image | Out-String)
if ($outjson -match '"sha256"' -and $outjson -match '"verdict_hint"') {
    Write-Host "  PASS  sentinel sample produces result JSON" -ForegroundColor Green; $script:pass++
} else {
    $preview = $outjson.Substring(0, [Math]::Min(120, $outjson.Length))
    Write-Host "  FAIL  sentinel sample produces result JSON  (got: $preview)" -ForegroundColor Red; $script:fail++
}

# 7. No leftover containers from this image (we always --rm).
$left = @(docker ps -a --filter "ancestor=$Image" --format "{{.ID}}").Count
Check "no leftover containers" 0 $left

Write-Host "`nResult: $($script:pass) passed, $($script:fail) failed."
if ($script:fail -eq 0) {
    Write-Host "ISOLATION VERIFIED - safe to analyze." -ForegroundColor Green
    exit 0
} else {
    Write-Host "ISOLATION NOT VERIFIED - do NOT analyze." -ForegroundColor Red
    exit 1
}
