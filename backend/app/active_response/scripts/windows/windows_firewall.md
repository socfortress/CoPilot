# Windows Firewall

## Description
Wazuh Active Response capable of creating a new rule in the Windows Firewall to block or unblock traffic to a specific IP address.

### Requirements
`windows_firewall.exe` - The executable file that will be used to create the rule in the Windows Firewall. Provided by SOCFortress at `https://repo.socfortress.co/repository/socfortress/active-response/windows_firewall.exe`.

Must be placed in the `C:\Program Files (x86)\ossec-agent\active-response\bin` directory on the Windows agent.

### Download Script Via PowerShell
```powershell
Invoke-WebRequest -Uri "https://repo.socfortress.co/repository/socfortress/active-response/windows_firewall.exe" -OutFile "C:\Program Files (x86)\ossec-agent\active-response\bin\windows_firewall.exe"
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

```bash
# Restart the Wazuh manager to apply the changes
systemctl restart wazuh-manager
```
