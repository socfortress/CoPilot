<template>
	<div class="flex flex-col gap-9" data-testid="uba-rules">
		<UbaRuleSettings :customer-code />

		<UbaSection title="What each rule found" :caption="`${visible.length} rules`">
			<UbaToolbar>
				<SegmentedToggle v-model="since" :options="SINCE_OPTIONS" label="Window" test-id="uba-rules-since" />
				<label class="flex items-center gap-2 pl-1 text-xs">
					<n-switch v-model:value="showNative" size="small" />
					Include native alert rules
				</label>
			</UbaToolbar>

			<UbaError v-if="error" :error />

			<n-data-table
				v-else
				:columns
				:data="visible"
				:loading
				:row-key="(row: UbaRuleStat) => row.rule_id"
				size="small"
				:scroll-x="800"
				class="uba-table"
			/>
		</UbaSection>

		<UbaBacktests :customer-code />
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaRuleStat } from "@/types/uba"
import { NDataTable, NSwitch, NTag } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaBacktests from "./UbaBacktests.vue"
import UbaError from "./UbaError.vue"
import UbaRuleSettings from "./UbaRuleSettings.vue"
import UbaSection from "./ui/UbaSection.vue"
import UbaToolbar from "./ui/UbaToolbar.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const dFormats = useSettingsStore().dateFormat
const SINCE_OPTIONS = [
	{ value: "24h", label: "24 h" },
	{ value: "7d", label: "7 days" },
	{ value: "30d", label: "30 days" }
]
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
	{
		title: "Findings",
		key: "signals",
		width: 100,
		align: "right",
		sorter: (a, b) => a.signals - b.signals,
		defaultSortOrder: "descend",
		render: row => <span class="font-mono tabular-nums">{row.signals}</span>
	},
	{
		title: "Entities",
		key: "entities",
		width: 100,
		align: "right",
		sorter: (a, b) => a.entities - b.entities,
		render: row => <span class="font-mono tabular-nums">{row.entities}</span>
	},
	{ title: "Added risk", key: "with_risk", width: 110, align: "right", render: row => <span class="font-mono tabular-nums">{row.with_risk}</span> },
	{ title: "Suppressed", key: "suppressed", width: 110, align: "right", render: row => <span class="font-mono tabular-nums">{row.suppressed}</span> },
	{
		title: "Last",
		key: "last_signal",
		width: 170,
		render: row => (
			<span class="text-secondary font-mono text-xs tabular-nums">
				{row.last_signal ? String(formatDate(row.last_signal, dFormats.datetime)) : "—"}
			</span>
		)
	}
]

watch(since, load)
onBeforeMount(load)
</script>
