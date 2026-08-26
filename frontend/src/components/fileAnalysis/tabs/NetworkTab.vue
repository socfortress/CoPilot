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
				<!-- Data chips, not status pills: the alert around them already carries the
				     severity, so a second red pill per endpoint adds colour without adding
				     meaning. Bordered and square-cornered, they read as addresses. -->
				<div class="flex flex-wrap gap-2">
					<n-tag v-for="e of c2" :key="e" size="medium" bordered :round="false" class="font-mono">
						{{ e }}
					</n-tag>
				</div>
			</n-alert>

			<!-- "Observed" is load-bearing: it separates these from the config-extracted
			     C2 above, which is the one high-confidence signal on this tab. -->
			<div class="grid gap-4 md:grid-cols-2">
				<ValueList label="Observed hosts" :items="hosts" :link="ip => tiUrl(ip)" />
				<ValueList label="Observed domains" :items="domains" :link="d => tiUrl(d, 'domain')" />
			</div>

			<!-- Each row keeps the same hierarchy as elsewhere in the module: what kind
			     of thing it is, then the identity, then the supporting detail. -->
			<ValueList v-if="dns.length" label="DNS queries" :items="dnsItems" max-height="15rem" />

			<ValueList v-if="http.length" label="HTTP requests" :items="httpItems" max-height="18rem" />

			<!-- TCP/UDP connections — grouped by endpoint so repeated chatter (e.g. DNS to
			     the gateway) collapses into one counted row instead of hundreds of lines. -->
			<div v-if="groupedConnections.length" class="flex flex-col gap-2">
				<!-- Kept as its own header: the label states a ratio the list's own count
				     can't ("4 unique of 7"), and carries the dedup badge that explains it. -->
				<div class="flex items-center gap-2">
					<span :class="SECTION_LABEL">
						Connections
						<span class="text-tertiary normal-case">
							({{ groupedConnections.length }} unique of {{ connections.length }})
						</span>
					</span>
					<n-tag v-if="noisyCollapsed" size="tiny" round :bordered="false" type="info">deduplicated</n-tag>
				</div>
				<ValueList :items="connectionItems" max-height="18rem" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ValueListPart } from "@/components/common/value-list"
import type { SandboxSummary } from "@/types/file-analysis"
import { NAlert, NEmpty, NTag } from "naive-ui"
import { computed } from "vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import ValueList from "@/components/common/ValueList.vue"
import { groupConnections } from "@/components/fileAnalysis/fileAnalysis.helpers"

const props = defineProps<{ sandbox?: SandboxSummary | null; loading?: boolean }>()

// Observed traffic. Older cached results (engine < 7) stored observed endpoints in
// the c2_* fields, so fall back to them for those — but a fresh result keeps the two
// strictly separate: c2_* means "recovered from an extracted malware config".
// Deduplicated: these arrive raw from the sandbox report and repeat freely (the
// same resolver or CDN host is contacted many times). Duplicates rendered the same
// row twice AND made the v-for key non-unique, which is a Vue warning waiting to
// happen — the MITRE lists hit exactly that.
const hosts = computed(() => [...new Set(props.sandbox?.hosts ?? props.sandbox?.c2_ips ?? [])])
const domains = computed(() => [...new Set(props.sandbox?.domains ?? props.sandbox?.c2_domains ?? [])])
const c2 = computed(() => [...(props.sandbox?.c2_ips ?? []), ...(props.sandbox?.c2_domains ?? [])])
const hasExtractedC2 = computed(() => !!props.sandbox?.domains && c2.value.length > 0)
const dns = computed(() => props.sandbox?.dns ?? [])
const http = computed(() => props.sandbox?.http ?? [])
const connections = computed(() => props.sandbox?.connections ?? [])

const groupedConnections = computed(() => groupConnections(connections.value))
const noisyCollapsed = computed(() => connections.value.length > groupedConnections.value.length)

const dnsItems = computed<ValueListPart[][]>(() =>
	dns.value.map(q =>
		[
			{ text: q.type, tone: "accent" as const },
			{ text: q.request, tone: "strong" as const },
			{ text: q.answers?.join(", "), tone: "muted" as const }
		].filter((part): part is ValueListPart => Boolean(part.text))
	)
)

const httpItems = computed<ValueListPart[][]>(() =>
	http.value.map(h => [
		{ text: h.method || "GET", tone: "accent" as const },
		{ text: `${h.host}${h.uri}`, tone: "strong" as const }
	])
)

const connectionItems = computed<ValueListPart[][]>(() =>
	groupedConnections.value.map(c =>
		[
			{ text: c.proto.toUpperCase(), tone: "accent" as const },
			{
				text: c.dport ? `${c.dst}:${c.dport}` : c.dst,
				tone: "strong" as const,
				// Only an IP is worth a reputation lookup; a bare port or hostname
				// fragment would send the analyst to a page about nothing.
				href: looksLikeIp(c.dst) ? tiUrl(c.dst) : undefined
			},
			{ text: c.count > 1 ? `×${c.count}` : "", tone: "muted" as const }
		].filter((part): part is ValueListPart => Boolean(part.text))
	)
)

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
