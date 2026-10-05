<template>
	<div class="flex flex-col gap-3">
		<UbaRuleSettings :customer-code class="mb-4" />

		<span :class="SECTION_LABEL">What each rule found</span>
		<div class="flex flex-wrap items-end justify-between gap-3">
			<n-radio-group v-model:value="since" size="small">
				<n-radio-button value="24h">24 h</n-radio-button>
				<n-radio-button value="7d">7 days</n-radio-button>
				<n-radio-button value="30d">30 days</n-radio-button>
			</n-radio-group>
			<n-checkbox v-model:checked="showNative" size="small">Include native alert rules</n-checkbox>
		</div>

		<UbaError v-if="error" :error />

		<n-data-table
			v-else
			:columns
			:data="visible"
			:loading
			:row-key="(row: UbaRuleStat) => row.rule_id"
			size="small"
			:scroll-x="800"
		/>

		<UbaBacktests :customer-code class="mt-4" />
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaRuleStat } from "@/types/uba"
import { NCheckbox, NDataTable, NRadioButton, NRadioGroup, NTag } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaBacktests from "./UbaBacktests.vue"
import UbaError from "./UbaError.vue"
import UbaRuleSettings from "./UbaRuleSettings.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const dFormats = useSettingsStore().dateFormat
const since = ref("7d")
const showNative = ref(false)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const rules = ref<UbaRuleStat[]>([])
const visible = computed(() => (showNative.value ? rules.value : rules.value.filter(r => !r.native)))

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getRuleStats(customerCode, since.value)
		.then(res => {
			rules.value = res.data.rules
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

const columns: DataTableColumns<UbaRuleStat> = [
	{
		title: "Rule",
		key: "rule_id",
		minWidth: 260,
		render: row => (
			<div class="flex items-center gap-2">
				<span class="font-mono text-xs">{row.rule_id}</span>
				{row.native ? (
					<NTag size="tiny" bordered={false}>
						native
					</NTag>
				) : null}
			</div>
		)
	},
	{ title: "Signals", key: "signals", width: 90, sorter: (a, b) => a.signals - b.signals, defaultSortOrder: "descend" },
	{ title: "Entities", key: "entities", width: 90, sorter: (a, b) => a.entities - b.entities },
	{ title: "Added risk", key: "with_risk", width: 100 },
	{ title: "Suppressed", key: "suppressed", width: 100 },
	{
		title: "Last",
		key: "last_signal",
		width: 170,
		render: row => (row.last_signal ? String(formatDate(row.last_signal, dFormats.datetime)) : "—")
	}
]

watch(since, load)
onBeforeMount(load)
</script>
