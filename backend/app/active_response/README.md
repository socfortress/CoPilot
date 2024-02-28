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
