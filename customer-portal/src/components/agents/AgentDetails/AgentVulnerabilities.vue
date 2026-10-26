<template>
	<div class="flex flex-col gap-3" data-testid="agent-vulnerabilities">
		<!--
			Header, in reading order: how many findings of each severity (a strip whose cells are
			also the filter), then the tools for the list — search on the left, export on the right.
		-->
		<FilterStrip
			v-model="severity"
			:options="severityStrip"
			:loading
			:label="$t('agents.agentVulnerabilities.filterLabel')"
			testid="severity"
			data-testid="vulnerabilities-severity"
		/>

		<div class="flex items-center gap-2">
			<n-input
				v-model:value="search"
				size="small"
				clearable
				:placeholder="$t('agents.agentVulnerabilities.search')"
				class="min-w-0 flex-1 @2xl:max-w-80!"
				data-testid="vulnerabilities-search"
			>
				<template #prefix><Icon name="carbon:search" :size="14" /></template>
			</n-input>
			<span
				v-if="!loading && vulnerabilities.length"
				class="text-tertiary hidden font-mono text-xs whitespace-nowrap tabular-nums @2xl:inline"
			>
				{{ $t("agents.agentVulnerabilities.shown", { count: shown.length.toLocaleString() }) }}
			</span>
			<n-button
				size="small"
				secondary
				class="ml-auto! shrink-0"
				:loading="exporting"
				:disabled="!vulnerabilities.length"
				data-testid="vulnerabilities-export"
				@click="exportCsv()"
			>
				<template #icon><Icon name="carbon:download" /></template>
				{{ $t("agents.exportCsv") }}
			</n-button>
		</div>

		<n-alert v-if="error" type="error" :bordered="false" data-testid="vulnerabilities-error">{{ error }}</n-alert>

		<section
			v-else
			class="border-default bg-default @container overflow-hidden rounded-lg border"
			:aria-busy="loading"
		>
			<div
				class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 @3xl:grid"
				:class="COLUMNS"
			>
				<span :class="HEAD">{{ $t("agents.agentVulnerabilities.head.severity") }}</span>
				<span :class="HEAD">{{ $t("agents.agentVulnerabilities.head.vulnerability") }}</span>
				<span :class="HEAD">{{ $t("agents.agentVulnerabilities.head.package") }}</span>
				<span :class="HEAD" class="text-right">CVSS</span>
				<span :class="HEAD">{{ $t("agents.agentVulnerabilities.head.detected") }}</span>
				<span />
			</div>

			<div v-if="loading" class="flex flex-col gap-3 p-3" data-testid="vulnerabilities-loading">
				<!-- Wazuh builds the list per request: on an agent with many packages that takes a while. -->
				<p class="text-secondary m-0 flex items-start gap-2 text-sm" role="status">
					<Icon name="carbon:renew" :size="16" class="text-primary mt-0.5 shrink-0 animate-spin" />
					<span>{{ $t("agents.agentVulnerabilities.loading") }}</span>
				</p>
				<n-skeleton v-for="n of 5" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!shown.length"
				:description="
					vulnerabilities.length
						? $t('agents.agentVulnerabilities.emptyFiltered')
						: $t('agents.agentVulnerabilities.empty')
				"
				class="min-h-40 justify-center"
				data-testid="vulnerabilities-empty"
			/>
			<div v-else class="divide-border flex flex-col divide-y">
				<div
					v-for="v of page"
					:key="`${v.cve}-${v.name}-${v.version}`"
					:class="{ 'pb-4': expanded.has(key(v)) }"
					data-testid="vulnerability-row"
				>
					<button
						type="button"
						class="group hover:bg-secondary/50 grid w-full cursor-pointer items-center gap-x-3 gap-y-1.5 px-4 py-2.5 text-left transition-colors @3xl:gap-x-4 @3xl:gap-y-0"
						:class="[COLUMNS_ROW, { 'bg-secondary/50': expanded.has(key(v)) }]"
						:aria-expanded="expanded.has(key(v))"
						@click="toggle(key(v))"
					>
						<span class="[grid-area:sev]">
							<span :class="[CHIP, severityClasses(v.severity)]">{{ severityLabel(v.severity) }}</span>
						</span>
						<span class="flex min-w-0 flex-col gap-0.5 leading-tight [grid-area:vuln]">
							<span class="text-default truncate font-mono text-sm">{{ v.cve ?? "—" }}</span>
							<span v-if="v.title" class="text-secondary line-clamp-2 text-xs @3xl:line-clamp-1">
								{{ v.title }}
							</span>
						</span>
						<span
							class="flex min-w-0 items-baseline gap-2 leading-tight [grid-area:pkg] @3xl:flex-col @3xl:gap-0"
						>
							<span class="text-default truncate text-sm">{{ v.name ?? "—" }}</span>
							<span v-if="v.version" class="text-tertiary truncate font-mono text-xs">
								{{ v.version }}
							</span>
						</span>
						<span
							class="text-right font-mono text-sm tabular-nums [grid-area:cvss]"
							:class="cvssClass(v.cvss3_score)"
						>
							<span class="text-tertiary mr-1 text-xs font-normal uppercase @3xl:hidden">cvss</span>
							{{ formatCvss(v.cvss3_score) }}
						</span>
						<span class="text-secondary hidden text-xs whitespace-nowrap [grid-area:det] @3xl:block">
							{{ v.detection_time ? relative(v.detection_time) : "—" }}
						</span>
						<Icon
							name="carbon:chevron-down"
							:size="14"
							class="text-tertiary group-hover:text-default justify-self-end transition-transform duration-200 [grid-area:chev]"
							:class="{ 'rotate-180': expanded.has(key(v)) }"
						/>
					</button>

					<div
						v-if="expanded.has(key(v))"
						class="bg-secondary/30 border-default flex flex-col gap-4 border-y px-4 pt-4 pb-5"
						data-testid="vulnerability-detail"
					>
						<p v-if="v.title" class="text-default m-0 text-sm">{{ v.title }}</p>
						<dl class="m-0 grid grid-cols-2 gap-x-6 gap-y-3 @3xl:grid-cols-4">
							<div v-for="fact of facts(v)" :key="fact.label" class="flex min-w-0 flex-col gap-0.5">
								<dt :class="HEAD" class="text-tertiary">{{ fact.label }}</dt>
								<dd class="text-default m-0 truncate text-xs" :class="{ 'font-mono': fact.mono }">
									{{ fact.value }}
								</dd>
							</div>
						</dl>
						<div v-if="v.external_references?.length" class="flex min-w-0 flex-col gap-1.5">
							<span :class="HEAD" class="text-tertiary">
								{{ $t("agents.agentVulnerabilities.references", { count: v.external_references.length }) }}
							</span>
							<a
								v-for="url of v.external_references"
								:key="url"
								:href="url"
								target="_blank"
								rel="noopener noreferrer"
								class="text-primary truncate font-mono text-xs hover:underline"
							>
								{{ url }}
							</a>
						</div>
					</div>
				</div>
			</div>

			<footer
				v-if="shown.length > PAGE_SIZES[0]"
				class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
			>
				<span class="text-tertiary font-mono text-xs tabular-nums" data-testid="vulnerabilities-range">
					{{ rangeLabel }}
				</span>
				<n-pagination
					v-model:page="pageNumber"
					v-model:page-size="pageSize"
					:item-count="shown.length"
					:page-sizes="PAGE_SIZES"
					:page-slot="6"
					show-size-picker
					size="small"
				/>
			</footer>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { FilterStripOption } from "./FilterStrip.vue"
