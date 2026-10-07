<template>
	<UbaSection title="Rule settings for this customer">
		<template #description>
			Turn a rule off or give it other points for this customer only; everything else keeps UBA's built-in
			values. A rule turned off still learns what is normal, so turning it back on needs no new learning
			period. Changes apply to new findings within a minute.
			<template v-if="!isAdmin">Only admins can change them.</template>
		</template>

		<UbaError v-if="error" :error />
		<template v-else-if="settings">
			<div class="panel border-default flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 text-sm">
				<span class="flex items-center gap-1.5 font-semibold">
					<Icon name="carbon:meter" :size="15" class="text-primary" />
					Alert threshold
				</span>
				<n-input-number
					v-model:value="threshold"
					:min="20"
					:max="1000"
					:step="10"
					size="small"
					class="w-32"
					:disabled="!isAdmin || saving"
					@keyup.enter="saveThreshold"
				/>
				<span class="text-secondary text-xs">
					points of risk raise an alert (built in: {{ settings.alert_threshold.default }}). One finding worth
					{{ settings.alert_threshold.single_finding }} or more alerts at once.
				</span>
				<template v-if="isAdmin">
					<n-button
						size="small"
						type="primary"
						secondary
						:disabled="threshold === settings.alert_threshold.value || threshold === null"
						:loading="saving"
						@click="saveThreshold"
					>
						Save
					</n-button>
					<n-button
						v-if="settings.alert_threshold.customized"
						size="small"
						quaternary
						:disabled="saving"
						@click="resetThreshold"
					>
						Reset
					</n-button>
				</template>
				<span v-if="settings.alert_threshold.customized" class="text-tertiary w-full text-xs">
					Set by {{ settings.alert_threshold.changed_by }}
					{{ settings.alert_threshold.changed_at ? formatDate(settings.alert_threshold.changed_at, dFormats.datetime) : "" }}
				</span>
			</div>

			<UbaToolbar>
				<n-input v-model:value="search" size="small" clearable placeholder="Search rules" class="w-64!">
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
				<label class="flex items-center gap-2 pl-1 text-xs">
					<n-switch v-model:value="customizedOnly" size="small" />
					Changed for this customer ({{ customizedCount }})
				</label>
			</UbaToolbar>

			<n-data-table
				:columns
				:data="visible"
				:loading
				:row-key="(row: UbaRuleSetting) => row.rule_id"
				size="small"
				:scroll-x="880"
				:max-height="480"
				class="uba-table"
			/>
		</template>
		<n-spin v-else :show="loading" class="min-h-24" />
	</UbaSection>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaRuleSetting, UbaRuleSettingPayload, UbaRuleSettings } from "@/types/uba"
import { NButton, NDataTable, NInput, NInputNumber, NSpin, NSwitch, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaSection from "./ui/UbaSection.vue"
import UbaToolbar from "./ui/UbaToolbar.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

// The groups of CoPilot's "About User Behavior Analytics" card (UBA's detectors/about.py).
const GROUPS: Record<string, string> = {
	auth: "Sign-ins",
	account: "Accounts and privileges",
	mail: "Email",
	saas: "Microsoft 365 apps and policies",
	file: "Files and data",
	process: "Programs",
	inventory: "Computer changes"
}

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const settings = ref<UbaRuleSettings | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<ApiError | null>(null)
const threshold = ref<number | null>(null)
const search = ref("")
const customizedOnly = ref(false)
const pending = ref<string | null>(null) // rule being saved

const customizedCount = computed(() => settings.value?.rules.filter(r => r.customized).length ?? 0)
const visible = computed(() => {
	const q = search.value.trim().toLowerCase()
	return (settings.value?.rules ?? []).filter(
		r =>
			(!customizedOnly.value || r.customized) &&
			(!q || r.name.toLowerCase().includes(q) || r.rule_id.includes(q) || (GROUPS[r.category] ?? "").toLowerCase().includes(q))
	)
})

function apply(next: UbaRuleSettings) {
	settings.value = next
	threshold.value = next.alert_threshold.value
}

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getRuleSettings(customerCode)
		.then(res => apply(res.data))
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function change(row: UbaRuleSetting, payload: UbaRuleSettingPayload) {
	pending.value = row.rule_id
	Api.uba
		.setRuleSetting(customerCode, row.rule_id, payload)
		.then(res => {
			apply(res.data)
			message.success(`${row.name}: saved. UBA applies it to new findings within a minute.`)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Saving the rule setting failed")
		})
		.finally(() => {
			pending.value = null
		})
}

function scoreFrom(e: Event): number | null {
	const raw = (e.target as HTMLInputElement).value.trim()
	const value = Number(raw)
	return raw === "" || Number.isNaN(value) || value < 0 || value > 100 ? null : value
}

function setScore(row: UbaRuleSetting, value: number | null) {
	if (value === null || value === row.score) return
	// Back at the built-in points: clear the customer's value instead of storing the same number.
	change(row, { score: value === row.default_score ? null : value })
}

function setEnabled(row: UbaRuleSetting, value: boolean) {
	change(row, { enabled: value === row.default_enabled ? null : value })
}

function reset(row: UbaRuleSetting) {
	pending.value = row.rule_id
	Api.uba
		.resetRuleSetting(customerCode, row.rule_id)
		.then(res => apply(res.data))
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Resetting the rule failed")
		})
		.finally(() => {
			pending.value = null
		})
}

