<template>
	<div class="flex flex-col gap-3 pt-2" data-testid="cloud-checks">
		<div class="flex flex-wrap items-center gap-2">
			<n-select v-model:value="status" :options="STATUS_OPTIONS" clearable placeholder="Every outcome" class="w-44!" aria-label="Outcome" />
			<n-select
				v-model:value="severity"
				:options="severityOptions"
				multiple
				clearable
				max-tag-count="responsive"
				placeholder="Every severity"
				class="w-60!"
				aria-label="Severity"
			/>
			<n-select
				v-model:value="service"
				:options="serviceOptions"
				clearable
				filterable
				placeholder="Every service"
				class="w-48!"
				aria-label="Service"
			/>
			<n-input v-model:value="query" clearable placeholder="Search checks" class="w-64!" aria-label="Search checks">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>

		<n-alert v-if="error" type="error" :bordered="false">{{ errorText }}</n-alert>

		<section class="border-default bg-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<header class="bg-secondary border-default flex flex-wrap items-baseline justify-between gap-2 border-b px-4 py-2">
				<span :class="SECTION_LABEL">Checks</span>
				<span class="text-secondary text-2xs font-mono tabular-nums">{{ total }} matching</span>
			</header>
			<div v-if="loading && !checks.length" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 4" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty v-else-if="!checks.length" description="No check matches" class="py-10" />
			<div v-else class="divide-border flex flex-col divide-y">
				<div v-for="check of checks" :key="check.check_id" :data-testid="`cloud-check-${check.check_id}`">
					<button
						type="button"
						class="hover:bg-secondary/50 grid w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1 px-4 py-2.5 text-left transition-colors md:grid-cols-[6rem_minmax(0,1fr)_7rem_16rem]"
						:aria-expanded="expanded === check.check_id"
						@click="expanded = expanded === check.check_id ? null : check.check_id"
					>
						<n-tag :type="SEVERITY_TAGS[check.severity]" size="tiny" round :bordered="false" class="justify-self-start">
							{{ SEVERITY_LABELS[check.severity] }}
						</n-tag>
						<span class="flex min-w-0 flex-col">
							<span class="text-default truncate text-sm" :title="check.title"><bdi>{{ check.title || check.check_id }}</bdi></span>
							<span class="text-tertiary truncate font-mono text-xs">{{ check.check_id }}</span>
						</span>
						<span class="text-secondary hidden truncate font-mono text-xs md:block">{{ check.service || "—" }}</span>
						<span class="col-span-2 flex items-center gap-2 md:col-span-1 md:justify-end">
							<n-tag :type="CHECK_STATUS_TAGS[check.status]" size="tiny" round :bordered="false">
								{{ CHECK_STATUS_LABELS[check.status] }}
							</n-tag>
							<span class="text-tertiary text-xs tabular-nums" :title="countsTitle(check)">
								{{ check.failed }} failing · {{ check.passed }} passing
							</span>
						</span>
					</button>
					<!--
						Prowler's own words for the check, from its check metadata (Markdown since 5.x): rendered
						without raw HTML or images. The references are links only for http(s) addresses.
					-->
					<div
						v-if="expanded === check.check_id"
						class="bg-secondary/40 border-default flex flex-col gap-3 border-t px-4 py-3 text-sm"
						data-testid="cloud-check-detail"
					>
						<Markdown v-if="check.description" :source="check.description" no-images class="cloud-check-text" />
						<div v-if="check.risk" class="flex flex-col gap-1">
							<span :class="SECTION_LABEL">Risk</span>
							<Markdown :source="check.risk" no-images class="cloud-check-text" />
						</div>
						<div v-if="check.remediation" class="flex flex-col gap-1">
							<span :class="SECTION_LABEL">Remediation</span>
							<Markdown :source="check.remediation" no-images class="cloud-check-text" />
						</div>
						<div v-if="links(check).length" class="flex flex-col gap-1">
							<span :class="SECTION_LABEL">References</span>
							<ul class="m-0 flex list-none flex-col gap-0.5 p-0">
								<li v-for="url of links(check)" :key="url" class="truncate">
									<a :href="url" target="_blank" rel="noopener noreferrer" class="text-xs">{{ url }}</a>
								</li>
							</ul>
						</div>
						<div v-if="Object.keys(check.compliance).length" class="flex flex-col gap-1">
							<span :class="SECTION_LABEL">Compliance</span>
							<div class="flex flex-wrap gap-1">
								<n-tag v-for="(ids, framework) of check.compliance" :key="framework" size="tiny" :bordered="false" :title="ids.join(', ')">
									{{ framework }} · {{ ids.length }}
								</n-tag>
							</div>
						</div>
						<div class="flex flex-wrap items-center gap-3 text-xs">
							<span class="text-secondary">
								{{ check.failed }} failing · {{ check.passed }} passing · {{ check.manual }} manual · {{ check.muted }} muted
							</span>
							<n-button
								v-if="findingsAvailable && check.failed + check.manual > 0"
								size="tiny"
								secondary
								@click="emit('viewFindings', check.check_id)"
							>
								Its findings
							</n-button>
						</div>
					</div>
				</div>
			</div>
			<div v-if="total > PAGE_SIZE" class="border-default flex justify-end border-t px-4 py-2">
				<n-pagination v-model:page="page" :page-size="PAGE_SIZE" :item-count="total" />
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { CloudCheck, CloudChecksQuery, CloudSeverity } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { refDebounced } from "@vueuse/core"
import { NAlert, NButton, NEmpty, NInput, NPagination, NSelect, NSkeleton, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { getApiErrorMessage } from "@/utils"
import { CHECK_STATUS_LABELS, CHECK_STATUS_TAGS, safeLink, SEVERITIES, SEVERITY_LABELS, SEVERITY_TAGS } from "./utils"

const { customerCode, scanId, findingsAvailable = true } = defineProps<{
	customerCode: string
	scanId: number
	findingsAvailable?: boolean
}>()
const emit = defineEmits<{ (e: "viewFindings", checkId: string): void }>()

const PAGE_SIZE = 50
const SearchIcon = "carbon:search"
const STATUS_OPTIONS = [
	{ label: "Failing", value: "fail" },
	{ label: "Manual review", value: "manual" },
	{ label: "Passing", value: "pass" }
]
const severityOptions = SEVERITIES.map(value => ({ label: SEVERITY_LABELS[value], value }))

const status = ref<"fail" | "manual" | "pass" | null>("fail")
const severity = ref<CloudSeverity[]>([])
const service = ref<string | null>(null)
const query = ref("")
const debouncedQuery = refDebounced(query, 300)
const page = ref(1)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const checks = ref<CloudCheck[]>([])
const services = ref<string[]>([])
const total = ref(0)
const expanded = ref<string | null>(null)
let controller: AbortController | null = null

const errorText = computed(() => (error.value ? getApiErrorMessage(error.value) || "The checks couldn't be read." : ""))
const serviceOptions = computed(() => services.value.map(value => ({ label: value, value })))

function links(check: CloudCheck): string[] {
	return [...new Set([...check.remediation_urls, ...check.additional_urls].map(safeLink).filter((url): url is string => !!url))]
}

function countsTitle(check: CloudCheck): string {
	return `${check.failed} failing, ${check.passed} passing, ${check.manual} manual, ${check.muted} muted`
}

function params(): CloudChecksQuery {
	return {
		status: status.value ?? undefined,
		severity: severity.value.length ? severity.value : undefined,
		service: service.value ?? undefined,
		q: debouncedQuery.value.trim() || undefined,
		page: page.value,
		page_size: PAGE_SIZE
	}
}

function load() {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	error.value = null
	Api.cloudAssessment
		.getChecks(customerCode, scanId, params(), current.signal)
		.then(res => {
			checks.value = res.data.checks
			services.value = res.data.services
			total.value = res.data.total
		})
		.catch((err: ApiError) => {
			if (!current.signal.aborted) error.value = err
		})
		.finally(() => {
			if (controller === current) loading.value = false
		})
}

watch([status, severity, service, debouncedQuery], () => {
	expanded.value = null
	if (page.value !== 1) page.value = 1
	else load()
})
watch(page, () => {
	expanded.value = null
	load()
})

load()
</script>

<style scoped>
/* Prowler's paragraphs sit close together here, not at the Markdown view's report spacing. */
.cloud-check-text :deep(.markdown-style > *) {
	margin-bottom: 0.5rem;
}
.cloud-check-text :deep(.markdown-style > *:last-child) {
	margin-bottom: 0;
}
</style>
