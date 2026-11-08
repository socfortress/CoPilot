# Sysmon config reload, run once a day by the agent.conf wodle "sysmon-reload" (and by the
# active response run_sysmon_config_reload.cmd).
#
# This file contains no per-customer tokens, so the same file works in two places: the installer's copy in
# active-response\bin, and a copy pushed through the agent-group shared folder. The shared copy reaches
# existing endpoints without a reinstall; see wazuh/README.md.
#
# It applies C:\Program Files (x86)\ossec-agent\shared\sysmon_config.xml, which the Wazuh manager's agent
# group pushes, to the running Sysmon. Every step writes one JSON line to active-responses.log, and the
# manager's rule 200070 matches on "group":"SysmonConfigReload".
#
# Unlike the previous version, a run only reports "completed" when the reload actually worked:
#   * the Sysmon service must exist. If it is stopped, we start it without blocking, wait at most 30 s,
#     and report a "warning" summary (restarted) or "error" (could not start).
#   * the config must be well-formed XML with a <Sysmon> root, so a broken push never reaches Sysmon.
#   * the reload uses the binary the service actually runs, so the version always matches the driver.
#     Its exit code is checked, and a non-zero code is reported as "error" together with Sysmon's own output.
#   * the summary line carries the config SHA256 and the Sysmon version, so the SIEM can tell which config
#     each endpoint runs.
# Statuses: completed | warning | error (the service-check step can also report "restarted").

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$WarningPreference  = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.ServiceProcess   # Windows PowerShell 5.1 resolves [System.ServiceProcess.*] only once loaded

$logFile         = "C:\Program Files (x86)\ossec-agent\active-response\active-responses.log"
$configPath      = "C:\Program Files (x86)\ossec-agent\shared\sysmon_config.xml"
$serviceNames    = @('Sysmon64', 'Sysmon64a', 'Sysmon')

function Log-Step {
    param (
        [string]$stepName,
        [string]$status,
        [string]$details = "",
        [System.Collections.IDictionary]$extra = @{}
    )
    try {
        $payload = [ordered]@{
            group         = 'SysmonConfigReload'
            step          = $stepName
            status        = $status
            details       = $details
            executionTime = $stopwatch.Elapsed.ToString()
        }
        foreach ($k in $extra.Keys) { $payload[$k] = $extra[$k] }
        ($payload | ConvertTo-Json -Compress) | Out-File -Append -Encoding ascii $logFile
    } catch {
        Write-Host "Failed to log $stepName. Error: $_"
    }
}

function Get-SysmonService {
    foreach ($name in $serviceNames) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc) { return $svc }
    }
    return $null
}

