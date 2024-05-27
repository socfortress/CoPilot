# Windows Firewall

## Description

Wazuh Active Response capable of creating a new rule in the Windows Firewall to block or unblock traffic to a specific IP address.

### Requirements

-   Python 3.11 or later installed on the Windows agent.
-   `windows_firewall.exe` - The executable file that will be used to create the rule in the Windows Firewall. Provided by SOCFortress at `https://repo.socfortress.co/repository/socfortress/active-response/windows_firewall.exe`.

-   Must be placed in the `C:\Program Files (x86)\ossec-agent\active-response\bin` directory on the Windows agent.

### Download Python 3.11

```powershell
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe" -OutFile "$env:TEMP\python-3.11.0-amd64.exe"; Start-Process -FilePath "$env:TEMP\python-3.11.0-amd64.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait -NoNewWindow
```

### Download Script Via PowerShell

```powershell
Invoke-WebRequest -Uri "https://repo.socfortress.co/repository/socfortress/active-response/windows_firewall.exe" -OutFile "C:\Program Files (x86)\ossec-agent\active-response\bin\windows_firewall.exe" -Credential (New-Object System.Management.Automation.PSCredential ("socfortress_installer", (ConvertTo-SecureString "6cV8uJqnQffDa3Upx" -AsPlainText -Force)))
```

## Wazuh Manager Configuration

The following configuration must be added to the `ossec.conf` file on the Wazuh manager.

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

#. Create the rules file `/var/ossec/etc/rules/600000-active_response.xml` and add the following rule to trigger the custom active response:

```xml
<group name="active_response,">
 <rule id="600000" level="10">
    <decoded_as>json</decoded_as>
    <field name="active_response">windows_firewall</field>
    <description>Windows Firewall Active Response triggered.</description>
    <group>socfortress,</group>
    <options>no_full_log</options>
  </rule>
</group>
```

#. Restart the Wazuh manager to apply the changes:

```bash
# Restart the Wazuh manager to apply the changes
systemctl restart wazuh-manager
```

With this configuration, Wazuh runs an executable instead of a Python script when triggering an active response on a Windows endpoint.
