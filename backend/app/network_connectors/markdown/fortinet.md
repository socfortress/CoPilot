# [Fortinet Syslog Forwarding](https://help.fortinet.com/fa/faz50hlp/56/5-6-1/FMG-FAZ/2400_System_Settings/1600_Log%20Forwarding/0400_Configuring.htm)

This process involves configuring the Fortinet firewall to send logs to an external syslog server.

### Step 1: Accessing the Firewall

Log in to your Fortinet firewall using the web interface or FortiGate GUI:

-   Open a web browser.
-   Navigate to the IP address of the FortiGate unit (e.g., `https://192.168.1.99`).
-   Enter your administrative credentials to log in.

### Step 2: Configuring the Syslog Server

Once logged in, follow these steps to configure the syslog server:

-   **Go to Log & Report**
    -   Navigate to Log & Report on the left-hand sidebar.
    -   Select Log Settings
    -   Click on Log Settings to open the logging configuration options.
-   **Add a Syslog Server**
    -   Find the section labeled Syslog Servers and click on Create New.
-   **Configure Syslog Server Details**
    -   **Name:** Enter a recognizable name for your syslog server.
    -   **IP/Domain:** Enter the IP address or domain name of your syslog server.
    -   **Reliable:** Select whether to use TCP (reliable) or UDP (faster but less reliable) for log transmission.
    -   **Port:** Specify the port number on which the syslog server is listening (default is 514).
    -   **Facility:** Choose the syslog facility to be used (e.g., Local7).
    -   **Source IP:** (Optional) Specify the source IP address if you want the logs to come from a specific interface IP.

*   _Note_: The syslog format needs to be configured using FortiGate's CLI. Ensure that the format is set to rfc5424

-   **Configure Filters (if needed)**
    -   You can specify what kind of logs you want to send (e.g., traffic, event, virus, etc.). Select the appropriate log types.
-   **Test Connection (if available)**
    -   Some FortiGate models allow you to test the connection to ensure the syslog server is reachable.

### Step 3: Saving the Configuration

After entering all the necessary configurations:

-   Click on OK or Apply to save the settings.
-   The FortiGate firewall will now start forwarding logs to the specified syslog server based on your configurations.

### Step 4: Verify Log Reception

Check your syslog server to verify that it is receiving logs from the Fortinet firewall. You might need to configure filters or settings on the syslog server side to properly categorize and display incoming logs.

### Additional Considerations

-   **Security:** Ensure that the network path between your Fortinet firewall and the syslog server is secure. Consider using VPNs or IPsec tunnels if the logs contain sensitive information.
-   **Firewall Rules:** Ensure there are no firewall rules blocking the outgoing traffic on the port used for syslog.
-   **Backup Configurations:** Always keep a backup of your firewall configurations before making significant changes.
