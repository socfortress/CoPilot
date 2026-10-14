<template>
	<div class="flex flex-col gap-3" data-testid="agent-sca">
		<n-alert v-if="error" type="error" :bordered="false" data-testid="sca-error">{{ error }}</n-alert>

		<!-- The policies: worst score first, each opening its checks. -->
		<section
			v-else-if="!policy"
			class="border-default bg-default @container overflow-hidden rounded-lg border"
			:aria-busy="loading"
			data-testid="sca-policies"
		>
			<div class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 @3xl:grid" :class="POLICY_COLUMNS">
				<span :class="HEAD">Policy</span>
				<span :class="HEAD">Score</span>
				<span :class="HEAD">Checks</span>
				<span :class="HEAD">Last scan</span>
				<span />
			</div>
			<div v-if="loading" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 3" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!policies.length"
				description="No SCA scan on this agent yet"
				class="min-h-40 justify-center"
				data-testid="sca-empty"
			/>
			<div v-else class="divide-border flex flex-col divide-y">
				<button
					v-for="p of policies"
					:key="p.policy_id"
					type="button"
					class="group hover:bg-secondary/50 grid w-full cursor-pointer items-center gap-x-3 gap-y-2 px-4 py-2.5 text-left transition-colors @3xl:gap-x-4"
					:class="POLICY_ROW"
					data-testid="sca-policy-row"
					@click="openPolicy(p)"
				>
					<span class="flex min-w-0 flex-col leading-tight [grid-area:name]">
						<span class="text-default truncate text-sm">{{ p.name || p.policy_id }}</span>
						<span class="text-tertiary truncate font-mono text-xs">{{ p.policy_id }}</span>
					</span>
					<span class="flex min-w-0 items-center gap-3 [grid-area:score]">
						<span class="text-default w-10 shrink-0 font-mono text-sm font-semibold tabular-nums">{{ p.score }}%</span>
						<span class="bg-secondary h-1 min-w-0 grow overflow-hidden rounded-full">
							<span
								class="block h-full rounded-full"
								:class="SCORE_COLORS[scoreLevel(p.score)]"
								:style="{ width: `${Math.max(2, p.score)}%` }"
							/>
						</span>
					</span>
					<span class="flex flex-wrap items-baseline gap-x-2 font-mono text-xs tabular-nums [grid-area:checks]">
						<span class="text-success">{{ p.pass }} passed</span>
						<span class="text-error">{{ p.fail }} failed</span>
						<span v-if="p.invalid" class="text-tertiary">{{ p.invalid }} n/a</span>
					</span>
					<span class="text-secondary hidden text-xs whitespace-nowrap [grid-area:scan] @3xl:block">
						{{ p.end_scan ? relative(p.end_scan) : "—" }}
					</span>
					<Icon
						name="carbon:chevron-right"
						:size="14"
						class="text-tertiary group-hover:text-default justify-self-end [grid-area:chev]"
					/>
				</button>
			</div>
		</section>

		<!-- One policy's checks: failed first, filtered by result and searched by title or id. -->
		<template v-else>
			<div class="flex flex-wrap items-center gap-2">
				<n-button size="small" quaternary data-testid="sca-back" @click="closePolicy()">
					<template #icon><Icon name="carbon:arrow-left" /></template>
					All policies
				</n-button>
				<span class="flex min-w-0 items-baseline gap-2">
					<span class="text-default truncate text-sm font-medium" data-testid="sca-policy-name">
						{{ policy.name || policy.policy_id }}
					</span>
					<span class="text-tertiary font-mono text-xs tabular-nums">{{ policy.score }}%</span>
				</span>
				<n-button
					size="small"
					secondary
					class="ml-auto!"
					:loading="exporting"
					:disabled="!checks.length"
					data-testid="sca-export"
					@click="exportCsv()"
				>
					<template #icon><Icon name="carbon:download" /></template>
					Export CSV
				</n-button>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<n-radio-group v-model:value="result" size="small" data-testid="sca-result">
					<n-radio-button v-for="option of RESULT_OPTIONS" :key="option.value" :value="option.value">
						{{ option.label }}
						<span class="text-tertiary ml-1 font-mono text-xs tabular-nums">{{ counts[option.value] }}</span>
					</n-radio-button>
				</n-radio-group>
				<n-input
					v-model:value="search"
					size="small"
					clearable
					placeholder="Search check title or id"
					class="w-64!"
					data-testid="sca-search"
				>
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
			</div>

			<n-alert v-if="checksError" type="error" :bordered="false">{{ checksError }}</n-alert>
			<section
				v-else
				class="border-default bg-default @container overflow-hidden rounded-lg border"
				:aria-busy="loadingChecks"
				data-testid="sca-checks"
			>
				<div v-if="loadingChecks" class="flex flex-col gap-2 p-3">
					<n-skeleton v-for="n of 5" :key="n" :height="40" :sharp="false" class="rounded-md" />
				</div>
				<n-empty
					v-else-if="!shownChecks.length"
					:description="checks.length ? 'No check matches the filters' : 'This policy has no checks'"
					class="min-h-40 justify-center"
				/>
				<div v-else class="divide-border flex flex-col divide-y">
					<div
						v-for="c of pageChecks"
						:key="c.id"
						:class="{ 'pb-4': expanded.has(c.id) }"
						data-testid="sca-check-row"
					>
						<button
							type="button"
							class="group hover:bg-secondary/50 grid w-full cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2.5 text-left transition-colors @3xl:grid-cols-[7.5rem_4.5rem_minmax(0,1fr)_1rem] @3xl:gap-x-4"
							:class="{ 'bg-secondary/50': expanded.has(c.id) }"
							:aria-expanded="expanded.has(c.id)"
							@click="toggle(c.id)"
						>
							<span><span :class="[CHIP, scaResultClasses(c.result)]">{{ c.result }}</span></span>
							<span class="text-tertiary hidden font-mono text-xs tabular-nums @3xl:block">#{{ c.id }}</span>
							<span class="text-default min-w-0 truncate text-sm">{{ c.title }}</span>
							<Icon
								name="carbon:chevron-down"
								:size="14"
								class="text-tertiary group-hover:text-default justify-self-end transition-transform duration-200"
								:class="{ 'rotate-180': expanded.has(c.id) }"
							/>
						</button>
						<div
							v-if="expanded.has(c.id)"
							class="bg-secondary/30 border-default flex flex-col gap-4 border-y px-4 pt-4 pb-5"
							data-testid="sca-check-detail"
						>
							<div v-for="part of checkText(c)" :key="part.label" class="flex flex-col gap-1">
								<span :class="HEAD" class="text-tertiary">{{ part.label }}</span>
								<p class="text-default m-0 text-sm whitespace-pre-line">{{ part.value }}</p>
							</div>
							<div v-if="c.compliance.length" class="flex flex-col gap-1.5">
								<span :class="HEAD" class="text-tertiary">Compliance</span>
								<div class="flex flex-wrap gap-1.5">
									<span
										v-for="item of c.compliance"
										:key="`${item.key}-${item.value}`"
										class="border-default text-secondary rounded border px-1.5 py-0.5 font-mono text-xs"
									>
										{{ item.key }} {{ item.value }}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>
				<footer
					v-if="shownChecks.length > PAGE_SIZES[0]"
					class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
				>
					<span class="text-tertiary font-mono text-xs tabular-nums">{{ rangeLabel }}</span>
					<n-pagination
						v-model:page="pageNumber"
						v-model:page-size="pageSize"
						:item-count="shownChecks.length"
						:page-sizes="PAGE_SIZES"
						:page-slot="6"
						show-size-picker
						size="small"
					/>
				</footer>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ScaResultFilter } from "./agentFindings"
