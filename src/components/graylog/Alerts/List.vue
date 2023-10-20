<template>
	<n-spin :show="loading">
		<div class="header flex justify-end gap-2">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				show-size-picker
				:page-sizes="[50, 100, 150, 200]"
			/>
			<n-select size="small" v-model:value="timerange" :options="timeOptions" class="!w-32" />
		</div>
		<div class="list my-3">...</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="alerts.length > 3"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, watch } from "vue"
import { useMessage, NSpin, NPagination, NSelect } from "naive-ui"
import Api from "@/api"
import { nanoid } from "nanoid"
import dayjs from "dayjs"
import { useSettingsStore } from "@/stores/settings"
import type { AlertsQuery } from "@/types/graylog/alerts.d"

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loading = ref(false)
const alerts = ref<any[]>([])
const total = ref(0)
const pageSize = ref(100)
const currentPage = ref(1)

const hour = 60 * 60
const day = hour * 24
const week = day * 7
const month = week * 4
const year = month * 12

const timerange = ref(month)

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
				//....
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
}
</style>
