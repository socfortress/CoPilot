<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
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
							Total:
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Indicies:
							<code>{{ usedIndicies }}</code>
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
			<n-select size="small" v-model:value="timerange" :options="timeOptions" class="!w-32" v-if="!compactMode" />
			<n-popover overlap v-if="compactMode" placement="right">
				<template #trigger>
					<div class="bg-color border-radius">
						<n-button size="small">
							<template #icon>
								<Icon :name="FilterIcon"></Icon>
							</template>
						</n-button>
					</div>
				</template>
				<div class="mb-2">
					<div class="text-secondary-color text-sm my-1">Time range:</div>
					<n-select size="small" v-model:value="timerange" :options="timeOptions" class="!w-32 mb-1" />
				</div>
			</n-popover>
		</div>
		<div class="list my-3">
			<template v-if="alertsEvents.length">
				<AlertsEventItem
					v-for="alertsEvent of alertsEvents"
					:key="alertsEvent.event.id"
					:alertsEvent="alertsEvent"
					@click-event="gotoEventsPage($event)"
					class="mb-2"
				/>
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="alertsEvents.length > 3"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, watch, computed } from "vue"
import { useMessage, NSpin, NPagination, NSelect, NPopover, NButton, NEmpty } from "naive-ui"
import Api from "@/api"
import AlertsEventItem from "./Item.vue"
import { useResizeObserver } from "@vueuse/core"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"
import type { AlertsQuery, AlertsEventElement } from "@/types/graylog/alerts.d"

const emit = defineEmits<{
	(e: "clickEvent", value: string): void
}>()

const message = useMessage()
const loading = ref(false)
const alertsEvents = ref<AlertsEventElement[]>([])
const total = ref(0)
const pageSize = ref(50)
const currentPage = ref(1)
const header = ref()
const compactMode = ref(false)
const simpleMode = ref(false)
const showSizePicker = computed(() => !compactMode.value)
const pageSizes = [25, 50, 100, 150, 200]
const pageSlot = ref(8)
const usedIndicies = ref("")

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const hour = 60 * 60
const day = hour * 24
const week = day * 7
const month = week * 4
const year = month * 12

const timerange = ref(year)

const timeOptions = [
	{
		label: "24 Hours",
		value: day
	},
	{
		label: "This week",
		value: dayjs().startOf("week").unix()
	},
	{
		label: "Last week",
		value: week
	},
	{
		label: "This month",
		value: dayjs().startOf("month").unix()
	},
	{
		label: "Last month",
		value: month
	},
	{
		label: "This year",
		value: dayjs().startOf("year").unix()
	},
	{
		label: "Last year",
		value: year
	}
]

function gotoEventsPage(event_definition_id: string) {
	emit("clickEvent", event_definition_id)
}

function getData(page: number, pageSize: number, timerange: number) {
	loading.value = true

	const query: AlertsQuery = {
		query: "",
		page,
		per_page: pageSize,
		filter: {
			alerts: "only",
			event_definitions: []
		},
		timerange: {
			range: timerange,
			type: "relative"
		}
	}

	Api.graylog
		.getAlerts(query)
		.then(res => {
			if (res.data.success) {
				alertsEvents.value = res.data?.alerts?.events || []
				total.value = res.data?.alerts?.total_events || 0
				usedIndicies.value = res.data?.alerts?.used_indices?.join(", ")
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
	const { width } = entry.contentRect

	if (width < 650) {
		compactMode.value = true
		pageSize.value = pageSizes[0]
		pageSlot.value = 5
	} else {
		compactMode.value = false
		pageSlot.value = 8
	}

	simpleMode.value = width < 450
})

watch([currentPage, pageSize, timerange], ([page, pageSize, timerange]) => {
	getData(page, pageSize, timerange)
})

onBeforeMount(() => {
	getData(currentPage.value, pageSize.value, timerange.value)
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
