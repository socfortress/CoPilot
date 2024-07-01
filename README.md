<h1 align="center">

<a href="https://www.socfortress.co"><img src="frontend/src/assets/images/socfortress_logo.svg" width="300" height="200"></a>

SOCFortress CoPilot

[![Medium](https://img.shields.io/badge/Medium-12100E?style=for-the-badge&logo=medium&logoColor=white)](https://socfortress.medium.com/)
[![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/@taylorwalton_socfortress/videos)
[![Discord Shield](https://discordapp.com/api/guilds/871419379999469568/widget.png?style=shield)](https://discord.gg/UN3pNBzaEQ)
[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/taylorwalton)

</h1><h4 align="center">

[SOCFortress CoPilot](https://www.socfortress.co) focuses on providing a single pane of glass for all your security operations needs. Simplify your open source security stack with a single platform focused on making open source security tools easier to use and more accessible.

![demo_timeline](frontend/src/assets/images/copilot_gif.gif)

## Table of contents

-   [Getting Started](#getting-started)
    -   [Running Copilot](#runnning-copilot)
    -   [Upgrading Copilot](#upgrading-copilot)
-   [Connectors](#connectors)
-   [Help](#help)
-   [License](#license)
-   [Sponsoring](#sponsoring)

## Getting started

Copilot's true power comes from the ability to integrate with your existing security stack. We have built in integrations with the following tools:

-   [Wazuh](https://wazuh.com/)
-   [Graylog](https://www.graylog.org/)
-   [DFIR-IRIS](https://dfir-iris.org/)
-   [Velociraptor](https://docs.velociraptor.app/)
-   [Grafana](https://grafana.com/)
-   [InfluxDB](https://www.influxdata.com/)

❗️ **Note:** Copilot is currently in beta. We are actively working on adding more integrations and features. If you have any suggestions or feedback, please let us know!

### Running Copilot

To ease the installation and upgrades, Copilot is shipped in a single docker container. To run Copilot, you will need to have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

❗ **WARNING:** Copilot is not intended to be exposed to the internet. It is recommended for internal use only.

🔴 - Helpful docker DNS setting

```
nano /etc/docker/daemon.json
```

```json
{
	"dns": ["YOUR_DNS_SERVER"],
	"log-driver": "json-file",
	"log-opts": {
		"max-size": "10m",
		"max-file": "3"
	}
}
```

### In case you need to set MTU

```json
{
	"dns": ["YOUR_DNS_SERVER"],
	"log-driver": "json-file",
	"log-opts": {
		"max-size": "10m",
		"max-file": "3"
	},
	"mtu": 1450
}
```

```
systemctl daemon-reload
systemctl restart docker
```

---

```bash
#  Clone the CoPilot repository
wget https://raw.githubusercontent.com/socfortress/CoPilot/v0.1.0/docker-compose.yml

# Edit the docker-compose.yml file to set the server name and/or the services you want to use

# Create the path for storing your data
mkdir data

# Create the .env file based on the .env.example

# Run Copilot
docker compose up -d

# Once Copilot has started up you can retrieve the admin password by running the following command (Only accessible the first time Copilot is started up)
docker logs "$(docker ps --filter ancestor=ghcr.io/socfortress/copilot-backend:latest --format "{{.ID}}")" 2>&1 | grep "Admin user password"
```

Copilot shall be available on the host interface, port 443, protocol HTTPS - `https://<your_instance_ip>`.
By default, an `admin` account is created. The password is printed in stdout the very first time Copilot is started. It won't be printed anymore after that.
`Admin user password` can be searched in the logs of the `copilot` docker to find the password. You will use the `plain` password to login to the web interface.

🚀 **YouTube Tutorial:** [INSTALLING COPILOT](https://youtu.be/7dUHSMWWTuY?si=lRbn4tBHnyKmiTka)

#### SSL

By default Copilot uses a self-signed certificate valid for 365 days from install. You can replace the certificate and
key files with your own. These files should be mounted in the `copilot-frontend` container and you can set the path to
your certificate and key files in the `docker-compose.yml` file using the `TLS_CERT_PATH` and `TLS_KEY_PATH`
respectively.

For Example

```bash
# Generate a certificate e.g.
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365
```

Then update the `docker-compose.yml` file to mount the certificate and key files and set the `TLS_CERT_PATH` and `TLS_KEY_PATH` environment variables.

```yaml
copilot-frontend:
    image: ghcr.io/socfortress/copilot-frontend:latest
    volumes:
        - PATH_TO_YOUR_CERTS:/etc/letsencrypt
    environment:
        - SERVER_HOST=${SERVER_HOST:-localhost} # Set the domain name of your server
        - TLS_CERT_PATH=/etc/letsencrypt/live/${SERVER_HOST}/fullchain.pem # Set the path to your certificate
        - TLS_KEY_PATH=/etc/letsencrypt/live/${SERVER_HOST}/privkey.pem # Set the path to your key
    ports:
        - "80:80"
        - "443:443"
```

### Upgrading Copilot

🛠 You will likely want to upgrade often as we are frequently pushing new changes.

To upgrade Copilot, you will need to stop the running containers, pull the latest docker image, and start the containers again.

```bash
# Stop the running container. Make sure you are in the CoPilot directory
docker compose pull

# Start the container again
docker compose up -d
```

## Connectors

Copilot is designed to be a single pane of glass for your security operations. Think of it as a hub for all your security tools. Copilot Connectors are the glue that binds your security tools to Copilot. We take advantage of the APIs and webhooks provided by your security tools to provide a seamless integration.

## Help

You can reach us on [Discord](https://discord.gg/UN3pNBzaEQ) or by [📧](mailto:info@socfortress.co) if you have any question, issue or idea!

Check out our full video tutorial series on [![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/watch?v=qQbex2zAhWI&list=PLB6hQ_WpB6U0e5oSLXJMcxmSzz7n3zvD-&ab_channel=TaylorWalton)

## License

The contents of this repository is available under [AGPL-3.0 license](LICENSE.txt).

## Sponsoring

If you like this project and want to support it, you can consider becoming a sponsor to help us continue maintaining it and adding new features.

[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/taylorwalton)
