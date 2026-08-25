<template>
	<div class="flex flex-col gap-4">
		<n-empty
			v-if="!hasNetwork && !loading"
			description="No network activity captured (or detonation not yet reported)."
			class="min-h-52 justify-center"
		/>

		<template v-else>
			<!-- C2 recovered from an extracted config — the one high-confidence network signal -->
			<n-alert v-if="hasExtractedC2" type="error" :bordered="false">
				<template #header>Command-and-control extracted from malware config</template>
				<div class="flex flex-wrap gap-2">
					<n-tag v-for="e of c2" :key="e" type="error" size="small" round :bordered="false">
						<code>{{ e }}</code>
					</n-tag>
				</div>
			</n-alert>

			<!-- Hosts + domains summary -->
			<div class="grid gap-4 md:grid-cols-2">
				<div class="flex flex-col gap-2">
					<div class="flex items-center gap-2">
						<Icon :name="IpIcon" :size="16" />
						<span class="text-sm font-medium">Hosts contacted</span>
						<span class="text-secondary text-xs">(observed)</span>
						<n-tag size="tiny" round :bordered="false">{{ hosts.length }}</n-tag>
					</div>
					<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
						<a
							v-for="ip of hosts"
							:key="ip"
							:href="tiUrl(ip)"
							target="_blank"
							rel="noopener noreferrer"
							class="hover:text-primary text-xs break-all underline decoration-dotted"
							:title="`Look up ${ip} on VirusTotal`"
						>
							<code>{{ ip }}</code>
						</a>
						<span v-if="!hosts.length" class="text-secondary text-xs">—</span>
					</div>
				</div>
				<div class="flex flex-col gap-2">
					<div class="flex items-center gap-2">
						<Icon :name="DomainIcon" :size="16" />
						<span class="text-sm font-medium">Domains</span>
						<n-tag size="tiny" round :bordered="false">{{ domains.length }}</n-tag>
					</div>
					<div class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
						<a
							v-for="d of domains"
							:key="d"
							:href="tiUrl(d, 'domain')"
							target="_blank"
							rel="noopener noreferrer"
							class="hover:text-primary text-xs break-all underline decoration-dotted"
							:title="`Look up ${d} on VirusTotal`"
						>
							<code>{{ d }}</code>
						</a>
						<span v-if="!domains.length" class="text-secondary text-xs">—</span>
					</div>
				</div>
			</div>

			<!-- DNS queries -->
			<div v-if="dns.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">DNS queries ({{ dns.length }})</span>
				<n-scrollbar class="bg-secondary max-h-60 rounded-lg p-3">
					<div v-for="(q, i) of dns" :key="i" class="flex flex-wrap items-center gap-2 py-0.5 text-xs">
						<n-tag v-if="q.type" size="tiny" round :bordered="false">{{ q.type }}</n-tag>
						<code class="font-medium break-all">{{ q.request }}</code>
						<span v-if="q.answers?.length" class="text-secondary">→ {{ q.answers.join(", ") }}</span>
					</div>
				</n-scrollbar>
			</div>

			<!-- HTTP requests -->
			<div v-if="http.length" class="flex flex-col gap-2">
				<span class="text-secondary text-xs font-medium">HTTP requests ({{ http.length }})</span>
				<n-scrollbar class="bg-secondary max-h-72 rounded-lg p-3">
					<div v-for="(h, i) of http" :key="i" class="flex items-center gap-2 py-0.5 text-xs">
						<n-tag size="tiny" round :bordered="false" type="info">{{ h.method || "GET" }}</n-tag>
						<code class="break-all">{{ h.host }}{{ h.uri }}</code>
					</div>
				</n-scrollbar>
			</div>

			<!-- TCP/UDP connections — grouped by endpoint so repeated chatter (e.g. DNS to
			     the gateway) collapses into one counted row instead of hundreds of lines. -->
			<div v-if="groupedConnections.length" class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<span class="text-secondary text-xs font-medium">
						Connections — {{ groupedConnections.length }} unique of {{ connections.length }}
					</span>
					<n-tag v-if="noisyCollapsed" size="tiny" round :bordered="false" type="info">deduplicated</n-tag>
				</div>
				<n-scrollbar class="bg-secondary max-h-72 rounded-lg p-3">
					<div v-for="(c, i) of groupedConnections" :key="i" class="flex items-center gap-2 py-0.5 text-xs">
						<n-tag size="tiny" round :bordered="false" :type="c.proto === 'tcp' ? 'warning' : 'default'">
							{{ c.proto.toUpperCase() }}
						</n-tag>
						<a
							v-if="looksLikeIp(c.dst)"
							:href="tiUrl(c.dst)"
							target="_blank"
							rel="noopener noreferrer"
							class="hover:text-primary break-all underline decoration-dotted"
							:title="`Look up ${c.dst} on VirusTotal`"
						>
							<code>
								{{ c.dst }}
								<span v-if="c.dport">:{{ c.dport }}</span>
							</code>
						</a>
						<code v-else class="break-all">
							{{ c.dst }}
							<span v-if="c.dport">:{{ c.dport }}</span>
						</code>
						<n-tag v-if="c.count > 1" size="tiny" round :bordered="false" class="opacity-80">
							×{{ c.count }}
						</n-tag>
					</div>
				</n-scrollbar>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { SandboxSummary } from "@/types/file-analysis"
import { NAlert, NEmpty, NScrollbar, NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { groupConnections } from "@/components/fileAnalysis/fileAnalysis.helpers"

const props = defineProps<{ sandbox?: SandboxSummary | null; loading?: boolean }>()

const DomainIcon = "carbon:web-services-container"
const IpIcon = "carbon:ibm-cloud-internet-services"

// Observed traffic. Older cached results (engine < 7) stored observed endpoints in
// the c2_* fields, so fall back to them for those — but a fresh result keeps the two
// strictly separate: c2_* means "recovered from an extracted malware config".
const hosts = computed(() => props.sandbox?.hosts ?? props.sandbox?.c2_ips ?? [])
const domains = computed(() => props.sandbox?.domains ?? props.sandbox?.c2_domains ?? [])
const c2 = computed(() => [...(props.sandbox?.c2_ips ?? []), ...(props.sandbox?.c2_domains ?? [])])
const hasExtractedC2 = computed(() => !!props.sandbox?.domains && c2.value.length > 0)
const dns = computed(() => props.sandbox?.dns ?? [])
const http = computed(() => props.sandbox?.http ?? [])
const connections = computed(() => props.sandbox?.connections ?? [])

const groupedConnections = computed(() => groupConnections(connections.value))
const noisyCollapsed = computed(() => connections.value.length > groupedConnections.value.length)

const hasNetwork = computed(
	() =>
		hosts.value.length || domains.value.length || dns.value.length || http.value.length || connections.value.length
)

function looksLikeIp(v: string): boolean {
	return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(v || "")
}
function tiUrl(indicator: string, kind: "ip" | "domain" = "ip"): string {
	const enc = encodeURIComponent(indicator)
	return kind === "domain"
		? `https://www.virustotal.com/gui/domain/${enc}`
		: `https://www.virustotal.com/gui/ip-address/${enc}`
}
</script>
