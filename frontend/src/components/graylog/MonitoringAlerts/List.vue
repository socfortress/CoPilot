<template>
	<div class="monitoring-alert-list">
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
						<div class="box text-success-color">
							Enabled :
							<code>{{ enabledTotal }}</code>
						</div>
					</div>
				</n-popover>
				<CustomAlertButton />
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
		</div>
		<n-spin :show="loading">
			<div class="list my-3">
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
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NPagination } from "naive-ui"
import Api from "@/api"
import MonitoringAlert from "./Item.vue"
import CustomAlertButton from "./CustomAlertButton.vue"
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts.d"
import Icon from "@/components/common/Icon.vue"
import type { EventDefinition } from "@/types/graylog/event-definition.d"

const { eventsList } = defineProps<{ eventsList: EventDefinition[] }>()

const message = useMessage()
const loadingEvents = ref(false)
const loadingAlerts = ref(false)
const alerts = ref<AvailableMonitoringAlert[]>([])
const events = ref<EventDefinition[]>([])

const loading = computed(() => loadingAlerts.value || loadingEvents.value)

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return alerts.value.length || 0
})

const enabledTotal = computed<number>(() => {
	return enabledList.value.length || 0
})

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

	if (eventsList.length && !events.value.length) {
		events.value = eventsList
	} else {
		getEvents()
	}
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
