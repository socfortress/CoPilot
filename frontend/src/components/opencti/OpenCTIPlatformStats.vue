<template>
	<div class="@container">
		<div v-if="error" class="bg-secondary border-error rounded-lg border px-4 py-2.5">{{ error }}</div>
		<n-spin v-else :show="loading">
			<div class="grid grid-cols-1 gap-4 @md:grid-cols-2 @4xl:grid-cols-4">
				<CardLink
					v-for="tile of tiles"
					:key="tile.label"
					:title="tile.label"
					:value="tile.value"
					:icon="tile.icon"
					:subtitle="tile.sub"
				/>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { OpenCTIAbout } from "@/types/opencti"
import { NSpin } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import { getApiErrorMessage } from "@/utils"
// TEMP(mock): UI/UX review — restore `import Api from "@/api"` and `Api.opencti` before merging.
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

const tiles = computed(() => [
	{
		label: "Platform",
		value: about.value?.version || "—",
		sub: "OpenCTI version",
		icon: "carbon:cloud-service-management"
	},
	{
		label: "Account",
		value: about.value?.user_name || "—",
		sub: "Connector token's user",
		icon: "carbon:user-certification"
	},
	{
		label: "Indicators",
		value: formatCount(indicatorCount.value),
		sub: "Visible to the connector",
		icon: "carbon:radar"
	},
	{
		label: "High score",
		value: formatCount(highScoreCount.value),
		sub: `Indicators scored ${HIGH_SCORE}+`,
		icon: "carbon:warning-alt"
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
