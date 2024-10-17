<template>
	<div class="monitoring-alerts-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
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
					v-if="monitoringAlerts.length"
					size="small"
					type="error"
					ghost
					:loading="loadingPurge"
					@click="handlePurge()"
				>
					<div class="flex items-center gap-2">
						<Icon :name="TrashIcon" :size="16"></Icon>
						<span class="xs:block hidden">Purge</span>
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
			<div class="list my-3 flex flex-col gap-2">
				<template v-if="monitoringAlerts.length">
					<Alert
						v-for="alert of itemsPaginated"
						:key="alert.id"
						:alert="alert"
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="getData()"
						@invoked="getData()"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MonitoringAlert } from "@/types/monitoringAlerts.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import { NButton, NEmpty, NPagination, NPopover, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Alert from "./Item.vue"

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
