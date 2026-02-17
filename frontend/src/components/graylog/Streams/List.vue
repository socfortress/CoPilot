<template>
	<n-spin :show="loading">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
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
						<div class="box">
							Enabled:
							<code>{{ totalEnabled }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
			<n-popover overlap placement="right" class="px-0!">
				<template #trigger>
					<div class="bg-default rounded-lg">
						<n-button size="small">
							<template #icon>
								<Icon :name="FilterIcon" />
							</template>
						</n-button>
					</div>
				</template>
				<div class="py-1">
					<div class="px-3">
						<div class="text-secondary mb-1 text-sm">Enabled:</div>
						<n-select
							v-model:value="enabledFilter"
							size="small"
							:options="enabledOptions"
							clearable
							placeholder="All"
							class="w-36!"
						/>
					</div>
					<n-divider class="my-3!" />
					<div class="px-3">
						<div class="text-secondary mb-1 text-sm">Editable:</div>
						<n-select
							v-model:value="editableFilter"
							size="small"
							:options="editableOptions"
							clearable
							placeholder="All"
							class="w-36!"
						/>
					</div>
				</div>
			</n-popover>
		</div>
		<div class="my-3 flex min-h-52 flex-col gap-2">
			<template v-if="itemsPaginated.length">
				<StreamItem v-for="stream of itemsPaginated" :key="stream.id" :stream="stream" />
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: refactor
import type { Stream } from "@/types/graylog/stream.d"
import { useResizeObserver } from "@vueuse/core"
import { NButton, NDivider, NEmpty, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import StreamItem from "./Item.vue"

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const streams = ref<Stream[]>([])
const total = ref(0)
const totalEnabled = computed(() => streams.value.filter(o => !o.disabled).length)
const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)
const enabledFilter = ref<null | number>(null)
const editableFilter = ref<null | number>(null)
const enabledOptions = [
	{ label: "Enabled", value: 1 },
	{ label: "Not Enabled", value: 0 }
]
const editableOptions = [
	{ label: "Editable", value: 1 },
	{ label: "Not Editable", value: 0 }
]

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return streams.value
		.filter(o => {
			switch (enabledFilter.value) {
				case 1:
					return o.disabled === false
				case 0:
					return o.disabled === true
				default:
					return true
			}
		})
		.filter(o => {
			switch (editableFilter.value) {
				case 1:
					return o.is_editable === true
				case 0:
					return o.is_editable === false
				default:
					return true
			}
		})
		.slice(from, to)
})

function getData() {
	loading.value = true

	Api.graylog
		.getStreams()
		.then(res => {
			if (res.data.success) {
				streams.value = res.data.streams || []
				total.value = res.data.total || 0
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	if (!entry) return

	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	getData()
})
</script>
