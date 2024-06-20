# [DUO Integration](https://duo.com/docs/adminapi#overview)

# Duo Admin API

CoPilot and DUO. Ingest DUO auth logs into your SIEM stack

## Overview

CoPilot's integration with DUO allows for administrators to collect and analyze Duo authentication logs seamlessly. By integrating the Duo Admin API with CoPilot, you can enhance your security monitoring and incident response capabilities within your SIEM stack.

### Key Features

-   **Automated Log Collection:** Automatically ingest Duo authentication logs into your SIEM for real-time analysis.
-   **Comprehensive Monitoring:** Monitor Duo-related activities, including user logins, telephony logs, and administrator actions.
-   **Custom Alerts:** Set up custom alerts based on Duo log data to quickly identify and respond to potential security incidents.
-   **Detailed Reports:** Generate detailed reports on Duo authentication events, helping you to meet compliance requirements and improve security posture.

## First Steps

**Role required: Owner**

Note that only administrators with the Owner role can create or modify an Admin API application in the Duo Admin Panel.

1. Sign up for a Duo account.
2. Log in to the Duo Admin Panel and navigate to Applications.
3. Click **Protect an Application** and locate the entry for Admin API in the applications list. Click **Protect** to the far-right to configure the application and get your integration key, secret key, and API hostname. You'll need this information to complete your setup. See [Protecting Applications](https://duo.com/docs/protecting-applications) for more information about protecting applications in Duo and additional application options.

### Treat your secret key like a password

The security of your Duo application is tied to the security of your secret key (skey). Secure it as you would any sensitive credential. Don't share it with unauthorized individuals or email it to anyone under any circumstances!

Determine the permissions you want to grant to this Admin API application. Refer to the API endpoint descriptions throughout this document for information about required permissions for operations.

### Permission Details

| Permission             | Details                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Grant administrators   | The Admin API application can read information about, create, update, and delete Duo administrators and administrative units.                                                   |
| Grant read information | The Admin API application can read information about the Duo customer account's utilization.                                                                                    |
| Grant applications     | The Admin API application can add, modify, and delete applications (referred to as "integrations" in the API), including permissions on itself or other Admin API applications. |
| Grant settings         | The Admin API application can read and change global Duo account settings.                                                                                                      |
| Grant read log         | The Admin API application can read authentication, offline access, telephony, and administrator action log information.                                                         |
| Grant read resource    | The Admin API application can read information about resource objects such as end users and devices.                                                                            |
| Grant write resource   | The Admin API application can create, update, and delete resource objects such as end users and devices.                                                                        |
