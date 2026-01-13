# SonicWall Syslog Forwarding

This process involves configuring the SonicWall firewall to send logs to an external syslog server.

## Method 1: Direct Syslog Forwarding (UDP/TCP)

For direct syslog forwarding from SonicWall to your SIEM stack, follow the [SonicWall Syslog Configuration Guide](https://socfortress.supportbench.net/ar-1084/).

### Step 1: Accessing the SonicWall Firewall

Log in to your SonicWall firewall using the web management interface:

-   Open a web browser.
-   Navigate to the IP address of the SonicWall unit (e.g., `https://192.168.1.1`).
-   Enter your administrative credentials to log in.

### Step 2: Configuring Syslog Settings

Once logged in, follow these steps to configure syslog forwarding:

-   **Navigate to Log Settings**
    -   Go to **Log** > **Settings** in the left-hand navigation menu.
    -   Click on the **Syslog** tab.

-   **Enable Syslog**
    -   Check the box to **Enable Syslog**.

-   **Configure Syslog Server Details**
    -   **Name or IP Address:** Enter the IP address or hostname of your syslog server.
    -   **Port:** Specify the port number (default is 514 for UDP, or custom port for TCP).
    -   **Syslog Format:** Select the syslog format (recommended: **Syslog** or **CEF**).
    -   **Syslog ID:** (Optional) Enter a unique identifier for this SonicWall device.

-   **Select Log Categories**
    -   Choose which categories of logs to forward:
        -   System Maintenance
        -   System Errors
        -   Blocked Web Sites
        -   Blocked Java etc.
        -   User Activity
        -   Attacks
        -   Dropped TCP/UDP/ICMP
        -   Network Debug
        -   And any other relevant categories

-   **Configure Advanced Settings (Optional)**
    -   **Syslog Facility:** Select the facility code (e.g., Local0 through Local7).
    -   **Display Format:** Choose how the logs should be formatted.

### Step 3: Saving the Configuration

After entering all the necessary configurations:

-   Click **Accept** or **Apply** to save the settings.
-   The SonicWall firewall will now start forwarding logs to the specified syslog server.

### Step 4: Verify Log Reception

Check your syslog server to verify that it is receiving logs from the SonicWall firewall. Monitor the logs to ensure proper formatting and categorization.

---

## Method 2: TLS Encrypted Forwarding via Syslog-NG (Recommended for Production)

For secure, encrypted log forwarding, use a local syslog-ng collector to receive UDP logs from SonicWall within your local network, then forward them via TLS to your SIEM stack.

### Overview

This method provides:
-   **Security:** TLS encryption for logs in transit over the internet
-   **Reliability:** Local collection prevents log loss due to network issues
-   **Flexibility:** Ability to preprocess or enrich logs before forwarding

### Architecture

```
SonicWall (UDP) → Syslog-NG Collector (Local Network) → TLS → SIEM Stack
```

### Step 1: Deploy Local Log Collector

Follow the [Local Log Collector using Syslog-NG Guide](https://socfortress.supportbench.net/article/local-log-collector-using-syslog-ng) to set up your local collector.

The local collector will:
1. Listen for UDP syslog messages from your SonicWall firewall
2. Receive logs on the local network (e.g., port 514/UDP)
3. Encrypt and forward logs via TLS to your SIEM stack

### Step 2: Configure SonicWall for Local Collector

Configure your SonicWall to send logs to the **local syslog-ng collector IP address**:

-   **Navigate to Log Settings**
    -   Go to **Log** > **Settings** > **Syslog** tab

-   **Configure Local Collector as Syslog Server**
    -   **Name or IP Address:** Enter the IP address of your local syslog-ng collector
    -   **Port:** 514 (UDP) or the port configured on your collector
    -   **Syslog Format:** Syslog or CEF
    -   Enable relevant log categories

-   **Apply Configuration**
    -   Click **Accept** to save the settings

### Step 3: Configure Syslog-NG for TLS Forwarding

On your local syslog-ng collector, configure the destination to forward logs via TLS to your SIEM stack:

-   Reference the [Syslog-NG TLS Configuration Guide](https://socfortress.supportbench.net/article/local-log-collector-using-syslog-ng) for detailed steps
-   Ensure TLS certificates are properly configured
-   Configure the destination with your SIEM stack's IP address and TLS port

### Step 4: Verify End-to-End Log Flow

1. **Check Local Collection:** Verify syslog-ng is receiving logs from SonicWall
2. **Check TLS Connection:** Verify syslog-ng establishes TLS connection to SIEM
3. **Check SIEM Reception:** Verify logs appear in your SIEM stack with proper source identification

### Additional Considerations

-   **Certificate Management:** Keep TLS certificates up to date and properly secured
-   **Collector High Availability:** Consider deploying redundant collectors for production environments
-   **Network Segmentation:** Ensure the local collector is in the same network segment as the SonicWall for optimal performance
-   **Firewall Rules:** Ensure:
    -   SonicWall can reach the local collector on the configured UDP port
    -   Local collector can reach the SIEM stack on the configured TLS port
    -   No firewall rules block outbound TLS traffic from the collector

---

## General Additional Considerations

-   **Security:** For internet-facing log forwarding, always use TLS encryption (Method 2)
-   **Backup Configurations:** Always keep a backup of your firewall configurations before making changes
-   **Log Volume:** Monitor the volume of logs being generated to ensure your syslog infrastructure can handle the load
-   **Time Synchronization:** Ensure all devices (SonicWall, collector, SIEM) have synchronized time using NTP
-   **Testing:** Test the configuration in a non-production environment first if possible