function saveThreshold() {
	if (threshold.value === null || threshold.value === settings.value?.alert_threshold.value) return
	saving.value = true
	Api.uba
		.setAlertThreshold(customerCode, threshold.value)
		.then(res => {
			apply(res.data)
			message.success("Alert threshold saved. UBA applies it within a minute.")
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Saving the alert threshold failed")
		})
		.finally(() => {
			saving.value = false
		})
}

function resetThreshold() {
	saving.value = true
	Api.uba
		.resetAlertThreshold(customerCode)
		.then(res => apply(res.data))
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Resetting the alert threshold failed")
		})
		.finally(() => {
			saving.value = false
		})
}

const columns = computed<DataTableColumns<UbaRuleSetting>>(() => [
	{
		title: "Rule",
		key: "name",
		minWidth: 300,
		render: row => (
			<div class="flex flex-col">
				<span>{row.name}</span>
				<span class="text-tertiary font-mono text-xs">{row.rule_id}</span>
			</div>
		)
	},
	{ title: "Group", key: "category", width: 170, render: row => GROUPS[row.category] ?? row.category },
	{
		title: "On",
		key: "enabled",
		width: 70,
		render: row => (
			<NSwitch
				size="small"
				value={row.enabled}
				disabled={!isAdmin.value || pending.value === row.rule_id}
				loading={pending.value === row.rule_id}
				onUpdateValue={(v: boolean) => setEnabled(row, v)}
			/>
		)
	},
	{
		title: "Points",
		key: "score",
		width: 170,
		render: row => (
			<div
				class="flex items-center gap-2"
				onKeyup={(e: KeyboardEvent) => e.key === "Enter" && setScore(row, scoreFrom(e))}
			>
				<NInputNumber
					size="small"
					class="w-20"
					min={0}
					max={100}
					showButton={false}
					value={row.score}
					disabled={!isAdmin.value || !row.enabled || pending.value === row.rule_id}
					onBlur={(e: FocusEvent) => setScore(row, scoreFrom(e))}
				/>
				{row.score !== row.default_score ? <span class="text-tertiary text-xs">{`built in ${row.default_score}`}</span> : null}
			</div>
		)
	},
	{
		title: "Changed",
		key: "changed_at",
		minWidth: 200,
		render: row =>
			row.customized ? (
				<div class="flex items-center gap-2">
					<div class="flex flex-col text-xs">
						<NTag size="tiny" bordered={false} type="info" class="w-fit">
							this customer
						</NTag>
						<span class="text-tertiary">
							{`${row.changed_by ?? ""} ${row.changed_at ? formatDate(row.changed_at, dFormats.datetime) : ""}`}
						</span>
					</div>
					{isAdmin.value ? (
						<NButton size="tiny" quaternary disabled={pending.value === row.rule_id} onClick={() => reset(row)}>
							Reset
						</NButton>
					) : null}
				</div>
			) : (
				<span class="text-tertiary text-xs">built in</span>
			)
	}
])

onBeforeMount(load)
</script>

<style scoped>
.panel {
	background-color: var(--bg-secondary-color);
}
</style>
