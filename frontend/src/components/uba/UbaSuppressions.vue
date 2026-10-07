<template>
	<div class="flex flex-col gap-3" data-testid="uba-suppressions">
		<UbaToolbar>
			<label class="flex items-center gap-2 text-xs">
				<n-switch v-model:value="includeExpired" size="small" />
				Show expired
			</label>
			<template #summary>{{ summary }}</template>
			<template #hint>
				A suppressed rule keeps recording its findings on the entity (they show in its timeline) but adds no
				risk and opens no alert until the date shown. Closing a UBA alert as a false positive suppresses the
				rules behind it for that entity.
			</template>
		</UbaToolbar>

		<UbaError v-if="error" :error />

		<n-data-table
			v-else
			:columns
			:data="suppressions"
			:loading
			:row-key="(row: UbaSuppression) => `${row.entity_key}|${row.rule_id}`"
			size="small"
			:scroll-x="900"
			class="uba-table"
		/>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaSuppression } from "@/types/uba"
import { NButton, NDataTable, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaToolbar from "./ui/UbaToolbar.vue"
import { entityTypeIcon, suppressionOrigin } from "./utils"

const { customerCode, refreshKey = 0 } = defineProps<{ customerCode: string; refreshKey?: number }>()
const emit = defineEmits<{ openEntity: [entityKey: string] }>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const includeExpired = ref(false)
const loading = ref(false)
const removing = ref<string | null>(null)
const error = ref<ApiError | null>(null)
const suppressions = ref<UbaSuppression[]>([])
/** Entity names and types by key: suppressions carry only the key, so each entity is looked up once. */
const names = ref<Record<string, { name: string | null; type: string | null }>>({})
const MAX_LOOKUPS = 50

function resolveNames() {
	const keys = [...new Set(suppressions.value.map(row => row.entity_key))].filter(key => !(key in names.value))
	for (const key of keys.slice(0, MAX_LOOKUPS)) {
		names.value[key] = { name: null, type: null }
		Api.uba
			.getEntity(customerCode, key)
			.then(res => {
				names.value[key] = { name: res.data.entity_name, type: res.data.entity_type }
			})
			.catch(() => {
				// The key stays as the label: an entity UBA no longer knows still reads.
			})
	}
}
/** "2 active", and the expired ones too while they are shown. */
const summary = computed(() => {
	const active = suppressions.value.filter(row => row.active).length
	const expired = suppressions.value.length - active
	return includeExpired.value ? `${active} active · ${expired} expired` : `${active} active`
})

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getSuppressions(customerCode, { include_expired: includeExpired.value })
		.then(res => {
			suppressions.value = res.data.suppressions
			resolveNames()
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
		minWidth: 260,
		render: row => {
			const known = names.value[row.entity_key]
			return (
				<button
					type="button"
					class="group flex max-w-full min-w-0 items-center gap-2.5 text-left"
					title={row.entity_key}
					onClick={() => emit("openEntity", row.entity_key)}
				>
					<span class="entity-icon">
						<Icon name={entityTypeIcon(known?.type)} size={14} />
					</span>
					<span class="flex min-w-0 flex-col">
						<span class="group-hover:text-primary truncate font-medium transition-colors">
							{known?.name || row.entity_key}
						</span>
						{known?.name ? <span class="text-tertiary truncate font-mono text-[11px]">{row.entity_key}</span> : null}
					</span>
				</button>
			)
		}
	},
	{
		title: "Rule",
		key: "rule_id",
		minWidth: 220,
		render: row => (
			<span class="rule-chip inline-block max-w-full truncate align-middle font-mono text-xs whitespace-nowrap" title={row.rule_id}>
				{row.rule_id}
			</span>
		)
	},
	{
		title: "Expires",
		key: "until",
		width: 170,
		render: row => {
			const soon = row.active && dayjs(row.until).diff(dayjs(), "day", true) < 3
			return (
				<div class="flex flex-col leading-tight">
					<span class={["text-sm", !row.active ? "text-tertiary line-through" : soon ? "text-warning" : ""]}>
						{row.active ? dayjs(row.until).fromNow() : `expired ${dayjs(row.until).fromNow()}`}
					</span>
					<span class="text-tertiary font-mono text-[11px] tabular-nums">{String(formatDate(row.until, dFormats.datetime))}</span>
				</div>
			)
		}
	},
	{
		title: "Why",
		key: "reason",
		minWidth: 260,
		render: row => {
			const origin = suppressionOrigin(row.reason, row.source)
			const meta = [
				origin.by ? `by ${origin.by}` : null,
				origin.via ? `via ${origin.via}` : null,
				row.created_at ? dayjs(row.created_at).fromNow() : null
			].filter(Boolean)
			return (
				<div class="flex min-w-0 flex-col leading-tight" title={[row.reason, row.source].filter(Boolean).join("\n")}>
					<span class="truncate text-sm">{origin.why}</span>
					{meta.length ? <span class="text-tertiary truncate text-[11px]">{meta.join(" · ")}</span> : null}
				</div>
			)
		}
	},
	{
		title: "",
		key: "actions",
		width: 120,
		align: "right",
		render: row =>
			row.active ? (
				<NButton size="tiny" quaternary loading={removing.value === `${row.entity_key}|${row.rule_id}`} onClick={() => remove(row)}>
					{{ icon: () => <Icon name="carbon:notification" size={13} />, default: () => "Remove" }}
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
