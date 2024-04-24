<template>
	<div class="scheduler-list">
		<n-spin :show="loading" class="min-h-48">
			<div class="list">
				<template v-if="alerts.length">
					<MonitoringAlert
						v-for="alert of itemsPaginated"
						:key="alert.name"
						:alert="alert"
						:is-enabled="isEnabled(alert)"
						class="mb-2"
						@provisioned="getData()"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import MonitoringAlert from "./Item.vue"
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts.d"
import type { EventDefinition } from "@/types/graylog/event-definition.d"

const message = useMessage()
const loadingEvents = ref(false)
const loadingAlerts = ref(false)
const alerts = ref<AvailableMonitoringAlert[]>([])
const events = ref<EventDefinition[]>([])

const loading = computed(() => loadingAlerts.value || loadingEvents.value)

const pageSize = ref(25)
const currentPage = ref(1)

const enabledList = computed<AvailableMonitoringAlert[]>(() => {
	return alerts.value.filter(alert => {
		const eventIndex = events.value.findIndex(event => event.title === alert.name)
		return eventIndex !== -1
	})
})

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return alerts.value.slice(from, to)
})

function isEnabled(alert: AvailableMonitoringAlert): boolean {
	return enabledList.value.findIndex(o => o.name === alert.name) !== -1
}

function getData() {
	loadingAlerts.value = true

	Api.monitoringAlerts
		.getAvailableMonitoringAlerts()
		.then(res => {
			if (res.data.success) {
				alerts.value = res.data.available_monitoring_alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

function getEvents() {
	loadingEvents.value = true

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
			loadingEvents.value = false
		})
}

onBeforeMount(() => {
	getData()
	getEvents()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
