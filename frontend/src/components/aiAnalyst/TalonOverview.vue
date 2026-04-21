<template>
	<div class="flex flex-col gap-8 p-2">
		<!-- Hero -->
		<div class="flex flex-col items-center gap-3 py-6 text-center">
			<div class="bg-primary/10 flex h-16 w-16 items-center justify-center rounded-2xl">
				<Icon name="carbon:machine-learning-model" :size="32" class="text-primary" />
			</div>
			<h1 class="text-default text-2xl font-bold">Talon AI Analyst</h1>
			<p class="text-secondary max-w-xl text-sm leading-relaxed">
				Automated Tier 1 SOC analyst that investigates every alert end-to-end &mdash; from raw SIEM events to
				structured investigation reports with severity assessments and recommended actions.
			</p>
			<div class="mt-1 flex items-center gap-2">
				<n-tag size="small" round type="success">
					<template #icon>
						<Icon name="carbon:checkmark-filled" />
					</template>
					Integrated
				</n-tag>
				<n-tag
					v-if="status"
					size="small"
					round
					:type="status === 'healthy' ? 'success' : 'warning'"
					class="animate-fade"
				>
					{{ status === "healthy" ? "Online" : status }}
				</n-tag>
				<n-tag v-else-if="statusChecked" size="small" round type="error" class="animate-fade">
					Unreachable
				</n-tag>
			</div>
			<a
				href="https://github.com/taylorwalton/talon"
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary mt-1 inline-flex items-center gap-1.5 text-xs no-underline hover:underline"
			>
				<Icon name="carbon:logo-github" :size="14" />
				<span>github.com/taylorwalton/talon</span>
				<Icon name="carbon:launch" :size="11" />
			</a>
		</div>

		<!-- How It Works -->
		<section>
			<SectionHeader title="How It Works" icon="carbon:flow" />
			<div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<StepCard
					v-for="item in investigationSteps"
					:key="item.step"
					:step="item.step"
					:title="item.title"
					:description="item.description"
					:icon="item.icon"
				/>
			</div>
		</section>

		<!-- Capabilities -->
		<section>
			<SectionHeader title="Capabilities" icon="carbon:catalog" />
			<div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
				<FeatureCard
					v-for="feature in capabilities"
					:key="feature.title"
					:title="feature.title"
					:description="feature.description"
					:icon="feature.icon"
				/>
			</div>
		</section>

		<!-- Architecture -->
		<section>
			<SectionHeader title="Architecture" icon="carbon:network-4" />
			<div class="bg-secondary mt-3 overflow-x-auto rounded-lg p-5">
				<pre class="text-default text-xs leading-relaxed"><code>{{ architectureDiagram }}</code></pre>
			</div>
		</section>

		<!-- Integration Points -->
		<section>
			<SectionHeader title="CoPilot Integration" icon="carbon:connect" />
			<div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
				<FeatureCard
					v-for="point in integrationPoints"
					:key="point.title"
					:title="point.title"
					:description="point.description"
					:icon="point.icon"
				/>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { NTag } from "naive-ui"
