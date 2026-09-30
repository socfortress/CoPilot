<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="text-secondary max-w-2xl text-xs">
				A suppressed rule keeps recording its findings on the entity (they show in the entity's timeline)
				but adds no risk and opens no alert until the date shown. Closing a UBA alert as a false positive
				suppresses the rules behind it for that entity.
			</p>
			<n-checkbox v-model:checked="includeExpired" size="small">Show expired</n-checkbox>
		</div>

		<UbaError v-if="error" :error />

		<n-data-table
			v-else
			:columns
			:data="suppressions"
			:loading
			:row-key="(row: UbaSuppression) => `${row.entity_key}|${row.rule_id}`"
			size="small"
			:scroll-x="900"
		/>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaSuppression } from "@/types/uba"
import { NButton, NCheckbox, NDataTable, NTag, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"

const { customerCode, refreshKey = 0 } = defineProps<{ customerCode: string; refreshKey?: number }>()
const emit = defineEmits<{ openEntity: [entityKey: string] }>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const includeExpired = ref(false)
const loading = ref(false)
const removing = ref<string | null>(null)
const error = ref<ApiError | null>(null)
const suppressions = ref<UbaSuppression[]>([])

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getSuppressions(customerCode, { include_expired: includeExpired.value })
		.then(res => {
			suppressions.value = res.data.suppressions
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function remove(row: UbaSuppression) {
	removing.value = `${row.entity_key}|${row.rule_id}`
	Api.uba
		.removeSuppressions(customerCode, row.entity_key, row.rule_id)
		.then(() => {
			message.success(`${row.rule_id} counts again for this entity (within a minute).`)
			load()
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Removing the suppression failed.")
		})
		.finally(() => {
			removing.value = null
		})
}

const columns: DataTableColumns<UbaSuppression> = [
	{
		title: "Entity",
		key: "entity_key",
		minWidth: 220,
		render: row => (
			<NButton text type="primary" class="font-mono text-xs" onClick={() => emit("openEntity", row.entity_key)}>
				{row.entity_key}
			</NButton>
		)
	},
	{ title: "Rule", key: "rule_id", minWidth: 200, render: row => <span class="font-mono text-xs">{row.rule_id}</span> },
	{
		title: "Until",
		key: "until",
		width: 170,
		render: row => (
			<span class={row.active ? "" : "text-tertiary line-through"}>{formatDate(row.until, dFormats.datetime)}</span>
		)
	},
	{ title: "Why", key: "reason", minWidth: 220, ellipsis: { tooltip: true } },
	{
		title: "Source",
		key: "source",
		width: 180,
		ellipsis: { tooltip: true },
		render: row => <NTag size="small" bordered={false}>{row.source || "—"}</NTag>
	},
	{
		title: "",
		key: "actions",
		width: 90,
		render: row =>
			row.active ? (
				<NButton size="tiny" secondary loading={removing.value === `${row.entity_key}|${row.rule_id}`} onClick={() => remove(row)}>
					Remove
				</NButton>
			) : null
	}
]

watch(includeExpired, load)
watch(
	() => refreshKey,
	() => load()
)
onBeforeMount(load)
</script>
