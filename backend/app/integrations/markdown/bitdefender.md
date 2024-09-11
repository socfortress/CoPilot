# [BitDefender Integration](https://www.bitdefender.com/business/support/en/77209-144080-build-an-event-push-service-api-connector-for-cef-standard.html)

## Prerequisites

Before using the GravityZone Event Push Service API Connector, you’ll want to first define the API client and set its scope. Refer to this guide (https://www.bitdefender.com/business/support/en/77209-125277-public-api.html?srsltid=AfmBOooClMFH-dCfndiVD6eDNTBM5Q13qoFafF04EO3EsdJBPIbm--kx) to getting access to the BitDefender API for setting up a new API client key. For the new API client, make sure the scope includes read access for Event streams.

![BitDefender API Settings](/images/bitdefender/bitdefender_api_key.png)

### Firewall Configuration

The connector uses the POST method to receive authenticated and secured messages from the GravityZone Event Push Service. It parses the message and then forwards it to a local or a remote Syslog server. You can use the Syslog server to feed these messages to the SIEM. This means that the connector must be able to receive messages from the GravityZone Event Push Service and send them to the Graylog server. Make sure that the firewall allows the connector to receive messages from the GravityZone Event Push Service and send them to the Graylog server.

What we will be deploying is an HTTP endpoint that will receive the BitDefender logs and forward them to a syslog server. The HTTP endpoint is running on the server running CoPilot and will be listening on the port that you will define. This means that we must configure public DNS records to point to your edge firewall and open the port that you will define in the firewall.

Traffic flow will be as follows:
BitDefender Cloud Platform _ Your Edge Firewall _ CoPilot Server _ Graylog Server

## Configuration

The configuration for our API creds and syslog forwarder settings are stored within `/opt/bitdefender/gz-evpsc/api/config/config.json`. Adjust to make your changes. **NOTE that the `port` , `syslog_port` , `target` , and `authentication_string` will need to be updated.** Below is an example, CoPilot will take care of this for you.

```json
{
	"port": 3200,
	"syslog_port": 10514,
	"transport": "Tcp",
	"target": "YOUR_GRAYLOG_SERVER",
	"authentication_string": "Basic cmVsaWFibGVwYnhfYml0ZGVmZW5kZXI6cmVsaWFibGVwYnhfYml0ZGVmZW5kZXI=",
	"secure": {
		"enabled": true,
		"key": "api/config/server.key",
		"cert": "api/config/server.crt"
	}
}
```

## Provisioning

Once you have saved the BitDefender configuration for the customer, you are ready to deploy the integration. Navigate to the `Customers` tab and select the appropriate customer. The provisiong creates the necessary:

-   Graylog CEF Input
-   Graylog Stream
-   Graylog Index
-   Grafana Datasource
-   Grafana Dashboards
-   BitDefender Docker-Compose File

## Deployment of BitDefender Container

The BitDefender integration runs via a docker container. During provisioning, the following directory is created `/opt/CoPilot/data/data/CUSTOMER_NAME`. Within this directory will reside the `CUSTOMER_NAME_bitdefender_docker-compose.yml` and the `config.json` files. These can be modified if desired but should already contain the details needed to collect logs for their BitDefender environment.

Start the container with the below command:

```bash
docker compose -f /opt/CoPilot/data/data/CUSTOMER_NAME/CUSTOMER_NAME_bitdefender_docker-compose.yml up -d
```

You should now see the container running.

## Test the Connector

[Helpful Doc For Testing](https://support.netenrich.com/hc/en-us/articles/10833633251869-Bitdefender-Gravity-Zone-Cloud-integration#:~:text=155.173,Configure%20Chronicle%20Forwarder)
