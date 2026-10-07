<template>
	<div class="flex flex-col gap-6" data-testid="uba-alert-detail">
		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-40">
			<div v-if="alert" class="flex flex-col gap-7">
				<!-- Who it is about and why it opened: the whole box opens the entity. -->
				<div class="flex flex-col gap-2">
					<div
						class="summary border-default flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-3"
						role="button"
						tabindex="0"
						:aria-label="`Open ${alert.entity_name || alert.entity_key}`"
						data-testid="uba-alert-entity"
						@click="emit('openEntity', alert.entity_key)"
						@keydown.enter.prevent="emit('openEntity', alert.entity_key)"
						@keydown.space.prevent="emit('openEntity', alert.entity_key)"
					>
						<span class="entity-icon" aria-hidden="true">
							<Icon :name="entityTypeIcon(alert.entity_type)" :size="14" />
						</span>
						<div class="flex min-w-0 flex-1 flex-col gap-0.5">
							<span class="truncate font-medium">{{ alert.entity_name || alert.entity_key }}</span>
							<span class="text-tertiary flex flex-wrap gap-x-2 font-mono text-[11px]">
								<span v-if="alert.reason">{{ alert.reason }}</span>
								<span>opened {{ formatDate(alert.opened_at, dFormats.datetime) }}</span>
							</span>
						</div>
						<Icon name="carbon:arrow-right" :size="16" class="go text-tertiary shrink-0" aria-hidden="true" />
					</div>
					<n-button
						v-if="alert.copilot_alert_id"
						size="tiny"
						quaternary
						class="self-end"
						@click="routeIncidentManagementAlerts(alert.copilot_alert_id).navigate()"
					>
						<template #icon><Icon name="carbon:launch" :size="12" /></template>
						Incident alert #{{ alert.copilot_alert_id }}
					</n-button>
				</div>

				<UbaSection title="What it was made of" caption="24 h before it opened" test-id="uba-alert-signals">
					<SignalTimeline :items="signalItems" :customer-code />
				</UbaSection>

				<UbaSection v-if="updates.length" title="Updates" caption="new findings while it was open" test-id="uba-alert-updates">
					<SignalTimeline :items="updateItems" :customer-code />
				</UbaSection>

				<UbaSection title="Verdict" test-id="uba-alert-verdict">
					<div v-if="alert.verdict" class="verdict border-default flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2.5 text-sm">
						<n-tag :type="alert.verdict === 'FALSE_POSITIVE' ? 'default' : 'error'" :bordered="false">
							{{ alert.verdict === "FALSE_POSITIVE" ? "False positive" : "True positive" }}
						</n-tag>
						<span class="text-secondary">
							{{ alert.verdict_reason ? `${alert.verdict_reason} · ` : "" }}by {{ alert.verdict_by || "unknown" }}
						</span>
						<span v-if="alert.verdict_at" class="text-tertiary ml-auto font-mono text-[11px]">
							{{ formatDate(alert.verdict_at, dFormats.datetime) }}
						</span>
					</div>
					<div v-else class="verdict border-default flex flex-col gap-3 rounded-lg border p-3">
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Verdict" data-testid="uba-verdict">
							<button
								v-for="option of VERDICT_OPTIONS"
								:key="option.value"
								type="button"
								role="radio"
								class="verdict-choice flex items-start gap-3 rounded-lg border px-3 py-2.5 text-left"
								:class="{ 'is-selected': verdict === option.value }"
								:aria-checked="verdict === option.value"
								:data-testid="`uba-verdict-${option.value}`"
								@click="verdict = option.value"
							>
								<Icon :name="option.icon" :size="18" class="choice-icon mt-0.5 shrink-0" />
								<span class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="text-sm font-semibold">{{ option.label }}</span>
									<span class="text-tertiary text-xs leading-snug">{{ option.hint }}</span>
								</span>
								<Icon
									:name="verdict === option.value ? 'carbon:checkmark-filled' : 'carbon:circle-dash'"
									:size="16"
									class="check mt-0.5 shrink-0"
								/>
							</button>
						</div>
						<template v-if="verdict === 'FALSE_POSITIVE'">
							<n-select v-model:value="reason" :options="FALSE_POSITIVE_REASONS" placeholder="Why" size="small" class="max-w-xs" />
							<n-checkbox v-model:checked="suppress">
								Suppress the rules behind this alert for this entity for 30 days
							</n-checkbox>
						</template>
						<n-input v-model:value="note" type="textarea" placeholder="Note (optional)" :autosize="{ minRows: 2 }" size="small" />
						<div class="flex justify-end">
							<!-- A verdict is final (see confirmText): confirm before it is sent. -->
							<n-popconfirm
								:disabled="!canSubmit"
								:positive-text="`Save ${verdictLabel}`"
								negative-text="Cancel"
								style="max-width: 320px"
								@positive-click="submit"
							>
								<template #trigger>
									<n-button
										type="primary"
										size="small"
										:disabled="!canSubmit"
										:loading="submitting"
										data-testid="uba-verdict-save"
									>
										<template #icon><Icon name="carbon:checkmark" :size="14" /></template>
										Save verdict
									</n-button>
								</template>
								<span class="text-sm" data-testid="uba-verdict-confirm">{{ confirmText }}</span>
							</n-popconfirm>
						</div>
					</div>
				</UbaSection>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SignalTimelineItem } from "./ui/SignalTimeline.vue"
