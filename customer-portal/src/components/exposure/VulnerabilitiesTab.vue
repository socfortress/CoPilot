<template>
	<div class="flex flex-col gap-3" data-testid="exposure-vulnerabilities">
		<ExposureDisabled v-if="data && !data.enabled" />

		<template v-else>
			<!-- Counts that are also the filter: distinct CVEs of each severity, all agents together.
				 No figures (—) while loading or when Wazuh could not be read: a 0 would read as "none". -->
			<FilterStrip
				v-model="severityModel"
				:options="severityOptions(data?.severities ?? [], !countsKnown)"
				:loading="!countsKnown"
				label="Filter by severity"
				testid="exposure-severity"
			/>

			<div class="flex flex-wrap items-center gap-2">
				<n-input
					v-model:value="searchInput"
					size="small"
					clearable
					placeholder="Search a CVE id or a package"
					class="min-w-0 flex-1 @2xl:max-w-80!"
					:maxlength="100"
					data-testid="exposure-search"
				>
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
				<span
					v-if="data && !data.error"
					class="text-tertiary font-mono text-xs whitespace-nowrap tabular-nums"
					data-testid="exposure-totals"
				>
					{{ totalsLine(data.totals) }}
				</span>
				<n-button
					size="small"
					secondary
					class="ml-auto! shrink-0"
					:loading="exporting"
					:disabled="!data?.totals.findings"
					data-testid="exposure-export"
					@click="exportCsv()"
				>
					<template #icon><Icon name="carbon:download" /></template>
					Export CSV
				</n-button>
			</div>

			<n-alert v-if="failure" type="error" :bordered="false" data-testid="exposure-error">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<span>{{ failure }}</span>
					<n-button size="small" secondary @click="reload()">Try again</n-button>
				</div>
			</n-alert>

			<section
				v-else
				class="border-default bg-default @container overflow-hidden rounded-lg border"
				:aria-busy="loading || undefined"
			>
				<div
					class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 @3xl:grid"
					:class="COLUMNS"
				>
					<span :class="HEAD">Severity</span>
					<span :class="HEAD">Vulnerability</span>
					<span :class="HEAD" class="text-right">Agents</span>
					<span :class="HEAD" class="text-right">CVSS</span>
					<span :class="HEAD" class="text-right">EPSS</span>
					<span :class="HEAD">First seen</span>
					<span />
				</div>

				<div v-if="!data" class="flex flex-col gap-3 p-3" data-testid="exposure-loading">
					<n-skeleton v-for="n of 6" :key="n" :height="44" :sharp="false" class="rounded-md" />
				</div>
				<n-empty
					v-else-if="!data.cves.length"
					:description="
						data.agents_in_scope === 0
							? 'No agent to assess yet'
							: state.severity || state.search
								? 'No vulnerability matches the filters'
								: 'No vulnerabilities found on your agents'
					"
					class="min-h-40 justify-center"
					data-testid="exposure-empty"
				/>
				<div v-else class="divide-border flex flex-col divide-y" :class="{ 'opacity-60': loading }">
					<button
						v-for="row of data.cves"
						:key="row.cve_id"
						type="button"
						class="group hover:bg-secondary/50 focus-visible:outline-primary grid w-full cursor-pointer items-center gap-x-3 gap-y-1.5 px-4 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 @3xl:gap-x-4 @3xl:gap-y-0"
						:class="COLUMNS_ROW"
						:data-cve="row.cve_id"
						data-testid="exposure-cve-row"
						@click="openCve(row.cve_id)"
					>
						<span class="[grid-area:sev]">
							<span :class="[CHIP, severityClasses(row.severity)]">{{ row.severity ?? "unknown" }}</span>
						</span>
						<span class="flex min-w-0 flex-col gap-0.5 leading-tight [grid-area:vuln]">
							<span class="text-default truncate font-mono text-sm">{{ row.cve_id }}</span>
							<span v-if="row.packages.length" class="text-secondary truncate text-xs" :title="row.packages.join(', ')">
								<bdi>{{ row.packages.join(", ") }}</bdi>
							</span>
						</span>
						<span class="text-default text-right font-mono text-sm tabular-nums [grid-area:hosts]">
							<span class="text-tertiary mr-1 text-xs uppercase @3xl:hidden">agents</span>
							{{ row.hosts.toLocaleString() }}
						</span>
						<span class="text-right font-mono text-sm tabular-nums [grid-area:cvss]" :class="cvssClass(row.cvss)">
							<span class="text-tertiary mr-1 text-xs font-normal uppercase @3xl:hidden">cvss</span>
							{{ formatCvss(row.cvss) }}
						</span>
						<span class="text-secondary text-right font-mono text-sm tabular-nums [grid-area:epss]">
							<span class="text-tertiary mr-1 text-xs uppercase @3xl:hidden">epss</span>
							{{ formatEpss(row.epss) }}
						</span>
						<span class="text-secondary hidden text-xs whitespace-nowrap [grid-area:seen] @3xl:block">
							{{ row.first_detected ? formatDate(row.first_detected, dFormats.date, { tz: true }) : "—" }}
						</span>
						<Icon
							name="carbon:chevron-right"
							:size="14"
							class="text-tertiary group-hover:text-default justify-self-end [grid-area:chev]"
						/>
					</button>
				</div>

				<footer
					v-if="data && data.total_cves > PAGE_SIZE"
					class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
				>
					<span class="text-tertiary font-mono text-xs tabular-nums" data-testid="exposure-range">
						{{ rangeLabel }}
					</span>
					<n-pagination
						:page="state.page"
						:page-count
						:page-slot="6"
						size="small"
						data-testid="exposure-pagination"
						@update:page="setPage"
					/>
				</footer>
				<p
					v-if="data?.truncated"
					class="text-tertiary border-default border-t px-4 py-2 text-xs"
					data-testid="exposure-truncated"
				>
					Only the 10,000 highest-scoring CVEs are ranked: narrow the search or the severity to see the rest.
				</p>
			</section>
		</template>

		<CveDrawer v-model:show="drawerOpen" :cve-id="drawerCve" />
	</div>
