# [OPNSense Syslog Forwarding](https://docs.opnsense.org/manual/settingsmenu.html#logging)

This process involves configuring the OPNSense firewall to send logs to an external syslog server.
To configure a remote syslog server in OPNsense, follow these steps:

### Access OPNsense Web Interface:

-   Open a web browser and navigate to the web interface of your OPNsense firewall.
-   Enter your administrative credentials to log in.

### Step 2: Configuring the Syslog Server

Navigate to System Logs:

-   In the OPNsense web interface, go to _System_ > _Settings_ > _Logging_.

Configure Remote Syslog Server:

-   Check the box next to _Enable Remote Logging_ to enable remote logging.
-   Enter the IP address or hostname of your remote syslog server in the _Remote log servers_ field.
-   Optionally, specify the port number (default is 514) and protocol (UDP or TCP) for remote logging.
-   Click _Save_ to apply the changes.

### Verify Configuration:

-   Once the configuration is saved, OPNsense will start sending syslog messages to the specified remote syslog server.
-   You can verify that syslog messages are being received on the remote syslog server by checking its logs or monitoring tools.

### Additional Considerations

-   **Security:** Ensure that the network path between your OPNSense firewall and the syslog server is secure. Consider using VPNs or IPsec tunnels if the logs contain sensitive information.
-   **Firewall Rules:** Ensure there are no firewall rules blocking the outgoing traffic on the port used for syslog.
-   **Backup Configurations:** Always keep a backup of your firewall configurations before making significant changes.