import type { UbaDrawerMeta } from "./ui/UbaDrawerHeader.vue"
import type { ApiError } from "@/types/common"
import type { UbaAlert, UbaAlertUpdate, UbaSignal } from "@/types/uba"
import { NButton, NCheckbox, NInput, NPopconfirm, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import SignalTimeline from "./ui/SignalTimeline.vue"
import UbaSection from "./ui/UbaSection.vue"
import { entityTypeIcon, FALSE_POSITIVE_REASONS } from "./utils"

const { customerCode, alertId } = defineProps<{ customerCode: string; alertId: string }>()
const emit = defineEmits<{ openEntity: [entityKey: string]; changed: []; meta: [meta: UbaDrawerMeta] }>()

const { routeIncidentManagementAlerts } = useNavigation()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const alert = ref<UbaAlert | null>(null)
const signals = ref<UbaSignal[]>([])
const updates = ref<UbaAlertUpdate[]>([])
const verdict = ref<"TRUE_POSITIVE" | "FALSE_POSITIVE" | null>(null)
const reason = ref<string | null>(null)
const note = ref("")
const suppress = ref(true)

const VERDICT_OPTIONS: { value: "TRUE_POSITIVE" | "FALSE_POSITIVE"; label: string; hint: string; icon: string }[] = [
	{
		value: "TRUE_POSITIVE",
		label: "True positive",
		hint: "A real threat: the alert stands and the risk keeps counting.",
		icon: "carbon:security"
	},
	{
		value: "FALSE_POSITIVE",
		label: "False positive",
		hint: "Expected activity: say why, and optionally mute the rules behind it.",
		icon: "carbon:checkmark-outline"
	}
]

const signalItems = computed<SignalTimelineItem[]>(() =>
	signals.value.map(s => ({
		key: s.id,
		time: s.time,
		ruleId: s.rule_id,
		explanation: s.explanation,
		points: s.effective_score,
		native: s.native,
		suppressed: s.suppressed,
		muted: s.suppressed || s.effective_score === 0,
		signalId: s.id,
		evidenceCount: s.evidence.length
	}))
)

const updateItems = computed<SignalTimelineItem[]>(() =>
	updates.value.map((u, i) => ({
		key: `u${i}`,
		time: u.time,
		ruleId: u.rule_id,
		explanation: u.explanation ?? "",
		points: u.effective ?? null
	}))
)

/** The drawer's header: the alert, its risk when it opened, and whether it is still open. */
const meta = computed<UbaDrawerMeta | null>(() => {
	const a = alert.value
	if (!a) return null
	const tags: NonNullable<UbaDrawerMeta["tags"]> = a.verdict
		? [{ label: a.verdict === "FALSE_POSITIVE" ? "false positive" : "true positive", type: a.verdict === "FALSE_POSITIVE" ? "default" : "error" }]
		: [{ label: "open", type: "error", icon: "carbon:warning-alt-filled" }]
	if (a.update_count) tags.push({ label: `${a.update_count} update${a.update_count === 1 ? "" : "s"}` })
	if (a.copilot_alert_id) tags.push({ label: `incident #${a.copilot_alert_id}`, icon: "carbon:link" })
	return {
		kind: "UBA alert",
		icon: "carbon:warning-alt",
		title: a.entity_name || a.entity_key,
		key: a.id,
		keyLabel: "Alert id",
		risk: a.risk,
		tags
	}
})

watch(meta, value => value && emit("meta", value))

const verdictLabel = computed(() => (verdict.value === "FALSE_POSITIVE" ? "false positive" : "true positive"))

/**
 * What saving does. A verdict cannot be changed afterwards (UBA keeps the first one on CoPilot's
 * incident, and a false positive's suppressions are not lifted by a later verdict), so say so.
 */
const confirmText = computed(() =>
	verdict.value === "FALSE_POSITIVE" && suppress.value
		? "Save this alert as a false positive? The rules behind it stop adding risk for this entity for 30 days. The verdict cannot be changed afterwards."
		: `Save this alert as a ${verdictLabel.value}? The verdict cannot be changed afterwards.`
)

const canSubmit = computed(() => verdict.value === "TRUE_POSITIVE" || (verdict.value === "FALSE_POSITIVE" && !!reason.value))

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getAlert(customerCode, alertId)
		.then(res => {
			alert.value = res.data.alert
			signals.value = res.data.signals
			updates.value = res.data.updates
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function submit() {
	if (!verdict.value) return
	submitting.value = true
	Api.uba
		.submitFeedback(customerCode, alertId, {
			verdict: verdict.value,
			reason: verdict.value === "FALSE_POSITIVE" ? reason.value : null,
			note: note.value || null,
			suppress: verdict.value === "FALSE_POSITIVE" && suppress.value
		})
		.then(res => {
			const rules = res.data.suppressed_rules
			message.success(rules.length ? `Saved. ${rules.length} rule(s) suppressed for this entity.` : "Verdict saved.")
			emit("changed")
			load()
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Saving the verdict failed.")
		})
		.finally(() => {
			submitting.value = false
		})
}

onBeforeMount(load)
</script>

<style scoped>
.summary,
.verdict {
	background-color: var(--bg-secondary-color);
}

.summary {
	transition: border-color 0.15s;
}

.summary:hover,
.summary:focus-visible {
	border-color: var(--primary-color);
	outline: none;
}

.summary:hover .go,
.summary:focus-visible .go {
	color: var(--primary-color);
}

/* A verdict is a choice between two buttons: a raised card each, the chosen one in the accent. */
.verdict-choice {
	border-color: var(--border-color);
	background-color: var(--bg-default-color);
	transition:
		border-color 0.15s,
		background-color 0.15s;
}

.verdict-choice:hover {
	border-color: var(--fg-tertiary-color);
}

.verdict-choice:focus-visible {
	outline: 1px solid var(--primary-color);
	outline-offset: 1px;
}

.verdict-choice .choice-icon,
.verdict-choice .check {
	color: var(--fg-tertiary-color);
}

.verdict-choice.is-selected {
	border-color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.08);
}

.verdict-choice.is-selected .choice-icon,
.verdict-choice.is-selected .check {
	color: var(--primary-color);
}
</style>
