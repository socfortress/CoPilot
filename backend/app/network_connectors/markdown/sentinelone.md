# SentinelOne Syslog Forwarding

This process involves configuring SentinelOne to send alerts and events to an external syslog server via TLS-encrypted connection.

## Overview

SentinelOne provides cloud-based endpoint protection and uses a syslog forwarder to send security events to your SIEM stack. The integration requires:

-   **TLS Encryption:** Secure, encrypted log forwarding from SentinelOne cloud endpoints
-   **Mutual Authentication:** Client certificate for TLS mutual authentication
-   **Cloud-to-Cloud:** Direct forwarding from SentinelOne cloud infrastructure to your SIEM stack

For detailed instructions, refer to the [SentinelOne Syslog Forwarder Configuration Guide](https://socfortress.supportbench.net/article/sentinelone-syslog-forwarder-to-siem-stack).

## Architecture

```
SentinelOne Cloud > TLS (Mutual Auth) > SIEM Stack
```

---

## Step 1: Accessing SentinelOne Management Console

Log in to your SentinelOne management console:

-   Open a web browser
-   Navigate to your SentinelOne console URL (e.g., `https://console.sentinelone.net`)
-   Enter your administrative credentials to log in

## Step 2: Navigate to Integrations

Once logged in, follow these steps to configure syslog forwarding:

-   **Navigate to Integrations**
    -   Go to **Settings** > **Integrations** in the left-hand navigation menu
    -   Look for the **Syslog** integration option

## Step 3: Configure Syslog Forwarder

Configure the syslog forwarder with the following parameters:

-   **Syslog Host Configuration**
    -   **Host:** Enter the FQDN or IP address of your SIEM stack (e.g., `firehose.mycompany.com`)
    -   **Port:** Enter the TCP port provided by SOCFortress staff (typically 6514 for TLS)

-   **Enable TLS Secure Connection**
    -   Check the box to **Use TLS secure connection**

-   **Upload TLS Certificates**

    You will need to upload three certificate files (provided by SOCFortress via your Onehub account):

    1. **Root CA Certificate** (`rootCA.mycompany.local.crt`)
        -   The root Certificate Authority public key

    2. **Client Certificate** (`syslog_client.mycompany.local.pem`)
        -   The TLS client certificate public key

    3. **Private Key** (`syslog_client.mycompany.local.key`)
        -   The TLS client certificate private key

-   **Log Format**
    -   Select **RFC-5424** as the syslog format

## Step 4: Configure Firewall Rules

Before testing connectivity, ensure proper firewall rules are in place:

### Inbound Firewall Rules

SentinelOne forwards alerts and events from their cloud endpoints. Configure the following firewall rules:

#### Rule 1: SentinelOne Cloud to Edge Firewall

| **SRC IP** | **DST IP** | **PORT** | **FIREWALL ACTION** | **DESCRIPTION** |
|------------|------------|----------|---------------------|-----------------|
| SentinelOne Cloud Endpoints | Your edge firewall's public IP | Provided by SOCFortress | Port Forward to Reverse Proxy (DMZ) | Allow Syslog Forwarder from SentinelOne |

> **Note:** Contact SentinelOne support to determine the specific source IP addresses/cloud endpoints for your region.

#### Rule 2: SIEM Stack DMZ to SIEM Stack Internal

| **SRC IP** | **DST IP** | **PORT** | **FIREWALL ACTION** | **DESCRIPTION** |
|------------|------------|----------|---------------------|-----------------|
| HAProxy DMZ | Graylog Server (01/02) | Provided by SOCFortress | Allow | Allow Syslog traffic DMZ > Internal |

## Step 5: Configure Event and Alert Forwarding

Define which events and alerts should be forwarded to your SIEM:

-   **Navigate to Notifications**
    -   Go to the **Notifications** tab in the Syslog integration settings

-   **Select Event Types**

    Choose the alerts and events to forward. Common selections include:
    -   Threat Detections
    -   Threat Mitigations
    -   Agent Activity
    -   Policy Changes
    -   User Actions
    -   System Events
    -   And any other relevant security events

-   **Apply Configuration**
    -   Click **Save** or **Apply** to activate the forwarding configuration

## Step 6: Test the Connection

After configuring all settings and firewall rules:

-   Click **Test Connection** in the SentinelOne syslog integration interface
-   Verify successful TLS handshake and authentication
-   Confirm test events are received in your SIEM stack

## Step 7: Verify Log Reception

Monitor your SIEM stack to ensure logs are being received:

-   Check that SentinelOne events appear in your log management system
-   Verify proper parsing and categorization of events
-   Confirm all selected event types are being forwarded
-   Monitor for any connection errors or certificate issues

---

## Additional Considerations

-   **Certificate Management**
    -   Keep TLS certificates up to date and properly secured
    -   Certificates must be in PEM format
    -   Ensure certificate expiration dates are monitored
    -   Plan for certificate renewal before expiration

-   **Source IP Addresses**
    -   SentinelOne uses cloud endpoints that vary by region
    -   Contact SentinelOne support for specific IP ranges for your deployment
    -   Update firewall rules if SentinelOne changes their endpoint IPs

-   **High Availability**
    -   Consider configuring backup syslog destinations if supported
    -   Ensure redundant firewall paths for critical log forwarding
    -   Monitor connection health and implement alerting for failures

-   **Log Volume**
    -   Monitor the volume of logs being generated
    -   Ensure your SIEM infrastructure can handle the load
    -   Adjust event filtering if necessary to manage data volume

-   **Security**
    -   TLS mutual authentication provides strong security
    -   Protect private keys and restrict access
    -   Regularly audit firewall rules for unauthorized changes

-   **Time Synchronization**
    -   Ensure all systems (SentinelOne, SIEM stack) use synchronized time via NTP
    -   Accurate timestamps are critical for security event correlation

-   **Testing**
    -   Perform initial testing during a maintenance window
    -   Verify all expected event types are being received
    -   Test connection recovery after network interruptions
    -   Validate TLS certificate authentication is working correctly

-   **Documentation**
    -   Keep records of:
        -   Certificate locations and expiration dates
        -   Firewall rule configurations
        -   Port assignments
        -   Selected event types for forwarding

---

## Troubleshooting

Common issues and solutions:

-   **Connection Failures**
    -   Verify firewall rules allow traffic from SentinelOne cloud endpoints
    -   Check that the destination port is correct and open
    -   Ensure certificates are correctly uploaded and not expired

-   **Certificate Errors**
    -   Verify certificate format is PEM
    -   Ensure the certificate chain is complete (root CA + client cert)
    -   Check that private key matches the client certificate

-   **Missing Events**
    -   Confirm event types are selected in the Notifications tab
    -   Verify SentinelOne agents are properly configured and reporting
    -   Check SIEM stack for parsing or ingestion errors

-   **Performance Issues**
    -   Monitor log volume and adjust retention policies
    -   Consider implementing log filtering for high-volume event types
    -   Ensure adequate resources on SIEM infrastructure
