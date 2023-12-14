<template>
	<div class="healthcheck-list">
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
						<div class="box text-warning-color">
							Critical :
							<code>{{ criticalTotal }}</code>
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
		</div>
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="healthcheckList.length">
					<HealthcheckItem
						v-for="alert of itemsPaginated"
						:key="alert.checkID + alert.time"
						:alert="alert"
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
import { useMessage, NSpin, NPopover, NButton, NEmpty, NPagination } from "naive-ui"
import Api from "@/api"
import _orderBy from "lodash/orderBy"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import HealthcheckItem from "./HealthcheckItem.vue"
import { InfluxDBAlertLevel, type InfluxDBAlert } from "@/types/healthchecks.d"

const message = useMessage()
const loading = ref(false)
const healthcheckList = ref<InfluxDBAlert[]>([])

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

	const list = _orderBy(healthcheckList.value, ["level", "time"], ["asc", "desc"])

	return list.slice(from, to)
})

const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return healthcheckList.value.length || 0
})

const criticalTotal = computed<number>(() => {
	return healthcheckList.value.filter(o => o.level === InfluxDBAlertLevel.Crit).length || 0
})

function getData() {
	loading.value = true

	Api.healthchecks
		.getHealthchecks()
		.then(res => {
			if (res.data.success) {
				healthcheckList.value = res.data.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			healthcheckList.value = []

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
	getData()
})
</script>

<style lang="scss" scoped>
.healthcheck-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