function Reload-SysmonConfig {
    $summary = [ordered]@{ service = $null; service_state = $null; sysmon_version = $null; config_sha256 = $null; loaded_config_hash = $null; exit_code = $null }
    $overall = 'completed'

    # 1. Service present and running?
    $svc = Get-SysmonService
    if (-not $svc) {
        Log-Step -stepName 'Check Sysmon Service' -status 'error' -details ('No Sysmon service found (' + ($serviceNames -join ', ') + '); nothing to reload')
        return
    }
    $summary.service = $svc.Name
    $runningState = [System.ServiceProcess.ServiceControllerStatus]::Running
    if ($svc.Status -ne $runningState) {
        $prev = [string]$svc.Status
        try {
            # ServiceController.Start() does not block (Start-Service can hang on StartPending), so the
            # 30 s timeout always applies.
            $svc.Refresh()
            if ($svc.Status -ne $runningState -and $svc.Status -ne [System.ServiceProcess.ServiceControllerStatus]::StartPending) {
                # The watchdog, or an SCM recovery restart, may be starting it at the same moment.
                try { $svc.Start() } catch { $svc.Refresh(); if ($svc.Status -ne $runningState -and $svc.Status -ne [System.ServiceProcess.ServiceControllerStatus]::StartPending) { throw } }
            }
            $svc.WaitForStatus($runningState, [TimeSpan]::FromSeconds(30))
            Log-Step -stepName 'Check Sysmon Service' -status 'restarted' -details "Service $($svc.Name) was $prev; started it"
            $overall = 'warning'
        } catch {
            $msg = $_.Exception.GetBaseException().Message
            $svc.Refresh()
            Log-Step -stepName 'Check Sysmon Service' -status 'error' -details "Service $($svc.Name) is $($svc.Status) (was $prev) and could not be started: $msg"
            return
        }
    } else {
        Log-Step -stepName 'Check Sysmon Service' -status 'completed' -details "Service $($svc.Name) is Running"
    }
    $svc.Refresh()
    $summary.service_state = [string]$svc.Status

    # 2. Use the binary the service actually runs (normally C:\Windows\Sysmon64.exe), so its version matches
    #    the loaded driver. Read the path from the service's registry ImagePath, falling back to WMI.
    $sysmonPath = $null
    foreach ($source in 'registry', 'wmi') {
        try {
            if ($source -eq 'registry') {
                $p = (Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\$($svc.Name)" -Name ImagePath -ErrorAction Stop).ImagePath
            } else {
                $p = (Get-WmiObject -Class Win32_Service -Filter "Name='$($svc.Name)'").PathName
            }
            $p = ([string]$p -replace '"', '').Trim()
            if ($p -and (Test-Path -LiteralPath $p)) { $sysmonPath = $p; break }
        } catch { }
    }
    if (-not $sysmonPath) {
        Log-Step -stepName 'Check Sysmon Path' -status 'error' -details "Cannot find the executable of service $($svc.Name)"
        return
    }
    try { $summary.sysmon_version = (Get-Item -LiteralPath $sysmonPath).VersionInfo.ProductVersion } catch { }

    # 3. Config present and well-formed?
    if (-not (Test-Path -LiteralPath $configPath)) {
        Log-Step -stepName 'Check Config Path' -status 'error' -details "Sysmon config file not found at $configPath"
        return
    }
    try {
        $summary.config_sha256 = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash
        [xml]$xml = Get-Content -LiteralPath $configPath -Raw -ErrorAction Stop
        if (-not $xml.Sysmon) { throw 'root element is not <Sysmon>' }
    } catch {
        Log-Step -stepName 'Validate Config' -status 'error' -details "Config is not valid Sysmon XML, not applied: $($_.Exception.Message)" -extra @{ config_sha256 = $summary.config_sha256 }
        return
    }

    # 4. Reload, and check the exit code. Sysmon prints why it rejects a config (for example an
    #    unsupported schemaversion) on stdout.
    try {
        $output = & $sysmonPath -accepteula -c $configPath 2>&1 | Out-String
        $code = $LASTEXITCODE
        $summary.exit_code = $code
        $output = ($output -replace '\s+', ' ').Trim()
        if ($output.Length -gt 900) { $output = $output.Substring(0, 900) + '...' }
        if ($code -ne 0) {
            Log-Step -stepName 'Reload Sysmon Config' -status 'error' -details "Sysmon exited with code $code. $output" -extra @{ exit_code = $code; config_sha256 = $summary.config_sha256; sysmon_version = $summary.sysmon_version }
            return
        }
        Log-Step -stepName 'Reload Sysmon Config' -status 'completed' -details $output -extra @{ exit_code = $code }
    } catch {
        Log-Step -stepName 'Reload Sysmon Config' -status 'error' -details "An error occurred while reloading Sysmon configuration: $($_.Exception.Message)"
        return
    }

    # 5. Post-checks: the service is still running, and (best effort) the hash the driver recorded.
    $svc.Refresh()
    $summary.service_state = [string]$svc.Status
    if ($svc.Status -ne [System.ServiceProcess.ServiceControllerStatus]::Running) {
        Log-Step -stepName 'Verify Sysmon Service' -status 'error' -details "Service $($svc.Name) is $($svc.Status) after the reload"
        return
    }
    try {
        $params = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Services\SysmonDrv\Parameters' -ErrorAction Stop
        if ($params.PSObject.Properties.Name -contains 'ConfigHash') { $summary.loaded_config_hash = [string]$params.ConfigHash }
    } catch { }

    Log-Step -stepName 'Summary' -status $overall -details 'Sysmon config reload finished' -extra $summary
}

try {
    Reload-SysmonConfig
} catch {
    Log-Step -stepName 'Summary' -status 'error' -details "Unexpected failure: $($_.Exception.Message)"
}
$stopwatch.Stop()