import type { AgentScaCheck, AgentScaPolicy } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NAlert, NButton, NEmpty, NInput, NPagination, NRadioButton, NRadioGroup, NSkeleton, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import {
	exportFilename,
	filterScaChecks,
	scaResultClasses,
	scaResultCounts,
	SCORE_COLORS,
	scoreLevel,
	sortScaPolicies
} from "./agentFindings"

/**
 * An agent's SCA (#1256): its policies, worst score first, and one policy's checks — the
 * failing ones first, with what to do about them — plus that policy's CSV export.
 */

const { agentId, agentLabel } = defineProps<{ agentId: string; agentLabel: string }>()

const PAGE_SIZES = [25, 50, 100]
const HEAD = "text-xxs font-medium tracking-[0.12em] uppercase"
const CHIP = "inline-flex rounded border px-1.5 py-0.5 text-xxs font-medium tracking-wide uppercase whitespace-nowrap"
const POLICY_COLUMNS = "grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_7rem_1rem]"
const POLICY_ROW = [
	"grid-cols-[minmax(0,1fr)_auto]",
	"[grid-template-areas:'name_chev'_'score_score'_'checks_checks']",
	"@3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_7rem_1rem]",
	"@3xl:[grid-template-areas:'name_score_checks_scan_chev']"
].join(" ")
const RESULT_OPTIONS: { label: string; value: ScaResultFilter }[] = [
	{ label: "All", value: "all" },
	{ label: "Failed", value: "failed" },
	{ label: "Passed", value: "passed" },
	{ label: "N/A", value: "not applicable" }
]

