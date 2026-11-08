<#
.SYNOPSIS
    Sysmon liveness watchdog, run by the Wazuh agent as a wodle "command" (SYSTEM, every 15 minutes).

.DESCRIPTION
    The script reaches every Windows endpoint through the Wazuh manager's agent-group shared folder, so
    no reinstall is needed. The agent syncs it to C:\Program Files (x86)\ossec-agent\shared\, which only
    Administrators and SYSTEM can write. See wazuh/README.md.

    Each run:
      1. Finds the Sysmon service (Sysmon64, Sysmon64a or Sysmon) and checks its state.
           not installed                -> "missing"
           Stopped                      -> start it and wait up to StartTimeoutSeconds -> "restarted" | "restart_failed"
           StartPending                 -> wait up to StartTimeoutSeconds              -> ok | "start_pending"
           Running, no new event in the Sysmon/Operational log for StaleMinutes        -> "stale"
      2. Tries to make the SCM restart Sysmon by itself next time ("sc failure"). Endpoints installed
         before Phase 0 never got this from the installer. The FailureActions value is checked first,
         and an attempt is made at most once a day. Sysmon 15+ runs as a PROTECTED service, and the
         SCM refuses this change even to SYSTEM (exit code 5, verified on the lab endpoint). The
         watchdog remembers that, reports recovery "unsupported" without alerting, and stops trying.
         On those endpoints its own restart (step 1) is the recovery mechanism.
      3. Prints exactly ONE JSON line, which Wazuh's built-in JSON decoder parses:
           {"sysmon_watchdog":{"status":"...","service":"Sysmon64","state":"Running",...}}

    Noise control. A stateless watchdog would repeat the same alert every run, and Wazuh cannot rate-limit
    per agent. So the last reported status and time are kept under
    HKLM\SOFTWARE\socfortress\SysmonWatchdog. Wazuh's agent is 32-bit, so on 64-bit Windows this is
    HKLM\SOFTWARE\WOW6432Node\socfortress\SysmonWatchdog, which only Administrators and SYSTEM can write.
      * A failing status is reported when it first appears and every RepeatHours after that. Runs in
        between report "suppressed" (level 0). Once an hour one of them carries heartbeat_due=true, and a
        level-3 rule stores it, so an endpoint in a lasting failure still shows that its watchdog is alive.
      * The first healthy run after a failure reports "recovered".
      * A healthy endpoint reports "heartbeat" about once an hour (level 3, stored). This lets the SIEM
        notice an endpoint whose watchdog has stopped reporting. Other healthy runs report "ok" (level 0).

    "stale" only means Sysmon wrote nothing at all for StaleMinutes. The watchdog's own PowerShell
    launch normally creates Sysmon events just before the check, so a working sensor always looks fresh.
    It cannot detect a cleared log; System EID 104 and Security EID 1102 cover that.

    The script writes no files and uses no temp paths. Apart from its own registry state, the only thing
    it changes is the start state and recovery settings of an existing Sysmon service.
#>
[CmdletBinding()]
param(
    [string[]]$ServiceNames = @('Sysmon64', 'Sysmon64a', 'Sysmon'),
    [int]$StaleMinutes = 120,
    [int]$StartTimeoutSeconds = 30,
    [int]$RepeatHours = 6,
    [int]$HeartbeatMinutes = 60
)

$ErrorActionPreference = 'Stop'
$WarningPreference     = 'SilentlyContinue'   # keep stdout to the single JSON line
$ProgressPreference    = 'SilentlyContinue'

$stateKey = 'HKLM:\SOFTWARE\socfortress\SysmonWatchdog'
$now      = [DateTime]::UtcNow

$result = [ordered]@{
    status             = 'ok'
    service            = $null
    state              = $null
    prev_state         = $null
    version            = $null
    last_event_age_min = $null
    recovery           = $null
    suppressed_status  = $null
    heartbeat_due      = $false
    detail             = $null
}

function Get-State([string]$name) {
    try { return (Get-ItemProperty -LiteralPath $stateKey -Name $name -ErrorAction Stop).$name } catch { return $null }
}
function Set-State([string]$name, [string]$value) {
    try {
        if (-not (Test-Path -LiteralPath $stateKey)) { New-Item -Path $stateKey -Force | Out-Null }
        Set-ItemProperty -LiteralPath $stateKey -Name $name -Value $value
    } catch { }
}
function Get-StateTime([string]$name) {
    $v = Get-State $name
    if (-not $v) { return $null }
    try { return [DateTime]::Parse($v, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AdjustToUniversal -bor [Globalization.DateTimeStyles]::AssumeUniversal) } catch { return $null }
}

