<template>
	<n-spin :show="loading">
		<div class="header flex justify-end" ref="paginationContainer">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="total"
			/>
		</div>
		<div class="list my-3">...</div>
		<div class="footer flex justify-end" ref="paginationContainer">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="total"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, watch } from "vue"
import { useMessage, NSpin, NPagination } from "naive-ui"
import Api from "@/api"
import { nanoid } from "nanoid"
import dayjs from "dayjs"
import { useSettingsStore } from "@/stores/settings"
import type { AlertsQuery } from "@/types/graylog/alerts.d"

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const paginationContainer = ref(null)
const loading = ref(false)
const alerts = ref<any[]>([])
const total = ref(0)
const pageSize = ref(0)
const currentPage = ref(1)

function getMessages(page: number) {
	loading.value = true

	const query: AlertsQuery = {
		query: "",
		page: 1,
		per_page: 100,
		filter: {
			alerts: "only",
			event_definitions: []
		},
		timerange: {
			range: 8640000,
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

watch(currentPage, val => {
	getMessages(val)
})

onBeforeMount(() => {
	getMessages(currentPage.value)
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