const message = useMessage()
const { loading, run } = useLatestRequest()
const { loading: loadingChecks, run: runChecks } = useLatestRequest()
const policies = ref<AgentScaPolicy[]>([])
const error = ref<string | null>(null)
const policy = ref<AgentScaPolicy | null>(null)
const checks = ref<AgentScaCheck[]>([])
const checksError = ref<string | null>(null)
const result = ref<ScaResultFilter>("all")
const search = ref("")
const pageNumber = ref(1)
const pageSize = ref(PAGE_SIZES[0])
const expanded = ref(new Set<number>())
const exporting = ref(false)

const counts = computed(() => scaResultCounts(checks.value))
const shownChecks = computed(() => filterScaChecks(checks.value, { result: result.value, search: search.value }))
const offset = computed(() => (pageNumber.value - 1) * pageSize.value)
const pageChecks = computed(() => shownChecks.value.slice(offset.value, offset.value + pageSize.value))
const rangeLabel = computed(
	() =>
		`${(offset.value + 1).toLocaleString()}–${Math.min(offset.value + pageSize.value, shownChecks.value.length).toLocaleString()} of ${shownChecks.value.length.toLocaleString()}`
)

const relative = (ts: string) => dayjs(ts).fromNow()

/** What a check says, in reading order; the placeholders Wazuh fills absent fields with are left out. */
function checkText(check: AgentScaCheck) {
	const placeholder = /not found$/i
	return [
		{ label: "Description", value: check.description },
		{ label: "Rationale", value: check.rationale },
		{ label: "Remediation", value: check.remediation },
		{ label: "Reason", value: check.reason }
	].filter((part): part is { label: string; value: string } => !!part.value && !placeholder.test(part.value))
}

function toggle(id: number) {
	const next = new Set(expanded.value)
	if (next.has(id)) next.delete(id)
	else next.add(id)
	expanded.value = next
}

function loadPolicies() {
	error.value = null
	return run(
		async signal => {
			policies.value = sortScaPolicies((await Api.agents.getScaPolicies(agentId, signal)).data.sca ?? [])
		},
		err => {
			error.value = getApiErrorMessage(err as ApiError) || "Could not load the SCA policies."
		}
	)
}

function openPolicy(selected: AgentScaPolicy) {
	policy.value = selected
	checks.value = []
	checksError.value = null
	result.value = "all"
	search.value = ""
	runChecks(
		async signal => {
			checks.value = (await Api.agents.getScaChecks(agentId, selected.policy_id, signal)).data.sca_policy_results ?? []
		},
		err => {
			checksError.value = getApiErrorMessage(err as ApiError) || "Could not load the policy's checks."
		}
	)
}

function closePolicy() {
	policy.value = null
	checks.value = []
}

async function exportCsv() {
	if (!policy.value) return
	exporting.value = true
	try {
		const response = await Api.agents.exportScaChecks(agentId, policy.value.policy_id)
		saveAs(response.data, exportFilename(`sca-${policy.value.policy_id}`, agentLabel))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not export the policy's checks.")
	} finally {
		exporting.value = false
	}
}

watch([result, search, pageSize], () => {
	pageNumber.value = 1
	expanded.value = new Set()
})

onBeforeMount(loadPolicies)
</script>