# True if the service already has at least one "restart" failure action (SC_ACTION type 1).
# Registry layout of FailureActions: DWORD reset, DWORD rebootMsg, DWORD command, DWORD cActions,
# DWORD actionsPtr, then cActions x { DWORD type, DWORD delay }.
function Test-RestartRecovery([string]$serviceName) {
    try {
        $blob = (Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\$serviceName" -Name FailureActions -ErrorAction Stop).FailureActions
        if (-not $blob -or $blob.Length -lt 28) { return $false }
        $count = [BitConverter]::ToUInt32($blob, 12)
        for ($i = 0; $i -lt $count; $i++) {
            $off = 20 + (8 * $i)
            if ($off + 4 -gt $blob.Length) { break }
            if ([BitConverter]::ToUInt32($blob, $off) -eq 1) { return $true }
        }
        return $false
    } catch { return $false }
}

try {
    # Windows PowerShell 5.1 resolves [System.ServiceProcess.*] only from already-loaded assemblies, and a
    # fresh -NoProfile session has not loaded it yet. So load it explicitly before the first type reference.
    Add-Type -AssemblyName System.ServiceProcess
    $running = [System.ServiceProcess.ServiceControllerStatus]::Running

    # ---- 1. Service state ------------------------------------------------------------------
    $svc = $null
    foreach ($name in $ServiceNames) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc) { break }
    }

    if (-not $svc) {
        $result.status = 'missing'
        $result.detail = 'No Sysmon service found (' + ($ServiceNames -join ', ') + ')'
    }
    else {
        $result.service = $svc.Name
        $result.state   = [string]$svc.Status

        try {
            $imagePath = (Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\$($svc.Name)" -Name ImagePath -ErrorAction Stop).ImagePath
            $exe = ([string]$imagePath -replace '"', '').Trim()
            if ($exe -and (Test-Path -LiteralPath $exe)) { $result.version = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion }
        } catch { }

        if ($svc.Status -eq [System.ServiceProcess.ServiceControllerStatus]::StopPending) {
            try { $svc.WaitForStatus([System.ServiceProcess.ServiceControllerStatus]::Stopped, [TimeSpan]::FromSeconds(15)) } catch { }
            $svc.Refresh()
        }

        if ($svc.Status -eq [System.ServiceProcess.ServiceControllerStatus]::StartPending) {
            # Already starting (boot, or an SCM recovery restart in progress): wait, do not start it again.
            try {
                $svc.WaitForStatus($running, [TimeSpan]::FromSeconds($StartTimeoutSeconds))
            } catch {
                $result.status = 'start_pending'
                $result.detail = "Service has been StartPending for more than $StartTimeoutSeconds seconds"
            }
            $svc.Refresh()
            $result.state = [string]$svc.Status
        }
        elseif ($svc.Status -ne $running) {
            # Stopped (crashed) or another non-running state: start it. ServiceController.Start() does
            # not block. Unlike Start-Service it cannot hang on StartPending, so the timeout always applies.
            $result.prev_state = [string]$svc.Status
            try {
                $svc.Refresh()
                # The reload script, or an SCM recovery restart, may already be starting it.
                if ($svc.Status -ne $running -and $svc.Status -ne [System.ServiceProcess.ServiceControllerStatus]::StartPending) {
                    try { $svc.Start() } catch { $svc.Refresh(); if ($svc.Status -ne $running -and $svc.Status -ne [System.ServiceProcess.ServiceControllerStatus]::StartPending) { throw } }
                }
                $svc.WaitForStatus($running, [TimeSpan]::FromSeconds($StartTimeoutSeconds))
                $svc.Refresh()
                $result.state  = [string]$svc.Status
                $result.status = 'restarted'
            }
            catch {
                $svc.Refresh()
                $result.state  = [string]$svc.Status
                $result.status = 'restart_failed'
                $result.detail = $_.Exception.GetBaseException().Message
            }
        }

        if ($result.status -eq 'ok') {
            # Running: confirm the sensor is still writing events at all.
            try {
                $last = Get-WinEvent -LogName 'Microsoft-Windows-Sysmon/Operational' -MaxEvents 1 -ErrorAction Stop
                $age = [math]::Round(((Get-Date) - $last.TimeCreated).TotalMinutes, 1)
                $result.last_event_age_min = $age
                if ($age -gt $StaleMinutes) {
                    $result.status = 'stale'
                    $result.detail = "No Sysmon event for $age minutes (threshold $StaleMinutes)"
                }
            }
            catch {
                $result.status = 'stale'
                $result.detail = 'Cannot read Microsoft-Windows-Sysmon/Operational: ' + $_.Exception.Message
            }
        }

        # ---- 2. SCM restart-on-failure (once per endpoint) ------------------------------------
        if (Test-RestartRecovery $svc.Name) {
            $result.recovery = 'present'
        }
        elseif ((Get-State 'RecoveryUnsupported') -eq '1') {
            # Sysmon 15+ runs as a protected service: the SCM denies "sc failure" even to SYSTEM
            # (exit code 5). Learned once per endpoint; the watchdog's own restart covers it instead.
            $result.recovery = 'unsupported'
        }
        else {
            $lastAttempt = Get-StateTime 'RecoveryAttemptUtc'
            if (-not $lastAttempt -or ($now - $lastAttempt).TotalHours -ge 24 -or ($now - $lastAttempt).TotalHours -lt 0) {
                Set-State 'RecoveryAttemptUtc' $now.ToString('o')
                $sc = Join-Path $env:SystemRoot 'System32\sc.exe'
                & $sc failure $svc.Name 'reset=' '86400' 'actions=' 'restart/60000/restart/60000/restart/300000' | Out-Null
                $codeFailure = $LASTEXITCODE
                & $sc failureflag $svc.Name '1' | Out-Null
                $codeFlag = $LASTEXITCODE
                if (($codeFailure -eq 0) -and (Test-RestartRecovery $svc.Name)) {
                    $result.recovery = 'configured'
                } elseif ($codeFailure -eq 5) {
                    # ERROR_ACCESS_DENIED: protected service (Sysmon 15+). Not a fault; stop trying.
                    Set-State 'RecoveryUnsupported' '1'
                    $result.recovery = 'unsupported'
                } else {
                    $result.recovery = "failed (sc failure $codeFailure, failureflag $codeFlag)"
                }
            }
            else {
                $result.recovery = 'absent'
            }
        }
    }
}
catch {
    $result.status = 'unknown_error'
    $result.detail = $_.Exception.Message
}

