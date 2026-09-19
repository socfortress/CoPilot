<template>
	<!--
		A one-line readout, not a dashboard: these numbers are orientation ("which
		platform, how much is in it"), and the tabs beside them are the work.
	-->
	<div v-if="error" class="text-warning flex items-center gap-1.5 text-xs" :title="error">
		<Icon name="carbon:warning-alt" :size="14" />
		<span>OpenCTI unreachable</span>
	</div>
	<dl
		v-else
		class="divide-border/40 -mx-1 flex flex-wrap items-center divide-x text-xs"
		:class="{ 'animate-pulse': loading }"
	>
		<div v-for="stat of stats" :key="stat.label" class="flex items-baseline gap-1.5 px-2" :title="stat.title">
			<dt class="text-tertiary whitespace-nowrap">{{ stat.label }}</dt>
			<dd class="text-default font-mono tabular-nums" :class="stat.valueClass">{{ stat.value }}</dd>
		</div>
	</dl>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { OpenCTIAbout } from "@/types/opencti"
import { computed, onBeforeMount, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
// TEMP(mock): UI/UX review — restore `import Api from "@/api"` and `Api.opencti` before merging.
import { getApiErrorMessage } from "@/utils"
import mockOpenCTI from "./__mock__/opencti-mock"

// Scores at or above this are what most feeds assign to confirmed-malicious IOCs.
const HIGH_SCORE = 75

const about = ref<OpenCTIAbout | null>(null)
const indicatorCount = ref<number | null>(null)
const highScoreCount = ref<number | null>(null)
const loading = ref(false)
const error = ref("")

function formatCount(value: number | null): string {
	return value === null ? "—" : value.toLocaleString()
}

const stats = computed(() => [
	{
		label: "OpenCTI",
		value: about.value?.version ? `v${about.value.version}` : "—",
		title: "Platform version",
		valueClass: ""
	},
	{
		label: "Account",
		value: about.value?.user_name || "—",
		title: about.value?.user_email
			? `Connector token's user (${about.value.user_email})`
			: "Connector token's user",
		valueClass: ""
	},
	{
		label: "Indicators",
		value: formatCount(indicatorCount.value),
		title: "Indicators visible to the connector",
		valueClass: ""
	},
	{
		label: `Score ≥${HIGH_SCORE}`,
		value: formatCount(highScoreCount.value),
		title: `Indicators scored ${HIGH_SCORE} or higher`,
		valueClass: highScoreCount.value ? "text-error" : ""
	}
])

function load() {
	loading.value = true
	error.value = ""

	// Counts come from `global_count` on a one-row page: OpenCTI totals the
	// whole match set server-side, so this costs two tiny queries, not a scan.
	Promise.all([
		mockOpenCTI.getAbout(),
		mockOpenCTI.getIndicators({ first: 1 }),
		mockOpenCTI.getIndicators({ first: 1, min_score: HIGH_SCORE })
	])
		.then(([aboutRes, allRes, highRes]) => {
			about.value = aboutRes.data.about
			indicatorCount.value = allRes.data.page_info.global_count
			highScoreCount.value = highRes.data.page_info.global_count
		})
		.catch(err => {
			error.value = getApiErrorMessage(err as ApiError) || "Could not reach OpenCTI."
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>
