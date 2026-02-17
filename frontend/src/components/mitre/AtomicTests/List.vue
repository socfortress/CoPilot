<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col">
			<div ref="header" class="header flex items-center justify-end gap-2">
				<div class="info flex grow gap-2">
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="bg-default rounded-lg">
								<n-button size="small" class="cursor-help!">
									<template #icon>
										<Icon :name="InfoIcon" />
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

					<n-select
						v-model:value="osCategory"
						:options="osCategoryOptions"
						clearable
						size="small"
						placeholder="OS Category"
						class="max-w-32"
					/>
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
					<template v-if="list.length">
						<TechniqueCard v-for="item of list" :key="item.technique_id" :entity="item" />
					</template>
					<template v-else>
						<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>
			<div class="flex justify-end">
				<n-pagination
					v-if="list.length > 3"
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
// TODO: refactor
import type { MitreAtomicOsCategory, MitreAtomicTestsQuery } from "@/api/endpoints/wazuh/mitre"
import type { MitreAtomicTest } from "@/types/mitre.d"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import TechniqueCard from "./TechniqueCard.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<MitreAtomicTest[]>([])
const header = ref()
const currentPage = ref(1)
const total = ref(0)
const compactMode = ref(false)
const simpleMode = ref(false)
const showSizePicker = computed(() => !compactMode.value)
const pageSizes = [25, 50, 100, 150, 200]
const pageSize = ref(pageSizes[0])
const pageSlot = ref(8)
const osCategory = ref<MitreAtomicOsCategory | null>(null)
const InfoIcon = "carbon:information"

const osCategoryOptions: { label: string; value: MitreAtomicOsCategory }[] = ["windows", "linux", "macos"].map(o => ({
	label: o,
	value: o as MitreAtomicOsCategory
}))

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: MitreAtomicTestsQuery = {
		size: pageSize.value,
		page: currentPage.value,
		os_category: osCategory.value || undefined
	}

	Api.wazuh.mitre
		.getMitreAtomicTests(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.tests || []
				total.value = res.data?.total_techniques || 0
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
	if (!entry) return

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

watchDebounced([currentPage, pageSize, osCategory], getList, {
	deep: true,
	debounce: 300,
	immediate: true
})
// MOCK
/*
list.value = techniqueAlertsResponse.alerts
total.value = techniqueAlertsResponse.total_alerts
*/
</script>
