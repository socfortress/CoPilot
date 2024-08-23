<template>
	<div class="alerts-list">
		<div class="header flex items-center justify-end gap-2">
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
							Total Summaries:
							<code>{{ totalAlertsSummary }}</code>
						</div>
						<div class="box">
							Total Alerts:
							<code>{{ totalAlerts }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex gap-2 items-center">
				<n-button size="small" @click="showFiltersDrawer = true">
					<template #icon>
						<Icon :name="FilterIcon" :size="15"></Icon>
					</template>
					Filters
				</n-button>
				<ThreatIntelButton size="small" type="primary" />
			</div>
		</div>
		<n-spin :show="loading">
			<template #description>Alerts are being fetched, this may take up to 1 minute.</template>

			<div class="list flex flex-col gap-2 my-3">
				<template v-if="alertsSummaryList.length">
					<AlertsSummaryItem
						v-for="alertsSummary of alertsSummaryList"
						:key="alertsSummary.index_name"
						:alertsSummary="alertsSummary"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>

		<n-drawer
			v-model:show="showFiltersDrawer"
			display-directive="show"
			:trap-focus="false"
			style="max-width: 90vw; width: 500px"
			:show-mask="loadingFilters ? 'transparent' : undefined"
			:class="{ 'opacity-0': loadingFilters }"
		>
			<n-drawer-content title="Alerts filters" closable :native-scrollbar="false">
				<AlertsGraylogFilters :filters="filters" @search="startSearch(true)" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
// MOCK
// import { alerts_summary } from "./mock"
// import type { AlertsSummary } from "@/types/alerts.d"

import { ref, onBeforeMount, computed, nextTick, onMounted, onBeforeUnmount, defineAsyncComponent } from "vue"
import { useMessage, NSpin, NPopover, NButton, NEmpty, NDrawer, NDrawerContent } from "naive-ui"
import Api from "@/api"
const ThreatIntelButton = defineAsyncComponent(() => import("@/components/threatIntel/ThreatIntelButton.vue"))
import AlertsGraylogFilters from "./AlertsGraylogFilters.vue"
import AlertsSummaryItem, { type AlertsSummaryExt } from "./AlertsSummary.vue"
import Icon from "@/components/common/Icon.vue"
import type { GraylogAlertsQuery } from "@/api/endpoints/alerts"
import type { IndexStats } from "@/types/indices.d"
import axios from "axios"

const message = useMessage()
const loading = ref(false)
const indices = ref<IndexStats[]>([])
const alertsSummaryList = ref<AlertsSummaryExt[]>([])
const loadingFilters = ref(true)
const showFiltersDrawer = ref(true)
let abortController: AbortController | null = null

const InfoIcon = "carbon:information"
const FilterIcon = "carbon:filter-edit"

const totalAlertsSummary = computed<number>(() => {
	return alertsSummaryList.value.length || 0
})
const totalAlerts = computed<number>(() => {
	return alertsSummaryList.value.reduce((acc: number, val: AlertsSummaryExt) => {
		return acc + val.alerts.length
	}, 0)
})

const filters = ref<Partial<GraylogAlertsQuery>>({})

function addIndexInfo() {
	if (indices.value?.length && alertsSummaryList.value.length) {
		for (const alert of alertsSummaryList.value) {
			const index = indices.value.find(o => o.index === alert.index_name)
			alert.indexStats = index
		}
	}
}

function getData() {
	loading.value = true

	abortController = new AbortController()

	Api.alerts
		.getGraylogAlertsList(filters.value, abortController.signal)
		.then(res => {
			alertsSummaryList.value = res.data?.alerts_summary || []

			if (res.data.success) {
				nextTick(() => {
					addIndexInfo()
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				alertsSummaryList.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

function startSearch(closeDrawer?: boolean) {
	cancelSearch()

	setTimeout(() => {
		getData()
	}, 200)

	if (closeDrawer) {
		showFiltersDrawer.value = false
	}
}

function cancelSearch() {
	abortController?.abort()
}

onBeforeMount(() => {
	nextTick(() => {
		// MOCK
		// alertsSummaryList.value = alerts_summary as AlertsSummary[]
		startSearch()
	})
})

onMounted(() => {
	showFiltersDrawer.value = false

	setTimeout(() => {
		loadingFilters.value = false
	}, 1000)
})

onBeforeUnmount(() => {
	cancelSearch()
})
</script>

<style lang="scss" scoped>
.alerts-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
