<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show">
			<div class="flex flex-col gap-6 p-7 pt-2">
				<div class="grid-auto-fit-200 grid gap-2">
					<CardKV>
						<template #key>Policy ID</template>
						<template #value>
							{{ sca.policy_id }}
						</template>
					</CardKV>

					<CardKV>
						<template #key>Agent</template>
						<template #value>
							{{ sca.agent_name }}
						</template>
					</CardKV>

					<CardKV v-if="sca.customer_code">
						<template #key>Customer</template>
						<template #value>
							<code
								class="text-primary cursor-pointer"
								@click.stop="gotoCustomer({ code: sca.customer_code })"
							>
								#{{ sca.customer_code }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
					</CardKV>

					<CardKV>
						<template #key>Compliance Level</template>
						<template #value>
							{{ getComplianceLevel(sca.score) }}
						</template>
					</CardKV>

					<CardKV>
						<template #key>Score</template>
						<template #value>{{ sca.score }}%</template>
					</CardKV>

					<CardKV>
						<template #key>Scan Date</template>
						<template #value>
							{{ formatDate(sca.end_scan, dFormats.datetime) }}
						</template>
					</CardKV>
				</div>

				<CardKV>
					<template #key>Description</template>
					<template #value>
						{{ sca.description }}
					</template>
				</CardKV>

				<CardKV v-if="sca.references">
					<template #key>References</template>
					<template #value>
						<a :href="sca.references" target="_blank" tabindex="-1" class="outline-none">
							{{ sca.references }}
						</a>
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Statistics & Progress" tab="Statistics & Progress" display-directive="show">
			<div class="flex flex-col gap-4 p-7 pt-2">
				<div class="flex items-center gap-2 text-sm">
					<Icon :name="InfoIcon" :size="14" />
					Total:
					<code>{{ sca.total_checks }}</code>
				</div>

				<div class="grid-auto-fit-200 grid gap-2">
					<n-card content-class="flex flex-col gap-2" size="small">
						<div class="flex items-center justify-between gap-2 whitespace-nowrap">
							<div class="flex items-center gap-2">
								<Icon :name="PassIcon" :size="20" class="text-success" />
								<span class="text-lg">Passed</span>
							</div>
							<div class="font-mono text-lg font-bold">{{ sca.pass }}</div>
						</div>
						<n-progress
							type="line"
							indicator-placement="inside"
							:percentage="getPercentage(sca.pass)"
							color="var(--success-color)"
							class="custom-progress"
						/>
					</n-card>

					<n-card content-class="flex flex-col gap-2" size="small">
						<div class="flex items-center justify-between gap-2 whitespace-nowrap">
							<div class="flex items-center gap-2">
								<Icon :name="FailIcon" :size="20" class="text-error" />
								<span class="text-lg">Failed</span>
							</div>
							<div class="font-mono text-lg font-bold">{{ sca.fail }}</div>
						</div>
						<n-progress
							type="line"
							indicator-placement="inside"
							:percentage="getPercentage(sca.fail)"
							color="var(--error-color)"
							class="custom-progress"
						/>
					</n-card>

					<n-card v-if="sca.invalid > 0" content-class="flex flex-col gap-2" size="small">
						<div class="flex items-center justify-between gap-2 whitespace-nowrap">
							<div class="flex items-center gap-2">
								<Icon :name="InvalidIcon" :size="20" class="text-warning" />
								<span class="text-lg">Invalid</span>
							</div>
							<div class="font-mono text-lg font-bold">{{ sca.invalid }}</div>
						</div>
						<n-progress
							type="line"
							indicator-placement="inside"
							:percentage="getPercentage(sca.invalid)"
							color="var(--warning-color)"
							class="custom-progress"
						/>
					</n-card>
				</div>

				<n-card class="bg-secondary! overflow-hidden" title="Progress">
					<n-progress
						type="line"
						indicator-placement="inside"
						:percentage="sca.score"
						color="var(--success-color)"
						class="custom-progress"
					/>
				</n-card>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Scan Information" tab="Scan Information" display-directive="show">
			<div class="flex flex-col gap-4 p-7 pt-2">
				<n-card class="bg-secondary! overflow-hidden">
					<div class="flex flex-wrap justify-between gap-8">
						<n-statistic
							label="Scan Started"
							:value="`${formatDate(sca.start_scan, dFormats.datetime)}`"
							tabular-nums
						/>
						<n-statistic
							label="Scan Completed"
							:value="`${formatDate(sca.end_scan, dFormats.datetime)}`"
							tabular-nums
						/>
						<n-statistic label="Scan Duration" :value="`${getScanDuration()}`" tabular-nums />
					</div>
				</n-card>

				<CardKV v-if="sca.hash_file">
					<template #key>Hash File</template>
					<template #value>
						{{ sca.hash_file }}
					</template>
				</CardKV>
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { AgentScaOverviewItem } from "@/types/sca.d"
import _toNumber from "lodash/toNumber"
import { NCard, NProgress, NStatistic, NTabPane, NTabs } from "naive-ui"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { getComplianceLevel } from "./utils"

const { sca } = defineProps<{ sca: AgentScaOverviewItem }>()

const dFormats = useSettingsStore().dateFormat
const { gotoCustomer } = useGoto()

const InfoIcon = "carbon:information"
const LinkIcon = "carbon:launch"
const PassIcon = "carbon:checkmark-filled"
const FailIcon = "carbon:close-filled"
const InvalidIcon = "carbon:warning-alt"

function getPercentage(count: number): number {
	if (sca.total_checks === 0) return 0
	return _toNumber(((count / sca.total_checks) * 100).toFixed(1))
}

function getScanDuration(): string {
	const start = new Date(sca.start_scan)
	const end = new Date(sca.end_scan)
	const durationMs = end.getTime() - start.getTime()
	const durationMinutes = Math.floor(durationMs / 60000)
	const durationSeconds = Math.floor((durationMs % 60000) / 1000)

	if (durationMinutes > 0) {
		return `${durationMinutes}m ${durationSeconds}s`
	}
	return `${durationSeconds}s`
}
</script>

<style lang="scss" scoped>
.custom-progress {
	:deep() {
		.n-progress-graph-line-indicator {
			text-shadow:
				0px 0px 1px black,
				0px 0px 2px black,
				0px 0px 3px black;
			font-weight: bold;
			color: white !important;
		}
	}
}
</style>
