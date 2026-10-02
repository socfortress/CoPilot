<template>
	<div class="uba-deploy-guide flex flex-col gap-4 text-sm">
		<p class="text-secondary max-w-3xl">
			SOCFortress UBA runs as its own small Docker Compose stack (API, GELF receiver, worker, Postgres,
			Redis), usually on the Graylog host. Graylog sends it a copy of each customer's Wazuh and Microsoft 365
			events, UBA reads history from the Wazuh indexer, and CoPilot talks to its API. Once it is running and
			connected, every customer is set up from this page with one click.
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

// Values match a deployment next to Graylog on one host (the setup UBA documents in
// docs/13-deployment-operations.md): CoPilot's containers reach UBA on the Docker bridge, Graylog
// reaches UBA's GELF receiver on 127.0.0.1, UBA reaches Graylog's UBA ALERTS input on docker0.
const STEPS: Step[] = [
	{
		title: "Check the host",
		text: [
			"Docker with Compose v2, and about 4 GB of free memory next to Graylog and the indexer. From this host UBA must reach the Wazuh indexer (9200) and CoPilot (5000); Graylog must reach UBA's GELF port.",
			"Create a read-only indexer user for UBA: read on wazuh-*, office365-*, graylog_* and wazuh-states-* indices, plus point-in-time search. Never use admin."
		],
		code: "docker compose version\nfree -m\ndf -h /var/lib/docker"
	},
	{
		title: "Get UBA",
		text: [
			"The repository is private: clone it with an account that has access (or pull ghcr.io/socfortress/socfortress-uba after docker login ghcr.io with a read:packages token)."
		],
		code: [
			"git clone https://github.com/socfortress/socfortress-uba.git /opt/socfortress-uba",
			"cd /opt/socfortress-uba",
			"cp .env.example .env && chmod 600 .env",
			"mkdir -p data/geoip   # mounted at /var/lib/uba: the indexer's CA, optional GeoLite2 databases"
		].join("\n")
	},
	{
		title: "Configure .env",
		text: [
			"Set these values (replace the <...> parts). Keep UBA_SECRET_KEY safe: it encrypts identity-source secrets, and a new one means entering them again. Customers are not listed here: CoPilot registers them.",
			"Copy the indexer's root CA to data/geoip/indexer-root-ca.pem. GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in the same folder add countries and networks to sign-ins (optional)."
		],
		code: [
			"POSTGRES_PASSWORD=<output of: openssl rand -hex 24>",
			"UBA_SECRET_KEY=<output of: openssl rand -base64 32 | tr '+/' '-_'>",
			"",
			"# Where things listen (UBA next to Graylog on the same host)",
			"UBA_API_PUBLISH=172.17.0.1:8010          # the API, on the Docker bridge for CoPilot's containers",
			"UBA_GELF_PUBLISH=127.0.0.1:12203         # Graylog's GELF output sends the UBA feed here",
			"UBA_POSTGRES_PUBLISH=127.0.0.1:15432",
			"UBA_REDIS_PUBLISH=127.0.0.1:16379",
			"",
			"# What CoPilot's \"Set up UBA\" creates in Graylog",
			"UBA_PROVISION_FEED_HOST=127.0.0.1        # Graylog -> UBA (matches UBA_GELF_PUBLISH)",
			"UBA_PROVISION_FEED_PORT=12203",
			"UBA_PROVISION_ALERTS_BIND=172.17.0.1     # Graylog's UBA ALERTS input, never on a public address",
			"UBA_GRAYLOG_GELF_HOST=host.docker.internal",
			"UBA_GRAYLOG_GELF_PORT=12204              # UBA alerts -> that input",
			"",
			"# Wazuh indexer: history for new customers, evidence, gap repair",
			"UBA_INDEXER__URL=https://<indexer host>:9200",
			"UBA_INDEXER__USERNAME=<read-only user>",
			"UBA_INDEXER__PASSWORD=<password>",
			"UBA_INDEXER__CA_CERTS=/var/lib/uba/indexer-root-ca.pem",
			"",
			"# UBA alerts as CoPilot incident alerts (a CoPilot service account: analyst role, no 2FA)",
			"UBA_COPILOT_URL=http://host.docker.internal:5000",
			"UBA_COPILOT_USERNAME=<service account>",
			"UBA_COPILOT_PASSWORD=<password>",
			"",
			"# Customers come from CoPilot, not from this file",
			"UBA_BOOTSTRAP_TENANTS=[]",
			"UBA_O365_TENANT_MAP={}"
		].join("\n")
	},
	{
		title: "Start it",
		text: [
			"The first start builds the image and creates the database; later starts keep everything. Check that the API answers and the worker reports every minute."
		],
		code: [
			"cd /opt/socfortress-uba",
			"docker compose up -d --build",
			"curl -s http://172.17.0.1:8010/healthz",
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
			"Platform → Connectors → SOCFortress UBA: URL http://172.17.0.1:8010 (the address in UBA_API_PUBLISH), API key from the previous step, then Verify. This page then shows UBA."
		]
	},
	{
		title: "Set each customer up",
		text: [
			"Provision the customer in CoPilot as usual (Wazuh, and Microsoft 365 if they have it). Then, on this page, pick the customer and click Set up UBA: it registers the customer with UBA and creates its Graylog streams, pipelines and output. UBA learns from the history you choose, then scores new activity. After adding Microsoft 365 later, use Setup → Run setup again."
		]
	},
	{
		title: "Upgrade",
		text: ["Pull the new version and rebuild; database migrations run on start."],
		code: "cd /opt/socfortress-uba\ngit pull\ndocker compose up -d --build"
	}
]
</script>
