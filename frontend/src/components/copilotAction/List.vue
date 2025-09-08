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
			</div>

			<n-spin :show="loading">
				<div class="my-3">
					<template v-if="list.length">
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
							<ActionCard v-for="item of list" :key="item.copilot_action_name" :action="item" />
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loading" description="No actions found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CopilotActionInventoryQuery } from "@/api/endpoints/copilotAction"
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NInput, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { Technology } from "@/types/copilotAction.d"
import ActionCard from "./ActionCard.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<ActiveResponseItem[]>([])
const header = ref()
const total = ref(0)
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
		limit: 100,
		offset: 0,
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

watchDebounced([selectedTechnology, selectedCategory, searchQuery], getList, {
	deep: true,
	debounce: 300,
	immediate: true
})
</script>
