<template>
	<div class="uba-deploy-guide flex flex-col gap-4 text-sm">
		<p class="text-secondary max-w-3xl">
			SOCFortress UBA runs as its own small Docker Compose stack (API, GELF receiver, worker, Postgres,
			Redis) on a VM in the same network as Graylog, the Wazuh indexer and CoPilot. Graylog sends it a copy
			of each customer's Wazuh and Microsoft 365 events, UBA reads history from the Wazuh indexer, and
			CoPilot talks to its API. Once it is running and connected, every customer is set up from this page
			with one click. Below, replace the &lt;uba-ip&gt;, &lt;graylog-ip&gt;, &lt;indexer-ip&gt; and
			&lt;copilot-ip&gt; placeholders with those hosts' addresses.
		</p>

		<ol class="flex flex-col gap-4">
			<li v-for="(step, i) of STEPS" :key="step.title" class="flex flex-col gap-2">
				<div class="flex items-baseline gap-2">
					<n-tag size="small" round :bordered="false">{{ i + 1 }}</n-tag>
					<b>{{ step.title }}</b>
				</div>
				<p v-for="(line, j) of step.text" :key="j" class="text-secondary max-w-3xl">{{ line }}</p>
				<CodeSource v-if="step.code" :code="step.code" lang="shellscript" :max-height="360" />
			</li>
		</ol>
	</div>
</template>

<script setup lang="ts">
import { NTag } from "naive-ui"
import CodeSource from "@/components/common/CodeSource.vue"

interface Step {
	title: string
	text: string[]
	code?: string
}

const IMAGE = "ghcr.io/socfortress/socfortress-uba:latest"

// The customer layout of UBA's docs/13-deployment-operations.md ("On its own VM"): UBA on its own VM
// in the VLAN of Graylog, the indexer and CoPilot; the VM pulls only the public image, which carries
// docker-compose.yml.
const STEPS: Step[] = [
	{
		title: "Prepare the VM",
		text: [
			"A Linux VM with Docker and Compose v2, 4 vCPU and 8 GB of memory to start, in the same network as Graylog, the Wazuh indexer and CoPilot. Postgres keeps UBA's state: give it room on the Docker disk."
		],
		code: "docker compose version\nfree -m\ndf -h /var/lib/docker"
	},
	{
		title: "Get UBA",
		text: ["The image is public and carries the stack definition, so nothing else is needed on the VM."],
		code: [
			"mkdir -p /opt/socfortress-uba/data/geoip && cd /opt/socfortress-uba",
			`docker pull ${IMAGE}`,
			`docker run --rm ${IMAGE} cat /app/deploy/docker-compose.yml > docker-compose.yml`
		].join("\n")
	},
	{
		title: "Write /opt/socfortress-uba/.env",
		text: [
			"Create the file with these values (chmod 600). Keep UBA_SECRET_KEY: it encrypts identity-source secrets, and a new one means entering them again. Customers are not listed here: CoPilot registers them.",
			"Optional: GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in data/geoip add countries and networks to sign-ins; without them the new-country, new-network and impossible-travel rules stay quiet."
		],
		code: [
			"UBA_TAG=latest",
			"POSTGRES_PASSWORD=<output of: openssl rand -hex 24>",
			"UBA_SECRET_KEY=<output of: openssl rand -base64 32 | tr '+/' '-_'>",
			"UBA_STORE=postgres",
			"",
			"# Where UBA listens (all interfaces of the VM)",
			"UBA_API_PUBLISH=8010                      # CoPilot connects here",
			"UBA_GELF_PUBLISH=12201                    # Graylog sends the UBA feed here",
			"",
			"# What CoPilot's \"Set up UBA\" creates in Graylog",
			"UBA_PROVISION_FEED_HOST=<uba-ip>          # Graylog's output -> this VM",
			"UBA_PROVISION_FEED_PORT=12201",
			"UBA_PROVISION_ALERTS_BIND=0.0.0.0         # Graylog's UBA ALERTS input, on the Graylog host",
			"UBA_GRAYLOG_GELF_HOST=<graylog-ip>        # UBA's alerts -> that input",
			"UBA_GRAYLOG_GELF_PORT=12204",
			"",
			"# Wazuh indexer: history for new customers, evidence, gap repair",
			"UBA_INDEXER__URL=https://<indexer-ip>:9200",
			"UBA_INDEXER__USERNAME=admin",
			"UBA_INDEXER__PASSWORD=<indexer admin password>",
			"UBA_INDEXER__VERIFY_CERTS=false",
			"",
			"# UBA alerts as CoPilot incident alerts (a CoPilot service account: analyst role, no 2FA)",
			"UBA_COPILOT_URL=http://<copilot-ip>:5000",
			"UBA_COPILOT_USERNAME=<service account>",
			"UBA_COPILOT_PASSWORD=<password>",
			"",
			"# Computer changes (new local admins, services, ports, browser extensions), every 30 minutes",
			"UBA_INVENTORY_EVERY_S=1800",
			"UBA_ENRICH__GEOIP_CITY_DB=/var/lib/uba/GeoLite2-City.mmdb",
			"UBA_ENRICH__GEOIP_ASN_DB=/var/lib/uba/GeoLite2-ASN.mmdb",
			"",
			"# Customers come from CoPilot, not from this file",
			"UBA_BOOTSTRAP_TENANTS=[]",
			"UBA_O365_TENANT_MAP={}"
		].join("\n")
	},
	{
		title: "Start it",
		text: [
			"The first start creates the database; later starts keep everything. Check that the API answers and the worker reports every minute."
		],
		code: [
			"cd /opt/socfortress-uba",
			"docker compose pull && docker compose up -d",
			"curl -s http://<uba-ip>:8010/healthz",
			"docker compose logs --tail 20 worker"
		].join("\n")
	},
	{
		title: "Create CoPilot's API key (all customers)",
		text: [
			"Scope admin lets CoPilot set customers up as well as read and triage; tenants '*' covers every customer, current and future (CoPilot still checks each user's customer access). The key is shown once: copy it now.",
			"If a key named copilot already exists, revoke it first, or pick another name."
		],
		code: [
			"docker compose exec api uba-admin api-keys create --name copilot --scope admin --tenants '*'",
			"",
			"# list keys, or revoke one",
			"docker compose exec api uba-admin api-keys list",
			"docker compose exec api uba-admin api-keys revoke --name copilot"
		].join("\n")
	},
	{
		title: "Connect CoPilot",
		text: [
			"Platform → Connectors → SOCFortress UBA: URL http://<uba-ip>:8010, the API key from the previous step, then Verify. This page then shows UBA."
		]
	},
	{
		title: "Set each customer up",
		text: [
			"Provision the customer in CoPilot as usual (Wazuh, and Microsoft 365 if they have it). Then, on this page, pick the customer and click Set up UBA: it registers the customer with UBA and creates its Graylog streams, pipelines and output. UBA learns from the history you choose (the indexer must still hold it), then scores new activity. After adding Microsoft 365 later, use Setup → Run setup again."
		]
	},
	{
		title: "Back up and upgrade",
		text: [
			"Postgres holds what UBA has learned, its identities and alerts: back it up nightly. To upgrade, pull the new image and restart; database migrations run first."
		],
		code: [
			"# nightly backup (in a crontab line, write each % as \\%)",
			"cd /opt/socfortress-uba && docker compose exec -T postgres pg_dump -U uba -Fc uba > /backup/uba-$(date +%F).dump",
			"",
			"# upgrade",
			"cd /opt/socfortress-uba && docker compose pull && docker compose up -d"
		].join("\n")
	}
]
</script>
