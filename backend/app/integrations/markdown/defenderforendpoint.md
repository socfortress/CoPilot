# [Defender For Endpoint Integration](https://learn.microsoft.com/en-us/defender-endpoint/api/get-alerts)

## Prerequisites

Before using the Defender For Endpoint SIEM Connector, you’ll want to first define the API client and set its scope. Refer to this guide (https://learn.microsoft.com/en-us/defender-endpoint/api/get-alerts) to getting access to the Defender For Endpoint API for setting up a new API client key. For the new API client, make sure the scope includes access for `Alert.Read.All` and `Alert.ReadWrite.All`.

### IMPORTANT: Make sure your API has the below configred roles:

`Alert.Read.All, Alert.ReadWrite.All`

![Defender For Endpoint API Settings](/images/defenderforendpoint/permissions.png)

## Configuration

The configuration for our API creds and syslog forwarder settings are stored within `/usr/share/filebeat/filebeat.yml`. Adjust to make your changes. **NOTE that the `tenant_id` , `cliend_id` , `client_secret` , `syslog_port`, and `syslog_host` will need to be updated.** Below is an example, CoPilot will take care of this for you.

```yaml
filebeat.modules:
- module: microsoft
  defender_atp:
    enabled: true
    var.oauth2.client.id: "CLIENT_ID"
    var.oauth2.client.secret: "CLIENT_SECRET"
    var.oauth2.token_url: "https://login.microsoftonline.com/TENANT_ID/oauth2/token"

filebeat.inputs:
- type: log
  enabled: false
  paths:
    - /var/log/*.log

output.logstash:
  hosts: ["REPLACE_SYSLOG_HOST:REPLACE_SYSLOG_PORT"]
```

## Provisioning

Once you have saved the Defender For Endpoint configuration for the customer, you are ready to deploy the integration. Navigate to the `Customers` tab and select the appropriate customer. The provisiong creates the necessary:

-   Graylog CEF Input
-   Graylog Stream
-   Graylog Index
-   Grafana Datasource
-   Grafana Dashboards
-   Defender For Endpoint Docker-Compose File

## Deployment of Defender For Endpoint Container

The Defender For Endpoint integration runs via a docker container. During provisioning, the following directory is created `/opt/CoPilot/data/data/CUSTOMER_NAME`. Within this directory will reside the `CUSTOMER_NAME_docker-compose-defender-for-endpoint.yml` and the `filebeat.yml` files. These can be modified if desired but should already contain the details needed to collect logs for their Defender For Endpoint environment.

Start the container with the below command:

```bash
docker compose -f /opt/CoPilot/data/data/CUSTOMER_NAME/CUSTOMER_NAME_docker-compose-defender-for-endpoint.yml up -d
```

You should now see the container running.