import { defineComponent, h, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

// --- Inline sub-components ---

const SectionHeader = defineComponent({
	props: { title: String, icon: String },
	setup(props) {
		return () =>
			h("div", { class: "flex items-center gap-2" }, [
				h(Icon, { name: props.icon, size: 18, class: "text-primary" }),
				h("h2", { class: "text-default text-lg font-semibold" }, props.title)
			])
	}
})

const StepCard = defineComponent({
	props: { step: Number, title: String, description: String, icon: String },
	setup(props) {
		return () =>
			h("div", { class: "bg-secondary flex gap-3 rounded-lg p-4" }, [
				h(
					"div",
					{ class: "bg-primary/10 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" },
					h("span", { class: "text-primary text-sm font-bold" }, props.step)
				),
				h("div", { class: "flex flex-col gap-1" }, [
					h("div", { class: "text-default text-sm font-semibold" }, props.title),
					h("div", { class: "text-secondary text-xs leading-relaxed" }, props.description)
				])
			])
	}
})

const FeatureCard = defineComponent({
	props: { title: String, description: String, icon: String },
	setup(props) {
		return () =>
			h("div", { class: "bg-secondary flex gap-3 rounded-lg p-4" }, [
				h(
					"div",
					{ class: "bg-primary/10 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" },
					h(Icon, { name: props.icon, size: 16, class: "text-primary" })
				),
				h("div", { class: "flex flex-col gap-1" }, [
					h("div", { class: "text-default text-sm font-semibold" }, props.title),
					h("div", { class: "text-secondary text-xs leading-relaxed" }, props.description)
				])
			])
	}
})

// --- Status check ---

const status = ref<string | null>(null)
const statusChecked = ref(false)

onMounted(() => {
	Api.talon
		.getStatus()
		.then(res => {
			status.value = res.data.success ? "healthy" : "degraded"
		})
		.catch(() => {
			status.value = null
		})
		.finally(() => {
			statusChecked.value = true
		})
})

// --- Static content ---

const investigationSteps = [
	{
		step: 1,
		title: "Alert Ingestion",
		description:
			"Talon picks up OPEN alerts via real-time webhook (POST /investigate) or a 15-minute scheduled sweep as a safety net.",
		icon: "carbon:notification"
	},
	{
		step: 2,
		title: "SIEM Correlation",
		description:
			"Queries OpenSearch/Wazuh for the raw event and correlated events across the same asset, time window, and rule groups.",
		icon: "carbon:search"
	},
	{
		step: 3,
		title: "IOC Enrichment",
		description:
			"Extracts IOCs (IPs, hashes, domains, user accounts) and enriches them via VirusTotal, Shodan, and AbuseIPDB.",
		icon: "carbon:security"
	},
	{
		step: 4,
		title: "Report & Write-back",
		description:
			"Generates a structured investigation report with MITRE ATT&CK mapping, severity assessment, and recommended actions — written back to CoPilot.",
		icon: "carbon:document"
	}
]

const capabilities = [
	{
		title: "Privacy-Aware Anonymization",
		description:
			"An anonymizing MCP proxy replaces PII (usernames, hostnames, internal IPs) with session tokens before they reach the cloud model. A deanonymize tool restores real values in the final report.",
		icon: "carbon:locked"
	},
	{
		title: "Local LLM Support",
		description:
			"If Ollama is running, raw event interpretation routes through a local model — keeping the most sensitive analysis step entirely on-premises. No config needed if on the same host.",
		icon: "carbon:model-alt"
	},
	{
		title: "MemPalace Persistent Memory",
		description:
			"Long-term memory via ChromaDB + SQLite — past investigation outcomes, asset metadata, confirmed false positives, and IOC history are retrieved automatically at the start of each investigation.",
		icon: "carbon:data-base"
	},
	{
		title: "Alert-Type Templates",
		description:
			"Per-alert-type investigation guides (Sysmon Event 1, 3, 7, 11, 22, etc.) load automatically based on the alert's rule.groups field. Add new templates without touching code.",
		icon: "carbon:template"
	},
	{
		title: "MITRE ATT&CK Mapping",
		description:
			"Every investigation maps findings to MITRE ATT&CK tactics and techniques, providing standardized classification for SOC analysts and compliance reporting.",
		icon: "carbon:chart-relationship"
	},
	{
		title: "Containerized Isolation",
		description:
			"Each investigation runs in an isolated Linux container with a mount allowlist controlling file system access. Agents cannot modify their own configuration or escape the sandbox.",
		icon: "carbon:container-software"
	}
]

const integrationPoints = [
	{
		title: "Real-Time Investigation Trigger",
		description:
			"When an alert is created in CoPilot's Incident Management, Talon can be triggered immediately via POST /investigate. The \"Investigate with AI Analyst\" button on any alert's Overview tab does exactly this.",
		icon: "carbon:flash"
	},
	{
		title: "Scheduled Alert Sweep",
		description:
			"Every 15 minutes, Talon queries the CoPilot database for OPEN alerts with no existing job and automatically investigates them — a safety net ensuring nothing is missed.",
		icon: "carbon:time"
	},
	{
		title: "Report Write-back via MCP",
		description:
			"Job status, full investigation reports, and enriched IOCs are persisted back into CoPilot's database via the CoPilot MCP server — no direct database writes from Talon.",
		icon: "carbon:document-add"
	},
	{
		title: "In-Alert Report Viewing",
		description:
			"When you open any alert in Incident Management, the AI Analyst tab automatically loads if an investigation report exists — showing severity, summary, full report, and recommended actions.",
		icon: "carbon:view"
	}
]

const architectureDiagram = `┌──────────────────────────────────────────────────────┐
│                  CoPilot (FastAPI)                    │
│                                                      │
│  Alert created → POST /investigate ──────────────┐   │
│  GET /status, GET /jobs/:alertId ← Talon HTTP API│   │
│                                                  │   │
│  Write-back API (MCP tools):                     │   │
│    POST /api/ai_analyst/jobs         ←───────────┘   │
│    POST /api/ai_analyst/reports                      │
│    POST /api/ai_analyst/iocs                         │
│  MySQL: ai_analyst_job / report / ioc                │
└───────────────────────┬──────────────────────────────┘
                        │ read-only MCP        ▲ REST write-back
                        ▼                      │
┌──────────────────────────────────────────────────────┐
│                    Talon (Node.js)                    │
│                                                      │
│  HTTP channel (port 3100)                            │
│    POST /investigate  ← CoPilot triggers this        │
│    POST /message      ← ad-hoc analyst prompts       │
│    GET  /status       ← queue + job overview         │
│                                                      │
│  Scheduled task (every 15 min)                       │
│    Queries MySQL for OPEN alerts with no job row     │
│    Runs full investigation per alert                 │
│                                                      │
│  SOC agent (containerized)                           │
│    groups/copilot/CLAUDE.md  ← investigation flow    │
│    groups/copilot/prompts/   ← per-alert templates   │
└──────────────────────────────────────────────────────┘
         │ MCP tools (read-only)
         ▼
┌──────────────────────────────────────────────────────┐
│  opensearch-mcp    — raw SIEM queries                │
│  opensearch_anon   — anonymizing proxy (PII→tokens)  │
│  mysql-mcp         — CoPilot DB (alerts, assets)     │
│  copilot-mcp       — CoPilot REST API write-back     │
│  ollama (optional) — local LLM for sensitive data    │
│  mempalace         — persistent investigation memory │
└──────────────────────────────────────────────────────┘`
</script>
