<template>
	<n-modal
		:show
		preset="card"
		segmented
		:mask-closable="!running"
		:style="{ width: 'min(960px, 95vw)', maxHeight: '92vh' }"
		content-class="p-0!"
		@update:show="value => emit('update:show', value)"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="BacktestIcon" :size="20" />
				<span class="font-semibold">Backtest rule</span>
				<n-tag size="tiny" round :bordered="false" type="info">Graylog-only</n-tag>
			</div>
		</template>

		<div class="flex max-h-[78vh] flex-col">
			<n-form class="border-default flex flex-wrap items-end gap-3 border-b px-5 py-4">
				<n-form-item label="Customer" :show-feedback="false" class="min-w-55 grow">
					<n-select
						v-model:value="customerCode"
						:options="customerOptions"
						:loading="loadingCustomers"
						filterable
						placeholder="Select a customer"
					/>
				</n-form-item>
				<n-form-item label="Look-back" :show-feedback="false">
					<n-select
						v-model:value="rangeSeconds"
						:options="rangeOptions"
						class="w-30!"
						:consistent-menu-width="false"
					/>
				</n-form-item>
				<n-button type="primary" :loading="running" :disabled="!customerCode || running" @click="runBacktest">
					<template #icon><Icon :name="RunIcon" :size="16" /></template>
					Run backtest
				</n-button>
			</n-form>

			<n-scrollbar class="grow" style="max-height: calc(78vh - 74px)">
				<div class="px-5 py-4">
					<n-empty
						v-if="!result && !running && !errorMsg"
						description="Pick a customer and run the backtest to see how this rule would behave against their real Graylog data."
						class="py-20"
					>
						<template #icon><Icon :name="BacktestIcon" :size="42" /></template>
					</n-empty>

					<div v-else-if="running" class="flex flex-col items-center gap-3 py-20">
						<n-spin :size="30" />
						<span class="text-secondary text-sm">Querying Graylog… this can take a few seconds.</span>
					</div>

					<n-alert v-else-if="errorMsg" type="error" :bordered="false" title="Backtest failed">
						{{ errorMsg }}
					</n-alert>

					<BacktestResults
						v-else-if="result"
						:result
						:range-label
						@inspect="event => (detailEvent = event)"
					/>
				</div>
			</n-scrollbar>
		</div>
	</n-modal>

	<EventInspectorModal :event="detailEvent" @close="detailEvent = null" />
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { BacktestResponse } from "@/types/copilot-searches"
import { NAlert, NButton, NEmpty, NForm, NFormItem, NModal, NScrollbar, NSelect, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BacktestResults from "@/components/copilotSearches/backtest/BacktestResults.vue"
import EventInspectorModal from "@/components/copilotSearches/backtest/EventInspectorModal.vue"
import { MOCK_LATENCY_MS, mockBacktest, USE_MOCK_BACKTEST } from "@/components/copilotSearches/mock-backtest"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { getApiErrorMessage } from "@/utils"

const { show, yaml } = defineProps<{
	show: boolean
	yaml: string
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
}>()

const BacktestIcon = "carbon:chart-line"
const RunIcon = "carbon:play-filled-alt"

const { options: customerOptions, loading: loadingCustomers, load: loadCustomers } = useCustomerOptions()

const customerCode = ref<string | null>(null)
const rangeSeconds = ref(604800)
const running = ref(false)
const result = ref<BacktestResponse | null>(null)
const errorMsg = ref<string | null>(null)
const detailEvent = ref<Record<string, unknown> | null>(null)

const rangeOptions = [
	{ label: "Last 24 hours", value: 86400 },
	{ label: "Last 3 days", value: 259200 },
	{ label: "Last 7 days", value: 604800 },
	{ label: "Last 14 days", value: 1209600 },
	{ label: "Last 30 days", value: 2592000 }
]

/** The window the results describe — the response wins over the current picker value. */
const rangeLabel = computed(() => {
	const seconds = result.value?.range_seconds ?? rangeSeconds.value
	const days = Math.round(seconds / 86400)
	return days >= 1 ? `${days}d` : `${Math.round(seconds / 3600)}h`
})

async function runBacktest() {
	if (!customerCode.value) return
	running.value = true
	errorMsg.value = null
	result.value = null
	detailEvent.value = null

	// Dev fixture: a fully-populated result so every panel in this modal can be
	// reviewed at once. No real rule + tenant pair fills them all.
	if (USE_MOCK_BACKTEST) {
		// Resolved after a beat rather than synchronously: the fixture exists to review
		// this modal, and a mock that lands instantly is the one state the real run
		// never has — the running spinner would go unreviewed.
		await new Promise(resolve => setTimeout(resolve, MOCK_LATENCY_MS))
		result.value = mockBacktest(customerCode.value, rangeSeconds.value)
		running.value = false
		return
	}

	try {
		const res = await Api.copilotSearches.backtestRule({
			yaml,
			customer_code: customerCode.value,
			range_seconds: rangeSeconds.value
		})
		if (res.data.success) {
			result.value = res.data
		} else {
			errorMsg.value = res.data.error || res.data.message || "Backtest failed."
		}
	} catch (err) {
		errorMsg.value = getApiErrorMessage(err as ApiError) || "Backtest request failed."
	} finally {
		running.value = false
	}
}

watch(
	() => show,
	shown => {
		if (shown) loadCustomers()
	}
)
</script>
