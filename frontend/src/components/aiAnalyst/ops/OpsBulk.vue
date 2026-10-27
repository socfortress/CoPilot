<template>
	<section
		v-if="selected.length || report"
		class="border-default flex flex-col gap-2 rounded-md border p-2"
		aria-label="Act on the selected findings"
		data-testid="talon-ops-bulk"
	>
		<div v-if="selected.length" class="flex flex-wrap items-end gap-2">
			<span class="text-sm" data-testid="talon-ops-bulk-count">{{ selected.length }} selected</span>
			<n-button
				size="small"
				type="primary"
				secondary
				:loading="acting === 'acknowledge'"
				:disabled="acting !== null || overCap || !eligible.acknowledge.length"
				data-testid="talon-ops-bulk-acknowledge"
				@click="run('acknowledge')"
			>
				Acknowledge {{ eligible.acknowledge.length }}
			</n-button>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Mute until</span>
				<n-date-picker
					v-model:value="muteUntil"
					type="datetime"
					size="small"
					:is-date-disabled="(ts: number) => !isMuteDay(ts)"
					data-testid="talon-ops-bulk-mute-until"
				/>
			</label>
			<div class="flex gap-1" role="group" aria-label="Mute for">
				<n-button
					v-for="days of MUTE_PRESETS"
					:key="days"
					size="small"
					tertiary
					:disabled="acting !== null"
					:title="`Mute until ${days === 1 ? 'this time tomorrow' : `${days} days from now`}`"
					:data-testid="`talon-ops-bulk-mute-preset-${days}`"
					@click="muteUntil = muteUntilIn(days)"
				>
					{{ days === 1 ? "1 day" : `${days} days` }}
				</n-button>
			</div>
			<n-button
				size="small"
				secondary
				:loading="acting === 'mute'"
				:disabled="acting !== null || overCap || !eligible.mute.length || !isValidMuteUntil(muteUntil)"
				data-testid="talon-ops-bulk-mute"
				@click="run('mute')"
			>
				Mute {{ eligible.mute.length }}
			</n-button>
			<n-button
				size="small"
				text
				:disabled="acting !== null"
				data-testid="talon-ops-bulk-clear"
				@click="emit('clear')"
			>
				Clear selection
			</n-button>
		</div>
		<p v-if="overCap" class="text-warning text-xs" data-testid="talon-ops-bulk-cap">
			Select at most {{ BULK_MAX }} findings at a time.
		</p>
		<n-alert
			v-if="report"
			:type="report.failed.length ? 'warning' : 'success'"
			:bordered="false"
			closable
			data-testid="talon-ops-bulk-report"
			@close="report = null"
		>
			<p data-testid="talon-ops-bulk-summary">{{ report.text }}</p>
			<ul v-if="report.failed.length" class="mt-1 list-disc pl-5 text-xs" data-testid="talon-ops-bulk-failures">
				<li v-for="failure of report.failed" :key="failure.finding.id">
					<bdi>{{ failure.finding.title }}</bdi>
					:
					<bdi>{{ failure.detail }}</bdi>
				</li>
			</ul>
		</n-alert>
	</section>
</template>

<script setup lang="ts">
// Acknowledge or mute the selected findings: at most 50, only the ones whose status allows the action
// (as the drawer's buttons), one request each through CoPilot's per-finding route (each audited, the
// actor the signed-in user, the stored customer sent back), three at a time. Then "N acknowledged,
// N failed" with the failures by title, and one refresh of the table and the strip (`done`).
import type { BulkAction, BulkFailure } from "./ops"
import type { TalonOpsFinding } from "@/types/talonOps"
import { NAlert, NButton, NDatePicker } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import {
	allowsBulk,
	BULK_MAX,
	bulkSummary,
	defaultMuteUntil,
	isMuteDay,
	isValidMuteUntil,
	MUTE_PRESETS,
	muteUntilIn,
	runBulk
} from "./ops"

const { selected } = defineProps<{ selected: TalonOpsFinding[] }>()
const emit = defineEmits<{ (e: "done"): void; (e: "clear"): void }>()

const acting = ref<BulkAction | null>(null)
const muteUntil = ref<number | null>(defaultMuteUntil())
const report = ref<{ text: string; failed: BulkFailure[] } | null>(null)

const overCap = computed(() => selected.length > BULK_MAX)
const eligible = computed(() => ({
	acknowledge: selected.filter(f => allowsBulk("acknowledge", f.status)),
	mute: selected.filter(f => allowsBulk("mute", f.status))
}))

function failureText(err: unknown): string {
	const why = opsFailure(err)
	return why.code === "not_found"
		? "Talon no longer has this finding, or it isn't one of your customers'."
		: why.detail
}

async function run(action: BulkAction) {
	if (acting.value || overCap.value) return
	const findings = eligible.value[action]
	if (!findings.length || findings.length > BULK_MAX) return
	if (action === "mute" && !isValidMuteUntil(muteUntil.value)) return
	const until = action === "mute" ? new Date(muteUntil.value as number).toISOString() : ""
	acting.value = action
	report.value = null
	try {
		const outcome = await runBulk(
			findings,
			finding =>
				action === "acknowledge"
					? Api.talonOps.acknowledge(finding.id, finding.customer_code)
					: Api.talonOps.mute(finding.id, until, finding.customer_code),
			failureText
		)
		report.value = { text: bulkSummary(action, outcome), failed: outcome.failed }
	} finally {
		acting.value = null
		emit("done")
	}
}
</script>
