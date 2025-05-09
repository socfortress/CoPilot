<template>
	<SegmentedPage>
		<template #sidebar-header>[de]select all</template>
		<template #sidebar-content>tactics list...</template>
		<template #main-toolbar>search...</template>
		<template #main-content>
			<n-spin :show="loading">
				<div class="flex flex-col gap-3">
					<div v-for="alert of list" :key="alert.technique_id">
						<pre>{{ alert }}</pre>
					</div>
				</div>
			</n-spin>
		</template>
	</SegmentedPage>
</template>

<script setup lang="ts">
import type { MitreTechniquesAlertsQuery, MitreTechniquesAlertsQueryTimeRange } from "@/api/endpoints/mitre"
import type { MitreTechnique } from "@/types/mitre.d"
import Api from "@/api"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NSpin, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import { techniques } from "./mock"

const props = defineProps<{
	filters?: { type: string; value: string }[]
}>()

const { filters } = toRefs(props)
const loading = ref(false)
const message = useMessage()
const list = ref<MitreTechnique[]>(techniques)
const currentPage = ref(1)
let abortController: AbortController | null = null

function resetList() {
	list.value = []
	currentPage.value = 1
	getList()
}

function nextPage() {
	currentPage.value++
	getList()
}

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: MitreTechniquesAlertsQuery = {
		time_range: filters.value?.find(o => o.type === "time_range")?.value as
			| MitreTechniquesAlertsQueryTimeRange
			| undefined,
		size: 5,
		page: currentPage.value,
		rule_level: filters.value?.find(o => o.type === "rule_level")?.value,
		rule_group: filters.value?.find(o => o.type === "rule_group")?.value,
		mitre_field: filters.value?.find(o => o.type === "mitre_field")?.value,
		index_pattern: filters.value?.find(o => o.type === "index_pattern")?.value
	}

	Api.mitre
		.getMitreTechniquesAlerts(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = [...list.value, ...res.data.techniques]
				if (res.data.total_pages > currentPage.value) {
					nextPage()
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

watchDebounced(filters, resetList, {
	deep: true,
	debounce: 300
})
</script>
