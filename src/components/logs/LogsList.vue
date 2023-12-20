<template>
	<div class="logs-list">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Event Info :
							<code>{{ eventInfoTotal }}</code>
						</div>
						<div class="box text-error-color">
							Event Error :
							<code>{{ eventErrorTotal }}</code>
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
			<n-popover
				:show="showFilters"
				trigger="manual"
				overlap
				placement="right"
				style="padding-left: 0; padding-right: 0"
			>
				<template #trigger>
					<div class="bg-color border-radius">
						<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
							<n-button size="small" @click="showFilters = true">
								<template #icon>
									<Icon :name="FilterIcon"></Icon>
								</template>
							</n-button>
						</n-badge>
					</div>
				</template>
				<LogsFilters
					v-model:type="filterType"
					v-model:value="filterValue"
					v-model:filtered="filtered"
					@submit="getData()"
					@close="showFilters = false"
				/>
			</n-popover>
		</div>
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="logsList.length">
					<LogItem
						v-for="log of itemsPaginated"
						:key="log.id"
						:log="log"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed, toRefs } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NPagination, NBadge } from "naive-ui"
import Api from "@/api"
import _orderBy from "lodash/orderBy"
import Icon from "@/components/common/Icon.vue"
import { nanoid } from "nanoid"
import { useResizeObserver } from "@vueuse/core"
import LogsFilters from "./LogsFilters.vue"
import LogItem from "./LogItem.vue"
import { LogEventType, type Log } from "@/types/logs.d"
import type { LogsQueryTypes, LogsQueryValues } from "@/api/logs"

interface LogExt extends Log {
	id?: string
}

const props = defineProps<{ userId?: string }>()
const { userId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const logsList = ref<LogExt[]>([])
const showFilters = ref(false)

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	const list = _orderBy(logsList.value, ["timestamp"], ["desc"])

	return list.slice(from, to)
})

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return logsList.value.length || 0
})

const eventInfoTotal = computed<number>(() => {
	return logsList.value.filter(o => o.event_type === LogEventType.Info).length || 0
})
const eventErrorTotal = computed<number>(() => {
	return logsList.value.filter(o => o.event_type === LogEventType.Error).length || 0
})

const filterType = ref<LogsQueryTypes | null>(null)
const filterValue = ref<LogsQueryValues | null>(null)

const filtered = ref(false)

function getData() {
	showFilters.value = false
	loading.value = true

	// TODO: add filters

	Api.logs
		.getLogs()
		.then(res => {
			if (res.data.success) {
				logsList.value = (res.data.logs || []).map((o: LogExt) => {
					o.id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			logsList.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	if (userId.value) {
		filterType.value = "userId"
		filterValue.value = userId.value
	}

	getData()
})
</script>

<style lang="scss" scoped>
.logs-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