# ---- 3. De-duplicate and heartbeat (per endpoint) ----------------------------------------------
try {
    $failing    = @('missing', 'restart_failed', 'start_pending', 'stale', 'unknown_error')
    $lastStatus = Get-State 'LastStatus'
    $lastReport = Get-StateTime 'LastReportUtc'

    if ($failing -contains $result.status) {
        $sinceReport = if ($lastReport) { ($now - $lastReport).TotalHours } else { -1 }
        if (($lastStatus -eq $result.status) -and ($sinceReport -ge 0) -and ($sinceReport -lt $RepeatHours)) {
            $result.suppressed_status = $result.status
            $result.status = 'suppressed'
            # Stay visible as alive while failing: once an hour a suppressed run is marked heartbeat_due,
            # and a level-3 rule stores it, so "no stored watchdog event in 2 h" still means a dead watchdog.
            $lastBeat = Get-StateTime 'HeartbeatUtc'
            $sinceBeat = if ($lastBeat) { ($now - $lastBeat).TotalMinutes } else { -1 }
            if ($sinceBeat -lt 0 -or $sinceBeat -ge ($HeartbeatMinutes - 2)) {
                $result.heartbeat_due = $true
                Set-State 'HeartbeatUtc' $now.ToString('o')
            }
        } else {
            Set-State 'LastStatus' $result.status
            Set-State 'LastReportUtc' $now.ToString('o')
        }
    }
    elseif ($result.status -eq 'restarted') {
        # Always reported. The service is healthy again, so clear the failure state.
        Set-State 'LastStatus' 'ok'
    }
    else {
        # ok
        if ($lastStatus -and ($failing -contains $lastStatus)) {
            $result.status = 'recovered'
            $result.detail = "Previously $lastStatus"
            Set-State 'LastStatus' 'ok'
            Set-State 'HeartbeatUtc' $now.ToString('o')
        }
        elseif ($result.recovery -eq 'configured') {
            $result.status = 'heartbeat'
            Set-State 'HeartbeatUtc' $now.ToString('o')
        }
        else {
            $lastBeat = Get-StateTime 'HeartbeatUtc'
            $sinceBeat = if ($lastBeat) { ($now - $lastBeat).TotalMinutes } else { -1 }
            if ($sinceBeat -lt 0 -or $sinceBeat -ge ($HeartbeatMinutes - 2)) {
                $result.status = 'heartbeat'
                Set-State 'HeartbeatUtc' $now.ToString('o')
            }
        }
    }
} catch { }

@{ sysmon_watchdog = $result } | ConvertTo-Json -Compress
