<template>
	<div class="monitoring-alerts-list">
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
					</div>
				</n-popover>

				<n-button
					size="small"
					type="error"
					ghost
					@click="handlePurge()"
					:loading="loadingPurge"
					v-if="monitoringAlerts.length"
				>
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16"></Icon>
						<span class="hidden xs:block">Purge</span>
					</div>
				</n-button>
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
				<template v-if="monitoringAlerts.length">
					<Alert
						v-for="alert of itemsPaginated"
						:key="alert.id"
						:alert="alert"
						@deleted="getData()"
						@invoked="getData()"
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
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NPagination, useDialog } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import Alert from "./Item.vue"
import type { MonitoringAlert } from "@/types/monitoringAlerts.d"

const dialog = useDialog()
const message = useMessage()
const loadingPurge = ref(false)
const loading = ref(false)
const monitoringAlerts = ref<MonitoringAlert[]>([])

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

	return monitoringAlerts.value.slice(from, to)
})

const TrashIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return monitoringAlerts.value.length || 0
})

function getData() {
	loading.value = true

	Api.monitoringAlerts
		.listAll()
		.then(res => {
			if (res.data.success) {
				monitoringAlerts.value = res.data?.monitoring_alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			monitoringAlerts.value = []

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function handlePurge() {
	dialog.warning({
		title: "Confirm",
		content: "This will remove ALL Pending Alerts, are you sure you want to proceed?",
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			purge()
		},
		onNegativeClick: () => {
			message.info("Purge canceled")
		}
	})
}

function purge() {
	loadingPurge.value = true

	Api.monitoringAlerts
		.purge()
		.then(res => {
			if (res.data.success) {
				getData()
				message.success(res.data?.message || "Pending Alerts purged successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingPurge.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	simpleMode.value = width < 550
})

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.monitoring-alerts-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
