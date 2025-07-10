<template>
	<div class="flex flex-col gap-4">
		<Filters @update="filters = $event" />

		<div class="flex flex-col">
			<div ref="header" class="header flex items-center justify-end gap-2">
				<div class="info flex grow gap-5">
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="bg-default rounded-lg">
								<n-button size="small" class="!cursor-help">
									<template #icon>
										<Icon :name="InfoIcon"></Icon>
									</template>
								</n-button>
							</div>
						</template>
						<div class="flex flex-col gap-2">
							<div class="box">
								Total:
								<code>{{ total }}</code>
							</div>
						</div>
					</n-popover>
				</div>
				<n-pagination
					v-model:page="currentPage"
					v-model:page-size="pageSize"
					:item-count="total"
					:page-slot="pageSlot"
					:show-size-picker="showSizePicker"
					:page-sizes="pageSizes"
					:simple="simpleMode"
				/>
			</div>

			<n-spin :show="loading">
				<div class="my-3 flex min-h-28 flex-col gap-2">
					<template v-if="alertsList.length">
						<TechniqueEventCard
							v-for="alert of alertsList"
							:key="alert.id"
							:alert
							embedded
							use-details-tab
						/>
					</template>
					<template v-else>
						<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>
			<div class="flex justify-end">
				<n-pagination
					v-if="alertsList.length > 3"
					v-model:page="currentPage"
					:page-size="pageSize"
					:item-count="total"
					:page-slot="6"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreEventsQuery, MitreTechniquesAlertsQueryTimeRange } from "@/api/endpoints/mitre"
import type { MitreEventDetails } from "@/types/mitre.d"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Filters from "./Filters.vue"
import TechniqueEventCard from "./TechniqueEventCard.vue"

const { externalId } = defineProps<{
	externalId: string
}>()

const filters = ref<{ type: string; value: string }[]>([])
const loading = ref(false)
const message = useMessage()
const alertsList = ref<MitreEventDetails[]>([])
const header = ref()
const currentPage = ref(1)
const total = ref(0)
const compactMode = ref(false)
const simpleMode = ref(false)
const showSizePicker = computed(() => !compactMode.value)
const pageSizes = [25, 50, 100, 150, 200]
const pageSize = ref(pageSizes[0])
const pageSlot = ref(8)
const InfoIcon = "carbon:information"

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: MitreEventsQuery = {
		technique_id: externalId,
		time_range: filters.value?.find(o => o.type === "time_range")?.value as
			| MitreTechniquesAlertsQueryTimeRange
			| undefined,
		size: pageSize.value,
		page: currentPage.value,
		rule_level: filters.value?.find(o => o.type === "rule_level")?.value,
		rule_group: filters.value?.find(o => o.type === "rule_group")?.value,
		mitre_field: filters.value?.find(o => o.type === "mitre_field")?.value,
		index_pattern: filters.value?.find(o => o.type === "index_pattern")?.value
	}

	Api.wazuh.mitre
		.getMitreEvents(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
				total.value = res.data?.total_alerts || 0
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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	if (width < 650) {
		compactMode.value = true
		pageSlot.value = 5
	} else {
		compactMode.value = false
		pageSlot.value = 8
	}

	simpleMode.value = width < 450
})

watchDebounced([filters, currentPage, pageSize], getList, {
	deep: true,
	debounce: 300,
	immediate: true
})
// MOCK
/*
alertsList.value = techniqueAlertsResponse.alerts
total.value = techniqueAlertsResponse.total_alerts
*/
</script>
