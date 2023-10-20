<template>
	<n-spin :show="loading">
		<div class="header flex justify-end gap-2"></div>
		<div class="list my-3">...</div>
		<div class="footer flex justify-end"></div>
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
const events = ref<EventDefinition[]>([])

function getData() {
	loading.value = true

	Api.graylog
		.getEventDefinitions()
		.then(res => {
			if (res.data.success) {
				events.value = res.data.event_definitions || []
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

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
