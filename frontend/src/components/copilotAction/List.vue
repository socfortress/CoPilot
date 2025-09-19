<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info">
			CoPilot Actions leverages Velociraptor to run actions and Grafana to view results. See
			<a href="https://github.com/socfortress/CoPilot-Action" target="_blank">
				https://github.com/socfortress/CoPilot-Action
			</a>
			for details.
		</n-alert>

		<div class="flex flex-col">
			<div class="flex flex-wrap items-center justify-end gap-2">
				<div class="flex min-w-80 grow gap-2">
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="bg-default rounded-lg">
								<n-button size="small" class="cursor-help!">
									<template #icon>
										<Icon :name="InfoIcon"></Icon>
									</template>
								</n-button>
							</div>
						</template>
						<div class="flex flex-col gap-2">
							<div class="box">
								Total Actions:
								<code>{{ pagination.total }}</code>
							</div>
						</div>
					</n-popover>

					<n-select
						v-model:value="selectedTechnology"
						:options="technologyOptions"
						clearable
						size="small"
						placeholder="Technology"
						:loading="loadingTechnologies"
						class="max-w-30"
						:consistent-menu-width="false"
					/>

					<n-input
						v-model:value="searchQuery"
						size="small"
						placeholder="Search actions..."
						class="max-w-120!"
						clearable
					>
						<template #prefix>
							<Icon :name="SearchIcon"></Icon>
						</template>
					</n-input>
				</div>

				<n-pagination
					v-model:page="pagination.current"
					:page-size="pagination.size"
					:item-count="pagination.total"
					:page-slot="5"
				/>
			</div>

			<n-spin :show="loading">
				<div class="my-3">
					<div v-if="list.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
						<ActionCard v-for="item of list" :key="item.copilot_action_name" :action="item" />
					</div>

					<template v-else>
						<n-empty v-if="!loading" description="No actions found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>

			<div class="flex justify-end">
				<n-pagination
					v-if="list.length > 3"
					v-model:page="pagination.current"
					:page-size="pagination.size"
					:item-count="pagination.total"
					:page-slot="6"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CopilotActionInventoryQuery } from "@/api/endpoints/copilotAction"
import type { CopilotAction } from "@/types/copilotAction.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NAlert, NButton, NEmpty, NInput, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ActionCard from "./ActionCard.vue"

const loading = ref(false)
const loadingTechnologies = ref(false)
const message = useMessage()
const list = ref<CopilotAction[]>([])
const pagination = ref({
	current: 1,
	size: 24,
	total: 0
})
const selectedTechnology = ref<string | null>(null)
const technologyOptions = ref<{ label: string; value: string }[]>([])
const searchQuery = ref<string | null>(null)
const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: CopilotActionInventoryQuery = {
		offset: (pagination.value.current - 1) * pagination.value.size,
		limit: pagination.value.size,
		technology: selectedTechnology.value || undefined,
		q: searchQuery.value || undefined
	}

	Api.copilotAction
		.getInventory(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.copilot_actions || []
				pagination.value.total = res.data?.total || 0
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

function getTechnologies() {
	loadingTechnologies.value = true

	Api.copilotAction
		.getTechnologies()
		.then(res => {
			if (res.data.success) {
				technologyOptions.value = res.data.technologies.map(o => ({ label: o, value: o }))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingTechnologies.value = false
		})
}

watchDebounced([selectedTechnology, searchQuery, () => pagination.value.current], getList, {
	deep: true,
	debounce: 300,
	immediate: true
})

onBeforeMount(() => {
	getTechnologies()
})
</script>
