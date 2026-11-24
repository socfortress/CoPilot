<template>
	<div class="flex flex-col gap-3 pt-2" data-testid="cloud-compliance">
		<n-alert v-if="error" type="error" :bordered="false">{{ errorText }}</n-alert>
		<n-alert v-else-if="!catalogAvailable && !loading" type="info" :bordered="false" data-testid="cloud-compliance-no-catalog">
			copilot-prowler couldn't be asked for Prowler's framework catalog: the figures cover only the requirements this
			scan's checks map to, without their names.
		</n-alert>

		<!-- One framework: its requirements, each with the checks behind it. -->
		<template v-if="framework">
			<div class="flex flex-wrap items-center gap-3">
				<n-button text size="small" @click="emit('close')">
					<template #icon><Icon :name="BackIcon" /></template>
					All frameworks
				</n-button>
				<h4 class="m-0 text-base font-semibold">{{ detail?.framework.name ?? framework }}</h4>
			</div>
			<n-spin :show="loading">
				<template v-if="detail">
					<p v-if="detail.framework.description" class="text-secondary m-0 max-w-4xl text-sm whitespace-pre-wrap">
						{{ detail.framework.description }}
					</p>
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<n-select
							v-model:value="statusFilter"
							:options="requirementStatusOptions"
							clearable
							placeholder="Every status"
							class="w-48!"
							aria-label="Requirement status"
						/>
						<n-input v-model:value="query" clearable placeholder="Search requirements" class="w-64!" aria-label="Search requirements">
							<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
						</n-input>
						<span class="text-secondary ml-auto text-xs">{{ shownRequirements.length }} of {{ detail.requirements.length }}</span>
					</div>
					<section class="border-default bg-default mt-3 overflow-hidden rounded-lg border">
						<n-empty v-if="!shownRequirements.length" description="No requirement matches" class="py-8" />
						<div v-else class="divide-border flex flex-col divide-y">
							<div
								v-for="requirement of shownRequirements"
								:key="requirement.id"
								class="grid grid-cols-1 gap-2 px-4 py-3 md:grid-cols-[8rem_minmax(0,1fr)]"
								:data-testid="`cloud-requirement-${requirement.id}`"
							>
								<div class="flex flex-col items-start gap-1">
									<n-tag :type="REQUIREMENT_STATUS_TAGS[requirement.status]" size="small" round :bordered="false">
										{{ REQUIREMENT_STATUS_LABELS[requirement.status] }}
									</n-tag>
									<span class="text-tertiary font-mono text-xs break-all">{{ requirement.id }}</span>
								</div>
								<div class="flex min-w-0 flex-col gap-1.5">
									<span class="text-default text-sm">{{ requirement.name ?? requirement.description ?? requirement.id }}</span>
									<span v-if="requirement.name && requirement.description" class="text-secondary text-xs">
										{{ requirement.description }}
									</span>
									<span v-if="requirement.section" class="text-tertiary text-xs">{{ requirement.section }}</span>
									<div v-if="requirement.checks.length" class="flex flex-wrap gap-1">
										<n-tag
											v-for="check of requirement.checks"
											:key="check.check_id"
											size="tiny"
											:type="check.failed ? 'error' : 'default'"
											:bordered="!check.ran"
											:title="check.ran ? `${check.failed} failing, ${check.passed} passing, ${check.manual} manual` : 'This scan has no result for this check'"
										>
											<span class="font-mono">{{ check.check_id }}</span>
											<span class="ml-1 opacity-80">{{ checkOutcome(check) }}</span>
										</n-tag>
									</div>
									<span v-else class="text-tertiary text-xs">No automated check: review it by hand.</span>
								</div>
							</div>
						</div>
					</section>
				</template>
			</n-spin>
		</template>

		<!-- Every framework the scan's checks cover. -->
		<template v-else>
			<div class="flex flex-wrap items-center gap-2">
				<n-input v-model:value="query" clearable placeholder="Search frameworks" class="w-64!" aria-label="Search frameworks">
					<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
				</n-input>
			</div>
			<n-spin :show="loading">
				<section class="border-default bg-default overflow-hidden rounded-lg border">
					<n-empty v-if="!shownFrameworks.length && !loading" description="No framework matches" class="py-8" />
					<div v-else class="divide-border flex flex-col divide-y">
						<button
							v-for="item of shownFrameworks"
							:key="item.key"
							type="button"
							class="hover:bg-secondary/50 grid w-full grid-cols-1 items-center gap-x-4 gap-y-2 px-4 py-3 text-left transition-colors md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]"
							:data-testid="`cloud-framework-${item.key}`"
							@click="emit('open', item.key)"
						>
							<span class="flex min-w-0 flex-col">
								<span class="text-default truncate text-sm font-medium" :title="item.name ?? item.key">{{ item.name ?? item.key }}</span>
								<span class="text-tertiary truncate font-mono text-xs">{{ item.key }}</span>
							</span>
							<span class="flex flex-col gap-1.5">
								<!-- A requirement's status, each share labelled below: never colour alone. -->
								<span class="bg-secondary flex h-1.5 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
									<span
										v-for="part of parts(item)"
										:key="part.status"
										class="h-full first:rounded-l-full last:rounded-r-full"
										:class="part.fill"
										:style="{ width: `${part.percent}%` }"
									/>
								</span>
								<span class="text-secondary flex flex-wrap gap-x-3 text-xs tabular-nums">
									<span>{{ item.passed }} passing</span>
									<span :class="item.failed ? 'text-error' : ''">{{ item.failed }} failing</span>
									<span>{{ item.manual }} manual</span>
									<span class="text-tertiary">{{ item.not_assessed }} not assessed</span>
								</span>
							</span>
						</button>
					</div>
				</section>
			</n-spin>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { CloudComplianceFramework, CloudRequirement, CloudRequirementStatus } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { NAlert, NButton, NEmpty, NInput, NSelect, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { frameworkOrder, naturalCompare, REQUIREMENT_STATUS_LABELS, REQUIREMENT_STATUS_TAGS } from "./utils"

const { customerCode, scanId, framework = null } = defineProps<{
	customerCode: string
	scanId: number
	framework?: string | null
}>()
const emit = defineEmits<{ (e: "open", key: string): void; (e: "close"): void }>()

const BackIcon = "carbon:arrow-left"
const SearchIcon = "carbon:search"
const STATUS_FILLS: Record<CloudRequirementStatus, string> = {
	pass: "bg-success",
	fail: "bg-error",
	manual: "bg-warning",
	not_assessed: "bg-border"
}
const requirementStatusOptions = (Object.keys(REQUIREMENT_STATUS_LABELS) as CloudRequirementStatus[]).map(value => ({
	label: REQUIREMENT_STATUS_LABELS[value],
	value
}))

const loading = ref(false)
const error = ref<ApiError | null>(null)
const catalogAvailable = ref(true)
const frameworks = ref<CloudComplianceFramework[]>([])
const detail = ref<{ framework: CloudComplianceFramework; requirements: CloudRequirement[] } | null>(null)
const query = ref("")
const statusFilter = ref<CloudRequirementStatus | null>(null)

const errorText = computed(() => (error.value ? getApiErrorMessage(error.value) || "The compliance view couldn't be read." : ""))

const shownFrameworks = computed(() => {
	const needle = query.value.trim().toLocaleLowerCase()
	return frameworks.value
		.filter(item => !needle || `${item.name ?? ""} ${item.key}`.toLocaleLowerCase().includes(needle))
		.sort(frameworkOrder)
})

// Requirements in reading order, 1.2 before 1.10 (Prowler's files list some by text: 1.1, 1.10, 1.11, …).
const orderedRequirements = computed(() => [...(detail.value?.requirements ?? [])].sort((a, b) => naturalCompare(a.id, b.id)))

const shownRequirements = computed(() => {
	const needle = query.value.trim().toLocaleLowerCase()
	return orderedRequirements.value.filter(
		requirement =>
			(!statusFilter.value || requirement.status === statusFilter.value) &&
			(!needle ||
				`${requirement.id} ${requirement.name ?? ""} ${requirement.description ?? ""} ${requirement.section ?? ""}`
					.toLocaleLowerCase()
					.includes(needle))
	)
})

/** What a requirement's check found, in a word or two. */
function checkOutcome(check: CloudRequirement["checks"][number]): string {
	if (!check.ran) return "not run"
	if (check.failed) return `${check.failed} failing`
	if (check.manual) return "manual review"
	return check.passed ? "passing" : "nothing to check"
}

function parts(item: CloudComplianceFramework) {
	const total = item.requirements_total || 1
	return (["pass", "fail", "manual", "not_assessed"] as CloudRequirementStatus[])
		.map(status => {
			const count = status === "pass" ? item.passed : status === "fail" ? item.failed : status === "manual" ? item.manual : item.not_assessed
			return { status, fill: STATUS_FILLS[status], percent: (count / total) * 100 }
		})
		.filter(part => part.percent > 0)
}

function loadFrameworks() {
	loading.value = true
	error.value = null
	Api.cloudAssessment
		.getCompliance(customerCode, scanId)
		.then(res => {
			frameworks.value = res.data.frameworks
			catalogAvailable.value = res.data.catalog_available
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function loadDetail(key: string) {
	loading.value = true
	error.value = null
	detail.value = null
	Api.cloudAssessment
		.getComplianceFramework(customerCode, scanId, key)
		.then(res => {
			detail.value = { framework: res.data.framework, requirements: res.data.requirements }
			catalogAvailable.value = res.data.catalog_available
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	() => framework,
	key => {
		query.value = ""
		statusFilter.value = null
		if (key) loadDetail(key)
		else loadFrameworks()
	},
	{ immediate: true }
)
</script>
