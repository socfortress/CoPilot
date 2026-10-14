<template>
	<n-modal
		v-model:show="show"
		preset="card"
		:title="`Roll back UBA — ${customerCode}`"
		:style="{ maxWidth: 'min(720px, 94vw)' }"
		segmented
		:mask-closable="!running"
		:closable="!running"
		data-testid="uba-rollback-dialog"
	>
		<n-spin v-if="loading" class="min-h-24" show />
		<UbaError v-else-if="error" :error />

		<!-- The result of a rollback, just run or opened from the history -->
		<div v-else-if="report" class="flex flex-col gap-4" data-testid="uba-rollback-report">
			<div class="flex flex-wrap items-center gap-2 text-sm">
				<n-tag size="small" :type="reportType" :bordered="false">{{ report.status }}</n-tag>
				<span>{{ report.message }}</span>
			</div>
			<p class="text-tertiary m-0 text-xs">
				{{ formatDate(report.started_at, dFormats.datetime) }}
				<template v-if="report.actor_username">by {{ report.actor_username }}</template>
			</p>

			<section v-if="report.verification.length" class="flex flex-col gap-1.5">
				<span :class="SECTION_LABEL">Checks</span>
				<ul class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
					<li
						v-for="c of report.verification"
						:key="c.check"
						class="flex items-start gap-2"
						data-testid="uba-rollback-check"
					>
						<Icon :name="checkIcon(c.ok)" :size="15" :class="checkClass(c.ok)" class="mt-0.5 shrink-0" />
						<span class="min-w-0">
							<span class="font-medium">{{ c.check }}</span>
							<span v-if="c.detail" class="text-secondary">: {{ c.detail }}</span>
						</span>
					</li>
				</ul>
			</section>

			<section class="flex flex-col gap-1.5">
				<span :class="SECTION_LABEL">Steps</span>
				<ul class="m-0 flex list-none flex-col gap-1 p-0 text-xs">
					<li v-for="(s, i) of report.steps" :key="i" class="flex flex-wrap items-center gap-2">
						<n-tag size="tiny" :bordered="false" :type="stepType(s.status)">{{ s.status }}</n-tag>
						<span class="font-mono">{{ s.step }}</span>
						<span v-if="s.detail" class="text-tertiary">{{ s.detail }}</span>
					</li>
				</ul>
			</section>
		</div>

		<!-- The preview -->
		<div v-else-if="plan" class="flex flex-col gap-4" data-testid="uba-rollback-plan">
			<p class="text-secondary m-0 text-sm">
				Removes this customer's UBA routing from Graylog, then deactivates the customer in UBA. Routing is
				disconnected first, so nothing is sent to UBA from then on. The customer's own streams, their other
				pipelines and Graylog's event definitions are not touched, and both UBA's and CoPilot's history is kept.
				Setting UBA up again recreates everything.
			</p>
			<n-alert v-if="plan.uba_problem" type="warning" :bordered="false" class="text-sm">
				UBA could not be asked ({{ plan.uba_problem }}). The Graylog side is rolled back anyway; roll back again
				once UBA answers to deactivate the customer there.
			</n-alert>
			<n-alert v-if="!plan.remove.length" type="info" :bordered="false" class="text-sm">
				UBA is not set up for this customer: there is nothing to roll back.
			</n-alert>

			<section v-if="plan.remove.length" class="flex flex-col gap-1.5">
				<span :class="SECTION_LABEL">Removed, in this order</span>
				<ol class="m-0 flex flex-col gap-1 pl-5 text-sm" data-testid="uba-rollback-remove">
					<li v-for="item of plan.remove" :key="`${item.kind}:${item.id}`">
						<span class="text-secondary">{{ kindLabel(item.kind) }}</span>
						<span class="font-mono">{{ item.title }}</span>
						<span v-if="item.detail" class="text-tertiary text-xs">— {{ item.detail }}</span>
						<n-tag
							v-if="!item.recorded && item.kind !== 'uba_tenant'"
							size="tiny"
							:bordered="false"
							class="ml-1"
						>
							found by name
						</n-tag>
					</li>
				</ol>
			</section>

			<section v-if="plan.keep.length" class="flex flex-col gap-1.5">
				<span :class="SECTION_LABEL">Kept</span>
				<ul class="m-0 flex flex-col gap-1 pl-5 text-sm">
					<li v-for="item of plan.keep" :key="`${item.kind}:${item.id}`">
						<span class="text-secondary">{{ kindLabel(item.kind) }}</span>
						<span class="font-mono">{{ item.title }}</span>
						<span class="text-tertiary text-xs">— {{ item.detail }}</span>
					</li>
				</ul>
			</section>

			<n-alert v-if="plan.conflicts.length" type="warning" :bordered="false" title="Left alone: review by hand">
				<ul class="m-0 flex flex-col gap-1 pl-5 text-sm" data-testid="uba-rollback-conflicts">
					<li v-for="item of plan.conflicts" :key="`${item.kind}:${item.id}`">
						<span class="font-mono">{{ item.title }}</span>
						{{ item.detail }}
					</li>
				</ul>
			</n-alert>

			<section v-if="plan.source_streams.length" class="flex flex-col gap-1.5">
				<span :class="SECTION_LABEL">Keep running</span>
				<ul class="m-0 flex flex-col gap-1 pl-5 text-sm">
					<li v-for="s of plan.source_streams" :key="s.id">
						<span class="font-medium">{{ s.title || s.id }}</span>
						<span class="text-tertiary text-xs">
							—
							{{
								keptPipelines(s).length
									? `pipelines: ${keptPipelines(s).join(", ")}`
									: "no other pipelines"
							}}
						</span>
					</li>
				</ul>
			</section>

			<n-form-item
				v-if="plan.remove.length"
				:label="`Type ${customerCode} to confirm`"
				:show-feedback="false"
				class="max-w-sm"
			>
				<n-input v-model:value="confirmText" :placeholder="customerCode" data-testid="uba-rollback-confirm" />
			</n-form-item>
		</div>

		<template #footer>
			<div class="flex flex-wrap justify-end gap-2">
				<n-button :disabled="running" @click="show = false">Close</n-button>
				<n-button v-if="report && report.status !== 'completed'" :disabled="running" @click="loadPlan">
					Review and run again
				</n-button>
				<n-button
					v-if="!report && plan?.remove.length"
					type="error"
					:loading="running"
					:disabled="confirmText.trim() !== customerCode"
					data-testid="uba-rollback-run"
					@click="run"
				>
					Roll back UBA
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaRollbackPlan, UbaRollbackReport, UbaRollbackSourceStream } from "@/types/uba"
import { NAlert, NButton, NFormItem, NInput, NModal, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"

const { customerCode, reportId = null } = defineProps<{
	customerCode: string
	/** Open this past rollback's report instead of a new preview. */
	reportId?: number | null
}>()
const emit = defineEmits<{ done: [report: UbaRollbackReport] }>()
const show = defineModel<boolean>("show", { required: true })

const KIND_LABELS: Record<string, string> = {
	routing_pipeline: "Routing pipeline",
	routing_rule: "Routing rule",
	output: "Output to UBA",
	feed_stream: "Feed stream",
	alerts_stream: "Alerts stream",
	alerts_input: "Shared alerts input",
	wazuh_rules: "Wazuh rules",
	uba_tenant: "UBA"
}

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const running = ref(false)
const error = ref<ApiError | null>(null)
const plan = ref<UbaRollbackPlan | null>(null)
const report = ref<UbaRollbackReport | null>(null)
const confirmText = ref("")

const reportType = computed(() =>
	report.value?.status === "completed" ? "success" : report.value?.status === "running" ? "info" : "warning"
)

const removedPipelines = computed(
	() => new Set((plan.value?.remove ?? []).filter(i => i.kind === "routing_pipeline").map(i => i.title))
)

function kindLabel(kind: string) {
	return KIND_LABELS[kind] ?? kind
}

function keptPipelines(stream: UbaRollbackSourceStream) {
	return stream.pipelines.filter(p => !removedPipelines.value.has(p))
}

function stepType(status: string) {
	if (status === "failed") return "error"
	if (status === "conflict") return "warning"
	if (["removed", "disconnected", "detached", "deactivated"].includes(status)) return "success"
	return "default"
}

function checkIcon(ok: boolean | null) {
	return ok === true ? "carbon:checkmark-filled" : ok === false ? "carbon:warning-filled" : "carbon:help"
}

function checkClass(ok: boolean | null) {
	return ok === true ? "text-success" : ok === false ? "text-error" : "text-tertiary"
}

function loadPlan() {
	loading.value = true
	error.value = null
	report.value = null
	plan.value = null
	confirmText.value = ""
	Api.uba
		.getRollbackPlan(customerCode)
		.then(res => {
			plan.value = res.data
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function loadReport(id: number) {
	loading.value = true
	error.value = null
	plan.value = null
	Api.uba
		.getRollback(customerCode, id)
		.then(res => {
			report.value = res.data.report
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function run() {
	running.value = true
	Api.uba
		.rollBack(customerCode)
		.then(res => {
			report.value = res.data.report
			if (res.data.report.status === "completed") message.success("UBA is rolled back for this customer")
			else message.warning(res.data.report.message || "The rollback did not finish: run it again")
			emit("done", res.data.report)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Rolling UBA back failed")
		})
		.finally(() => {
			running.value = false
		})
}

watch(
	show,
	open => {
		if (!open) return
		if (reportId) loadReport(reportId)
		else loadPlan()
	},
	{ immediate: true }
)
</script>