</template>

<script setup lang="ts">
import type { VulnerabilityState } from "./exposure"
import type { ApiError } from "@/types/common"
import type { ExposureSeverity } from "@/types/exposure"
import { refDebounced } from "@vueuse/core"
import { saveAs } from "file-saver"
import { NAlert, NButton, NEmpty, NInput, NPagination, NSkeleton, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import FilterStrip from "@/components/agents/AgentDetails/FilterStrip.vue"
import Icon from "@/components/common/Icon.vue"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CveDrawer from "./CveDrawer.vue"
import {
	exportFilename,
	formatCvss,
	formatEpss,
	PAGE_SIZE,
	severityClasses,
	severityOptions,
	totalsLine,
	vulnerabilityStateFromQuery,
	withExposureQuery
} from "./exposure"
import ExposureDisabled from "./ExposureDisabled.vue"
import { useExposureVulnerabilities } from "./useExposure"

/**
 * The Exposure page's vulnerabilities (#1289): distinct CVEs across all the customer's agents,
 * the highest CVSS first, then the most agents. Severity, search and page live in the URL; a
 * row opens the CVE with the agents it affects.
 */

const HEAD = "text-xxs font-medium tracking-[0.12em] uppercase"
const CHIP = "inline-flex rounded border px-1.5 py-0.5 text-xxs font-medium tracking-wide uppercase"
const COLUMNS = "grid-cols-[6rem_minmax(0,1fr)_4.5rem_4rem_4.5rem_7rem_1rem]"
const COLUMNS_ROW = [
	"grid-cols-[auto_minmax(0,1fr)_auto]",
	"[grid-template-areas:'sev_vuln_chev'_'hosts_cvss_epss']",
	"@3xl:grid-cols-[6rem_minmax(0,1fr)_4.5rem_4rem_4.5rem_7rem_1rem]",
	"@3xl:[grid-template-areas:'sev_vuln_hosts_cvss_epss_seen_chev']"
]

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const customerFilterStore = useCustomerFilterStore()

const state = computed<VulnerabilityState>(() => vulnerabilityStateFromQuery(route.query))
const { data, error, loading, reload } = useExposureVulnerabilities(state)

const failure = computed(() => error.value || data.value?.error || null)
const countsKnown = computed(() => !!data.value && !data.value.error)
const pageCount = computed(() => Math.max(1, Math.ceil(Math.min(data.value?.total_cves ?? 0, 10000) / PAGE_SIZE)))
const rangeLabel = computed(() => {
	const total = data.value?.total_cves ?? 0
	const start = (state.value.page - 1) * PAGE_SIZE + 1
	return `${start.toLocaleString()}–${Math.min(start + PAGE_SIZE - 1, total).toLocaleString()} of ${total.toLocaleString()} CVEs`
})

function write(next: Partial<VulnerabilityState>) {
	const merged = { ...state.value, ...next }
	router.replace({ query: withExposureQuery(route.query, "vulnerabilities", merged) })
}

const severityModel = computed<ExposureSeverity | "All">({
	get: () => state.value.severity ?? "All",
	// A narrower list starts again from its first page.
	set: value => write({ severity: value === "All" ? null : value, page: 1 })
})

function setPage(page: number) {
	write({ page })
}

// Typed, so debounced; the URL changing under us (back, a link) refills the box.
const searchInput = ref(state.value.search)
watch(refDebounced(searchInput, 300), value => {
	if ((value ?? "").trim() !== state.value.search) write({ search: value ?? "", page: 1 })
})
watch(
	() => state.value.search,
	value => {
		if ((searchInput.value ?? "").trim() !== value) searchInput.value = value
	}
)

function cvssClass(score: number | null) {
	if (score == null) return "text-tertiary"
	if (score >= 9) return "text-error font-semibold"
	if (score >= 7) return "text-warning font-semibold"
	return "text-default"
}

const drawerOpen = ref(false)
const drawerCve = ref<string | null>(null)

function openCve(cveId: string) {
	drawerCve.value = cveId
	drawerOpen.value = true
}

const exporting = ref(false)

async function exportCsv() {
	exporting.value = true
	try {
		const { severity, search } = state.value
		const response = await Api.exposure.exportVulnerabilities({ severity, search }, customerFilterStore.queryCustomerCodes)
		saveAs(response.data, exportFilename({ severity, search }))
		if (response.headers?.["x-export-truncated"] === "true") {
			message.warning("The CSV holds the first 100,000 findings: narrow the severity or the search for the rest.")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not export the vulnerabilities.")
	} finally {
		exporting.value = false
	}
}
</script>
