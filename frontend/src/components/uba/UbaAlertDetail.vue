<template>
	<div class="flex flex-col gap-4">
		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-40">
			<template v-if="alert">
				<header class="flex flex-wrap items-center gap-2">
					<n-tag :type="riskTagType(alert.risk)" round :bordered="false">risk {{ riskLabel(alert.risk) }}</n-tag>
					<n-button text type="primary" @click="emit('openEntity', alert.entity_key)">
						{{ alert.entity_name || alert.entity_key }}
					</n-button>
					<span class="text-tertiary text-xs">opened {{ formatDate(alert.opened_at, dFormats.datetime) }}</span>
					<n-tag v-if="alert.copilot_alert_id" size="small" :bordered="false">incident #{{ alert.copilot_alert_id }}</n-tag>
				</header>
				<p v-if="alert.reason" class="text-secondary text-sm">{{ alert.reason }}</p>

				<section class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">What it was made of (24 h before it opened)</span>
					<ul class="flex flex-col gap-2">
						<li v-for="s of signals" :key="s.id" class="border-default rounded-lg border px-3 py-2">
							<div class="flex flex-wrap items-center gap-2">
								<span class="text-tertiary text-xs">{{ formatDate(s.time, dFormats.datetime) }}</span>
								<span class="font-mono text-xs">{{ s.rule_id }}</span>
								<n-tag v-if="s.native" size="tiny" :bordered="false">native</n-tag>
								<span class="text-tertiary ml-auto text-xs">+{{ riskLabel(s.effective_score) }}</span>
							</div>
							<p class="mt-1 text-sm">{{ s.explanation }}</p>
						</li>
					</ul>
				</section>

				<section v-if="updates.length" class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Updates (new findings while it was open)</span>
					<ul class="flex flex-col gap-2">
						<li v-for="(u, i) of updates" :key="i" class="border-default rounded-lg border px-3 py-2">
							<div class="flex flex-wrap items-center gap-2">
								<span class="text-tertiary text-xs">{{ formatDate(u.time, dFormats.datetime) }}</span>
								<span v-if="u.rule_id" class="font-mono text-xs">{{ u.rule_id }}</span>
							</div>
							<p class="mt-1 text-sm whitespace-pre-line">{{ u.explanation }}</p>
						</li>
					</ul>
				</section>

				<section class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Verdict</span>
					<div v-if="alert.verdict" class="text-sm">
						<n-tag :type="alert.verdict === 'FALSE_POSITIVE' ? 'default' : 'error'" :bordered="false">
							{{ alert.verdict === "FALSE_POSITIVE" ? "False positive" : "True positive" }}
						</n-tag>
						<span class="text-secondary ml-2">
							{{ alert.verdict_reason || "" }} by {{ alert.verdict_by || "unknown" }}
							{{ alert.verdict_at ? `on ${formatDate(alert.verdict_at, dFormats.datetime)}` : "" }}
						</span>
					</div>
					<div v-else class="flex flex-col gap-3">
						<n-radio-group v-model:value="verdict">
							<n-radio-button value="TRUE_POSITIVE">True positive</n-radio-button>
							<n-radio-button value="FALSE_POSITIVE">False positive</n-radio-button>
						</n-radio-group>
						<template v-if="verdict === 'FALSE_POSITIVE'">
							<n-select v-model:value="reason" :options="FALSE_POSITIVE_REASONS" placeholder="Why" class="max-w-xs" />
							<n-checkbox v-model:checked="suppress">
								Suppress the rules behind this alert for this entity for 30 days
							</n-checkbox>
						</template>
						<n-input v-model:value="note" type="textarea" placeholder="Note (optional)" :autosize="{ minRows: 2 }" />
						<div>
							<n-button type="primary" :disabled="!canSubmit" :loading="submitting" @click="submit">Save verdict</n-button>
						</div>
					</div>
				</section>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaAlert, UbaAlertUpdate, UbaSignal } from "@/types/uba"
import { NButton, NCheckbox, NInput, NRadioButton, NRadioGroup, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import { FALSE_POSITIVE_REASONS, riskLabel, riskTagType } from "./utils"

const { customerCode, alertId } = defineProps<{ customerCode: string; alertId: string }>()
const emit = defineEmits<{ openEntity: [entityKey: string]; changed: [] }>()

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