import type { AgentVulnerability, VulnerabilitySeverity } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NAlert, NButton, NEmpty, NInput, NPagination, NSkeleton, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import {
	exportFilename,
	filterVulnerabilities,
	formatCvss,
	pageRangeLabel,
	SEVERITIES,
	severityClasses,
	severityCounts,
	severityDot,
	severityLabel
} from "./agentFindings"
import FilterStrip from "./FilterStrip.vue"

/**
 * An agent's vulnerabilities, as Wazuh found them (#1256): fetched once with every severity,
 * then filtered, counted and paged here; the export asks for the severity on screen.
 */

const {
	agentId,
	agentLabel,
	initialSearch = ""
} = defineProps<{
	agentId: string
	agentLabel: string
	/** Prefilled by a link (a CVE from the Exposure page, #1289). */
	initialSearch?: string
}>()

const PAGE_SIZES = [25, 50, 100]
const HEAD = "text-xxs font-medium tracking-[0.12em] uppercase"
const CHIP = "inline-flex rounded border px-1.5 py-0.5 text-xxs font-medium tracking-wide uppercase"
// Every cell placed by area, by the list's own width: narrow, a small card (severity and
// score on top, then the CVE and its title, then the package); wide, one line.
const COLUMNS = "grid-cols-[6rem_minmax(0,1.6fr)_minmax(0,1fr)_3.5rem_7rem_1rem]"
const COLUMNS_ROW = [
	"grid-cols-[auto_minmax(0,1fr)_auto_auto]",
	"[grid-template-areas:'sev_._cvss_chev'_'vuln_vuln_vuln_vuln'_'pkg_pkg_pkg_pkg']",
	"@3xl:grid-cols-[6rem_minmax(0,1.6fr)_minmax(0,1fr)_3.5rem_7rem_1rem]",
	"@3xl:[grid-template-areas:'sev_vuln_pkg_cvss_det_chev']"
].join(" ")

