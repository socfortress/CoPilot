# [Crowdstrike Integration](https://www.crowdstrike.com/blog/tech-center/integrate-with-your-siem)

## Prerequisites

Before using the Falcon SIEM Connector, you’ll want to first define the API client and set its scope. Refer to this guide (https://www.crowdstrike.com/blog/tech-center/get-access-falcon-apis/) to getting access to the CrowdStrike API for setting up a new API client key. For the new API client, make sure the scope includes read access for Event streams.

### IMPORTANT: If you are in the Government cloud of Crowdstrike, you must open a support ticket with Crowdstrike so they can enable the Falcon SIEM Connector on their end.

![Crowdstrike API Settings](/images/crowdstrike/crowdstrike_api_settings.png)

## Configuration

The configuration for our API creds and syslog forwarder settings are stored within `/opt/crowdstrike/etc/cs.falconhoseclient.cfg`. Adjust to make your changes. **NOTE that the `api_url` , `cliend_id` , `client_secret` , and `syslog_host` will need to be updated.** Below is an example, CoPilot will take care of this for you.

```yaml
[Settings]
version = 3
api_url = REPLACE_BASE_URL/sensors/entities/datafeed/v2
request_token_url = REPLACE_BASE_URL/oauth2/token
app_id = SIEM-Connector-v2.0.0

enable_correlation_id = false
format_floats_as_scientific = true

# API Client ID
client_id = REPLACE_CLIENT_ID
# API Client Secret
client_secret = REPLACE_CLIENT_SECRET

# Amount of time (in seconds) we will wait for a connect to complete.
connection_timeout = 10
# Amount of time to wait (in seconds) for a server's response headers after fully writing the request.
read_timeout = 30

# Specify partition number 0 to n or 'all' (without quote) for all partitions
partition = all

http_proxy =

# Output formats
# Supported formats are
#   1.syslog: will output syslog format with flat key=value pairs uses the mapping configuration below.
;             Use syslog format if CEF/LEEF output is required.
#   2.json: will output raw json format received from FalconHose API (default)
output_format = syslog

# Will be true regardless if Syslog is not enabled
# If path does not exist or user has no permission, log file will be used
output_to_file = false
output_path = /var/log/crowdstrike/falconhoseclient/output

# Offset file full filepath and filename
offset_path = /var/log/crowdstrike/falconhoseclient/stream_offsets

[Output_File_Rotation]
# If the output is writing to a file, then the settings below will govern output file rotation
#
# If true, then the rotation rules will apply. If not, the client will continue to write to the same file.
rotate_file = true
# Maximum individual output file size in MB
max_size = 500
# Number of backups of the output file to be stored
max_backups = 10
# Maximum age of backup output files before it is deleted in DAYS
max_age = 30

[Logging]
verbose_log = true
# Maximum individual log file size in MB
max_size = 500
# Number of backups to be stored
max_backups = 10
# Maximum age of backup files before it is deleted in DAYS
max_age = 30

[Syslog]
send_to_syslog_server = true
host = REPLACE_SYSLOG_HOST
port = REPLACE_SYSLOG_PORT
protocol = tcp
```

## Provisioning

Once you have saved the Crowdstrike configuration for the customer, you are ready to deploy the integration. Navigate to the `Customers` tab and select the appropriate customer. The provisiong creates the necessary:

-   Graylog CEF Input
-   Graylog Stream
-   Graylog Index
-   Grafana Datasource
-   Grafana Dashboards
-   Crowdstrike Docker-Compose File

## Deployment of Crowdstrike Container

The Crowdstrike integration runs via a docker container. During provisioning, the following directory is created `/opt/CoPilot/data/data/CUSTOMER_NAME`. Within this directory will reside the `CUSTOMER_NAME_docker-compose.yml` and the `cs.falconhoseclient.cfg` files. These can be modified if desired but should already contain the details needed to collect logs for their Crowdstrike environment.

Start the container with the below command:

```bash
docker compose -f /opt/CoPilot/data/data/CUSTOMER_NAME/CUSTOMER_NAME_docker-compose.yml up -d
```

You should now see the container running:
![Crowdstrike Running Container](/images/crowdstrike/docker_ps.PNG)
