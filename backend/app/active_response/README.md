Windows custom active response configuration

You can implement the custom Python script on Windows endpoints using two methods. The first method converts Python scripts to executable applications, while the second method uses a Windows Batch launcher to run the Python script.

Both methods require Python installed on the Windows endpoint. Use the following steps below to install Python on the Windows endpoint.

#. Download Python executable installer from the `official Python website <https://www.python.org/downloads/windows/>`\_\_.
#. Run the Python installer once downloaded. Check the following boxes when prompted and start the installation:

-   **Use admin privileges when installing py.exe**.
-   **Add python.exe to PATH**. This places the interpreter in the execution path.

Or you can use the following PowerShell command to install Python:

```
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe" -OutFile "$env:TEMP\python-3.11.0-amd64.exe"; Start-Process -FilePath "$env:TEMP\python-3.11.0-amd64.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait -NoNewWindow
```

Method 1: Convert the Python script to an executable application
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

#. Open an administrator PowerShell terminal and use `pip` to install `pyinstaller`:

      > pip install pyinstaller
      > pyinstaller --version

#. Run the following command using PowerShell with administrator privileges to create the executable file:

❗ - Make sure to point to the Wazuh DLLs

```powershell
pyinstaller --log-level DEBUG --add-data "C:\Program Files (x86)\ossec-agent\libwazuhext.dll;." --add-data "C:\Program Files (x86)\ossec-agent\libwinpthread-1.dll;." --add-data "C:\Program Files (x86)\ossec-agent\libwazuhshared.dll;." -F <PATH_TO_CUSTOM-AR.PY>
```

You can find the created `custom-ar.exe` executable in the `C:\Users\<USER>\dist\` directory.

#. Copy the `custom-ar.exe` executable file to `C:\Program Files (x86)\ossec-agent\active-response\bin\` directory on the monitored endpoint.
#. Restart the Wazuh agent using PowerShell with administrator privileges to apply the changes:

.. code-block:: console

      > Restart-Service -Name wazuh

#. On the Wazuh server, add the `<command>` and `<active-response>` blocks below to the `/var/ossec/etc/ossec.conf` configuration file. This uses the `custom-ar.exe` executable for Windows endpoints.

```xml
<command>
    <name>windows_firewall</name>
    <executable>windows_firewall.exe</executable>
    <timeout_allowed>no</timeout_allowed>
  </command>

  <active-response>
    <disabled>no</disabled>
    <command>windows_firewall</command>
    <location>local</location>
    <timeout>60</timeout>
  </active-response>
```

## Weekly Sysmon noise statistics (`services/sysmon_stats/`)

Each CoPilot sends SOCFortress's sysmon-sync one redacted report per customer per ISO week (`POST /v1/sysmon/report`,
contract v1, with the license key; the base URL is `SOCFORTRESS_SYSMON_SYNC_URL`, shared with the default-config pull).
SOCFortress turns patterns seen across many CoPilots into reviewed exclusions in the installer repository.

- **Loop**: the `send_sysmon_stats` job (every 6 h, admin-only) sends each customer's previous complete ISO week once,
  after a jittered send time (Monday 01:00 to Tuesday 24:00 UTC, deterministic per CoPilot and customer). State per
  customer and week lives in MinIO (`sysmon-config-defaults/stats-state.json`); a MySQL named lock lets one replica send.
- **Switches**: `SYSMON_STATS_SHARING=off` stops every query and request (empty follows `SYSMON_DEFAULT_SYNC`; an
  unknown value is off). Per customer, sharing is on unless an admin opts it out (`sysmon_stats_customer_settings`);
  an opt-out queues a withdraw (`stats-withdraw/<pseudonym>.json`) that asks SOCFortress to delete the reports.
- **What is sent**: only events of alerts at Wazuh rule level 5 or lower, only patterns on 3 or more endpoints, at most
  70 patterns of at most 5 fields. Never a command line, a destination IP, an internal DNS name (single-label, private
  suffixes, the customer's own domains, IPs in names) or anything the vendored contract (`contract_v1.py`) refuses.
  Values are redacted with the contract's placeholders (`redaction.py`, `dns_policy.py`) or the pattern is dropped.
- **Indexer**: aggregations only, in the heavy-query slot shared with the firing-stats cache, two stages per customer,
  bounded sizes and budgets; events are attributed only by their customer label (case-insensitive), never guessed.
- **Admin routes** (`/api/sysmon_config/stats`): `GET` status, `PUT /customers/{code}` sharing and hints,
  `POST /customers/{code}/preview` (the exact payload; sends nothing), `POST /send-now`. Audit actions
  `response.sysmon_stats_send|sharing|withdraw|resume` carry hashes and counts, never values or the license key.
- **sysmon-sync answering 404 "reports are not enabled"** (reports switched off there) is a quiet state: no indexer
  query, no audit row, one INFO line when it changes. A report refused for its content (422 `identity-leak`,
  `command-line`, `field-not-allowed`) pauses every report until the CoPilot version changes or an admin resumes.