const message = useMessage()
const { t } = useI18n()
const dFormats = useSettingsStore().dateFormat
const { loading, run } = useLatestRequest()
const vulnerabilities = ref<AgentVulnerability[]>([])
const error = ref<string | null>(null)
const severity = ref<VulnerabilitySeverity | "All">("All")
const search = ref(initialSearch)
const pageNumber = ref(1)
const pageSize = ref(PAGE_SIZES[0])
const expanded = ref(new Set<string>())
const exporting = ref(false)

const counts = computed(() => severityCounts(vulnerabilities.value))
const severityStrip = computed<FilterStripOption<VulnerabilitySeverity | "All">[]>(() =>
	(["All", ...SEVERITIES] as const).map(value => ({
		value,
		label: severityLabel(value),
		count: counts.value[value],
		dot: value === "All" ? "bg-primary" : severityDot(value)
	}))
)
const shown = computed(() =>
	filterVulnerabilities(vulnerabilities.value, { severity: severity.value, search: search.value })
)
const offset = computed(() => (pageNumber.value - 1) * pageSize.value)
const page = computed(() => shown.value.slice(offset.value, offset.value + pageSize.value))
const rangeLabel = computed(
	() => pageRangeLabel(offset.value + 1, Math.min(offset.value + pageSize.value, shown.value.length), shown.value.length)
)

const key = (v: AgentVulnerability) => `${v.cve}-${v.name}-${v.version}`
const relative = (ts: string) => dayjs(ts).fromNow()

function cvssClass(score: number | null) {
	if (score == null) return "text-tertiary"
	if (score >= 9) return "text-error font-semibold"
	if (score >= 7) return "text-warning font-semibold"
	return "text-default"
}

function facts(v: AgentVulnerability) {
	const date = (value: string | null) => (value ? String(formatDate(value, dFormats.datetime)) : "—")
	return [
		{
			label: t("agents.agentVulnerabilities.facts.package"),
			value: [v.name, v.version].filter(Boolean).join(" ") || "—",
			mono: true
		},
		{ label: t("agents.agentVulnerabilities.facts.architecture"), value: v.architecture ?? "—", mono: true },
		{ label: t("agents.agentVulnerabilities.facts.type"), value: v.type ?? "—", mono: false },
		{ label: t("common.fields.status"), value: v.status ?? "—", mono: false },
		{ label: "CVSS 3", value: formatCvss(v.cvss3_score), mono: true },
		{ label: t("agents.agentVulnerabilities.facts.published"), value: date(v.published), mono: true },
		{ label: t("agents.agentVulnerabilities.facts.detected"), value: date(v.detection_time), mono: true }
	]
}

function toggle(id: string) {
	const next = new Set(expanded.value)
	if (next.has(id)) next.delete(id)
	else next.add(id)
	expanded.value = next
}

function load() {
	error.value = null
	return run(
		async signal => {
			vulnerabilities.value = (await Api.agents.getVulnerabilities(agentId, signal)).data.vulnerabilities ?? []
		},
		err => {
			error.value = getApiErrorMessage(err as ApiError) || t("agents.agentVulnerabilities.loadFailed")
		}
	)
}

async function exportCsv() {
	exporting.value = true
	try {
		const response = await Api.agents.exportVulnerabilities(agentId, severity.value)
		saveAs(response.data, exportFilename(`vulnerabilities-${severity.value.toLowerCase()}`, agentLabel))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("agents.agentVulnerabilities.exportFailed"))
	} finally {
		exporting.value = false
	}
}

// A narrower list starts again from its first page.
watch([severity, search, pageSize], () => {
	pageNumber.value = 1
	expanded.value = new Set()
})

onBeforeMount(load)
</script>
