<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col">
			<div ref="header" class="header flex items-center justify-end gap-2">
				<div class="info flex grow gap-2">
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
								Total Actions:
								<code>{{ total }}</code>
							</div>
						</div>
					</n-popover>

					<n-select
						v-model:value="selectedTechnology"
						:options="technologyOptions"
						clearable
						size="small"
						placeholder="Technology"
						class="max-w-32"
					/>

					<n-select
						v-model:value="selectedCategory"
						:options="categoryOptions"
						clearable
						size="small"
						placeholder="Category"
						class="max-w-32"
					/>

					<n-input
						v-model:value="searchQuery"
						size="small"
						placeholder="Search actions..."
						class="max-w-48"
						clearable
					>
						<template #prefix>
							<Icon :name="SearchIcon"></Icon>
						</template>
					</n-input>
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
						<ActionCard v-for="item of list" :key="item.copilot_action_name" :action="item" />
					</template>
					<template v-else>
						<n-empty v-if="!loading" description="No actions found" class="h-48 justify-center" />
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
import type { CopilotActionInventoryQuery } from "@/api/endpoints/copilotAction"
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import { useResizeObserver, watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NInput, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { Technology } from "@/types/copilotAction.d"
import ActionCard from "./ActionCard.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<ActiveResponseItem[]>([])
const header = ref()
const currentPage = ref(1)
const total = ref(0)
const compactMode = ref(false)
const simpleMode = ref(false)
const showSizePicker = computed(() => !compactMode.value)
const pageSizes = [25, 50, 100, 150, 200]
const pageSize = ref(pageSizes[0])
const pageSlot = ref(8)
const selectedTechnology = ref<Technology | null>(null)
const selectedCategory = ref<string | null>(null)
const searchQuery = ref<string>("")
const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"

const technologyOptions = Object.values(Technology).map(tech => ({
	label: tech,
	value: tech
}))

// Get unique categories from the loaded actions
const categoryOptions = computed(() => {
	const categories = [...new Set(list.value.map(action => action.category).filter(Boolean))]
	return categories.map(category => ({
		label: category,
		value: category
	}))
})

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: CopilotActionInventoryQuery = {
		limit: pageSize.value,
		offset: (currentPage.value - 1) * pageSize.value,
		technology: selectedTechnology.value || undefined,
		category: selectedCategory.value || undefined,
		q: searchQuery.value || undefined
	}

	Api.copilotAction
		.getInventory(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.copilot_actions || []
				total.value = res.data?.copilot_actions?.length || 0
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

watchDebounced([currentPage, pageSize, selectedTechnology, selectedCategory, searchQuery], getList, {
	deep: true,
	debounce: 300,
	immediate: true
})
</script>
