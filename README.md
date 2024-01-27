<h1 align="center">

<a href="https://www.socfortress.co"><img src="src/assets/images/socfortress_logo.svg" width="300" height="200"></a>

SOCFortress CoPilot

[![Medium](https://img.shields.io/badge/Medium-12100E?style=for-the-badge&logo=medium&logoColor=white)](https://socfortress.medium.com/)
[![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/@taylorwalton_socfortress/videos)
[![Discord Shield](https://discordapp.com/api/guilds/871419379999469568/widget.png?style=shield)](https://discord.gg/UN3pNBzaEQ)

</h1><h4 align="center">

[SOCFortress CoPilot](https://www.socfortress.co) focuses on providing a single pane of glass for all your security operations needs. Simplify your open source security stack with a single platform focused on making open source security tools easier to use and more accessible.

![demo_timeline](src/assets/images/copilot_gif.gif)


## Table of contents
- [Getting Started](#getting-started)
  - [Running Copilot](#runnning-copilot)
  - [Configuration](#configuration)
- [Versioning](#versioning)
- [Showcase](#showcase)
- [Documentation](#documentation)
  - [Upgrades](#upgrades)
  - [API](#api)
- [Help](#help)
- [Considerations](#considerations)
- [License](#license)


## Getting started
Copilot's true power comes from the ability to integrate with your existing security stack. We have built in integrations with the following tools:
- [Wazuh](https://wazuh.com/)
- [Graylog](https://www.graylog.org/)
- [DFIR-IRIS](https://dfir-iris.org/)
- [Velociraptor](https://docs.velociraptor.app/)
- [Grafana](https://grafana.com/)
- [InfluxDB](https://www.influxdata.com/)

**Note:** Copilot is currently in beta. We are actively working on adding more integrations and features. If you have any suggestions or feedback, please let us know!


### Running Copilot
To ease the installation and upgrades, Copilot is shipped in a single docker container. To run Copilot, you will need to have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.


``` bash
#  Clone the CoPilot repository
git clone https://github.com/socfortress/CoPilot
cd CoPilot

# Copy the environment file
cp .env.example .env

# Run Copilot
docker compose up
```

Copilot shall be available on the host interface, port 5173, protocol HTTP - ``http://<your_instance_ip>:5173``.
By default, an ``admin`` account is created. The password is printed in stdout the very first time Copilot is started. It won't be printed anymore after that.
``WARNING :: post_init :: create_safe_admin :: >>>`` can be searched in the logs of the `copilot` docker to find the password.
