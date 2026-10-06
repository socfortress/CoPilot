<template>
	<div class="uba-deploy-guide flex flex-col gap-6 text-sm">
		<p class="text-default max-w-3xl">
			SOCFortress UBA runs as its own small Docker Compose stack (API, GELF receiver, worker, Postgres, Redis) on
			a VM in the same network as Graylog, the Wazuh indexer and CoPilot. Graylog sends it a copy of each
			customer's Wazuh and Microsoft 365 events, UBA reads history from the Wazuh indexer, and CoPilot talks to
			its API. Once it is running and connected, every customer is set up from this page with one click. Below,
			replace the &lt;uba-ip&gt;, &lt;graylog-ip&gt;, &lt;indexer-ip&gt; and &lt;copilot-ip&gt; placeholders with
			those hosts' addresses.
		</p>

		<div class="flex flex-col gap-6">
			<div v-for="(step, i) of STEPS" :key="step.title" class="flex flex-col gap-2">
				<div class="flex items-baseline gap-2">
					<n-tag size="small" round :bordered="false">{{ i + 1 }}</n-tag>
					<b>{{ step.title }}</b>
				</div>
				<p v-for="(line, j) of step.text" :key="j" class="text-secondary max-w-3xl">{{ line }}</p>
				<CodeSource v-if="step.code" :code="step.code" lang="shellscript" :max-height="360" />
			</div>
		</div>
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

const REPO = "https://github.com/socfortress/socfortress-uba-deploy"

// The customer layout (UBA's docs/13-deployment-operations.md, "On its own VM"): UBA on its own VM in
// the VLAN of Graylog, the indexer and CoPilot, deployed from the public socfortress-uba-deploy
// repository (compose file on the public image, .env.example, README).
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
		text: [
			"Clone the public deployment repository: a Docker Compose file that runs the public UBA image, a settings template and a README with every detail."
		],
		code: [
			`git clone ${REPO}.git /opt/socfortress-uba`,
			"cd /opt/socfortress-uba",
			"cp .env.example .env && chmod 600 .env"
		].join("\n")
	},
	{
		title: "Fill in .env",
		text: [
			"Replace every <...> value in .env: the addresses of this VM, Graylog, the Wazuh indexer and CoPilot on the private network; two generated secrets (the file shows the commands); the indexer's admin password; and a CoPilot service account for UBA's alerts (analyst role, no 2FA). Keep UBA_SECRET_KEY: it encrypts stored secrets, and a new one means entering them again.",
			"Optional: GeoLite2-City.mmdb and GeoLite2-ASN.mmdb in data/geoip add countries and networks to sign-ins; without them the new-country, new-network and impossible-travel rules stay quiet."
		],
		code: [
			"UBA_PROVISION_FEED_HOST=<uba-ip>        # Graylog sends the UBA feed to this VM",
			"UBA_GRAYLOG_GELF_HOST=<graylog-ip>      # UBA sends its alerts back to Graylog",
			"UBA_INDEXER__URL=https://<indexer-ip>:9200",
			"UBA_INDEXER__PASSWORD=<indexer admin password>",
			"UBA_COPILOT_URL=http://<copilot-ip>:5000",
			"UBA_COPILOT_USERNAME=<service account>",
			"UBA_COPILOT_PASSWORD=<password>",
			"POSTGRES_PASSWORD=<openssl rand -hex 24>",
			"UBA_SECRET_KEY=<openssl rand -base64 32 | tr '+/' '-_'>"
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
			"Postgres holds what UBA has learned, its identities and alerts: back it up nightly (the repository's README also shows the restore). UBA runs the version set in UBA_TAG; releases are listed on the deployment repository's Releases page. To upgrade, pull the repository, set UBA_TAG to the new version, then pull the image and restart; database migrations run first."
		],
		code: [
			"# nightly backup (in a crontab line, write each % as \\%)",
			"cd /opt/socfortress-uba && docker compose exec -T postgres pg_dump -U uba -Fc uba > /backup/uba-$(date +%F).dump",
			"",
			"# upgrade",
			"cd /opt/socfortress-uba && git pull",
			"sed -i 's/^UBA_TAG=.*/UBA_TAG=<new version>/' .env",
			"docker compose pull && docker compose up -d"
		].join("\n")
	}
]
</script>
