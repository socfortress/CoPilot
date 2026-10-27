<template>
	<n-drawer
		:show="findingId !== null"
		:width="drawerWidth"
		placement="right"
		auto-focus
		data-testid="talon-ops-detail"
		@update:show="value => !value && emit('close')"
	>
		<n-drawer-content closable :native-scrollbar="false" title="Ops finding">
			<div v-if="loading" class="flex justify-center py-10" data-testid="talon-ops-detail-loading">
				<n-spin size="small" />
			</div>
			<OpsProblem v-else-if="problem" :state="problem" @retry="load()" />
			<div v-else-if="finding" class="flex flex-col gap-4" data-testid="talon-ops-detail-body">
				<div class="flex flex-col gap-2">
					<div class="flex flex-wrap items-center gap-2">
						<n-tag
							:type="severityInfo(finding.severity).tag as 'default'"
							size="small"
							:bordered="false"
							data-testid="talon-ops-detail-severity"
						>
							{{ severityInfo(finding.severity).label }}
						</n-tag>
						<span class="inline-flex items-center gap-1 text-sm" data-testid="talon-ops-detail-status">
							<Icon :name="statusInfo(finding.status).icon" :size="14" />
							{{ statusInfo(finding.status).label }}
							<template v-if="finding.status === 'muted' && finding.muted_until">
								until {{ formatTime(finding.muted_until) }}
							</template>
						</span>
					</div>
					<h3 class="text-base font-semibold" data-testid="talon-ops-detail-title">
						<bdi>{{ finding.title }}</bdi>
					</h3>
				</div>

				<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
					<dt class="text-secondary">Customer</dt>
					<dd data-testid="talon-ops-detail-customer">
						<bdi>{{ customerText(finding.customer_code) }}</bdi>
					</dd>
					<dt class="text-secondary">Job</dt>
					<dd>
						{{ jobLabel(finding.job, titles) }}
						<span class="text-tertiary">· {{ kindLabel(finding.kind) }}</span>
					</dd>
					<template v-if="finding.acted_by">
						<dt class="text-secondary">Last action by</dt>
						<dd>
							<bdi>{{ finding.acted_by }}</bdi>
							· {{ formatTime(finding.acted_at) }}
						</dd>
					</template>
				</dl>

				<nav
					v-if="links.length"
					aria-label="Open in CoPilot"
					class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
					data-testid="talon-ops-detail-links"
				>
					<span class="text-secondary text-xs">Open in CoPilot</span>
					<router-link
						v-for="link of links"
						:key="link.key"
						:to="link.to"
						class="text-primary inline-flex items-center gap-1 no-underline hover:underline"
						:data-testid="`talon-ops-detail-link-${link.key}`"
					>
						<Icon :name="link.icon" :size="12" />
						<bdi>{{ link.label }}</bdi>
					</router-link>
				</nav>

				<section aria-label="Why it matters" class="flex flex-col gap-2">
					<h4 class="text-secondary text-xs font-semibold uppercase">Why it matters</h4>
					<!-- A model's text: bound as text only (never v-html or Markdown), newlines kept. -->
					<p v-if="finding.why" class="text-sm whitespace-pre-wrap" data-testid="talon-ops-detail-why">
						<bdi>{{ finding.why }}</bdi>
					</p>
					<p v-else class="text-tertiary text-sm">Talon didn't explain this finding.</p>
					<h4 class="text-secondary text-xs font-semibold uppercase">What to do</h4>
					<p
						v-if="finding.recommendation"
						class="text-sm whitespace-pre-wrap"
						data-testid="talon-ops-detail-recommendation"
					>
						<bdi>{{ finding.recommendation }}</bdi>
					</p>
					<p v-else class="text-tertiary text-sm">No recommendation.</p>
					<p class="text-tertiary text-xs" data-testid="talon-ops-detail-explained">
						{{
							finding.explained
								? "Written by Talon's model from the evidence below: check it against the evidence."
								: "Talon's job's own hint: the model didn't explain this finding."
						}}
					</p>
				</section>

				<section aria-label="Evidence" class="flex flex-col gap-2">
					<div class="flex items-center justify-between gap-2">
						<h4 class="text-secondary text-xs font-semibold uppercase">Evidence</h4>
						<div class="flex items-center gap-3">
							<n-button
								v-if="finding.evidence && hasView && evidenceMode !== 'json'"
								text
								size="tiny"
								data-testid="talon-ops-detail-evidence-view-toggle"
								@click="evidenceMode = evidenceMode === 'view' ? 'list' : 'view'"
							>
								{{ evidenceMode === "view" ? "Show as a list" : "Show the summary" }}
							</n-button>
							<n-button
								v-if="finding.evidence"
								text
								size="tiny"
								data-testid="talon-ops-detail-evidence-toggle"
								@click="toggleJson()"
							>
								{{ evidenceMode === "json" ? (hasView ? "Hide JSON" : "Show as a list") : "Show JSON" }}
							</n-button>
						</div>
					</div>
					<p v-if="!finding.evidence" class="text-tertiary text-sm">
						{{ finding.evidence_truncated ? "The evidence was too large to show here." : "No evidence." }}
					</p>
					<pre
						v-else-if="evidenceMode === 'json'"
						class="bg-secondary max-h-80 overflow-auto rounded-md p-2 text-xs"
						data-testid="talon-ops-detail-evidence-json"
					>{{ evidenceJson(finding) }}</pre>
					<div v-else-if="evidenceMode === 'view' && hasView" data-testid="talon-ops-detail-evidence-view">
						<OpsEvidence :finding :is-admin :settings="settings[finding.job] ?? null" />
					</div>
					<dl
						v-else
						class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm"
						data-testid="talon-ops-detail-evidence"
					>
						<template v-for="row of evidenceRows(finding.evidence)" :key="row.key">
							<dt class="text-secondary font-mono text-xs leading-5">
								<bdi>{{ row.key }}</bdi>
							</dt>
							<dd class="break-all">
								<bdi v-if="row.text !== null" :title="row.title">{{ row.text }}</bdi>
								<pre v-else class="bg-secondary overflow-auto rounded p-1 text-xs">{{ row.json }}</pre>
							</dd>
						</template>
					</dl>
				</section>

				<section
					v-if="finding.artifact"
					aria-label="Artifact"
					class="flex flex-col gap-2"
					data-testid="talon-ops-detail-artifact"
				>
					<div class="flex items-center justify-between gap-2">
						<h4 class="text-secondary text-xs font-semibold uppercase">
							Artifact
							<code class="normal-case">{{ finding.artifact.type }}</code>
						</h4>
						<n-button size="tiny" secondary data-testid="talon-ops-detail-copy" @click="copyArtifact()">
							<template #icon><Icon name="carbon:copy" :size="12" /></template>
							{{ copied ? "Copied" : "Copy" }}
						</n-button>
					</div>
					<pre
						class="bg-secondary max-h-80 overflow-auto rounded-md p-2 text-xs"
						data-testid="talon-ops-detail-artifact-body"
					>{{ finding.artifact.body }}</pre>
					<p class="text-tertiary text-xs">
						Built by Talon's job from a template. Review it before you use it.
					</p>
				</section>

				<OpsFindingHistory :finding :is-admin />

				<n-alert v-if="actionFailure" type="error" :bordered="false" data-testid="talon-ops-action-error">
					<bdi>{{ actionFailure }}</bdi>
				</n-alert>

				<section
					aria-label="Actions"
					class="border-default flex flex-wrap items-end gap-2 border-t pt-3"
					data-testid="talon-ops-actions"
				>
					<n-button
						v-if="canAcknowledge(finding.status)"
						size="small"
						type="primary"
						secondary
						:loading="acting === 'acknowledge'"
						:disabled="acting !== null"
						data-testid="talon-ops-acknowledge"
						@click="act('acknowledge')"
					>
						Acknowledge
					</n-button>
					<n-button
						v-if="canReopen(finding.status)"
						size="small"
						secondary
						:loading="acting === 'reopen'"
						:disabled="acting !== null"
						data-testid="talon-ops-reopen"
						@click="act('reopen')"
					>
						Reopen
					</n-button>
					<template v-if="canMute(finding.status)">
						<label class="flex flex-col gap-1">
							<span class="text-secondary text-xs">Mute until</span>
							<n-date-picker
								v-model:value="muteUntil"
								type="datetime"
								size="small"
								:is-date-disabled="(ts: number) => !isMuteDay(ts)"
								data-testid="talon-ops-mute-until"
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
								:data-testid="`talon-ops-mute-preset-${days}`"
								@click="muteUntil = muteUntilIn(days)"
							>
								{{ days === 1 ? "1 day" : `${days} days` }}
							</n-button>
						</div>
						<n-button
							size="small"
							secondary
							:loading="acting === 'mute'"
							:disabled="acting !== null || !isValidMuteUntil(muteUntil)"
							data-testid="talon-ops-mute"
							@click="act('mute')"
						>
							Mute
						</n-button>
					</template>
					<p
						v-if="finding.status === 'resolved'"
						class="text-tertiary text-xs"
						data-testid="talon-ops-resolved-note"
					>
						A resolved finding opens again when a run finds it again.
					</p>
				</section>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
// One ops finding, in a side drawer: severity, status, the customer and job, the times; Talon's
// explanation and recommendation as plain text (a model wrote them: never v-html, never Markdown);
// links out to the agent(s), the customer, index management or the alerts (`findingLinks`: from the
// finding's fields and evidence ids only); the evidence as its job's view (`evidence/`: units, tables, bars,
// `disk_forecast`'s chart), with the key-value list and JSON as fallbacks; any artifact in a copyable
// code block; its history (`OpsFindingHistory`: its times and its job's runs since first seen); and the actions
// its status allows (acknowledge, mute until a picked time or for 1, 7 or 30 days, reopen). The actor
// is the signed-in user, which CoPilot adds; the finding's stored customer is sent back so a finding
// that moved is refused.
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsFinding } from "@/types/talonOps"
import { useWindowSize } from "@vueuse/core"
import { NAlert, NButton, NDatePicker, NDrawer, NDrawerContent, NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { RouterLink } from "vue-router"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { formatTime } from "../health/health"
import { viewKind } from "./evidence/evidence"
import OpsEvidence from "./evidence/OpsEvidence.vue"
import {
	canAcknowledge,
	canMute,
	canReopen,
	customerText,
	defaultMuteUntil,
	evidenceJson,
	evidenceRows,
	findingLinks,
	isMuteDay,
	isValidMuteUntil,
	jobLabel,
	kindLabel,
	MUTE_PRESETS,
	muteUntilIn,
	problemState,
	severityInfo,
	statusInfo
} from "./ops"
import OpsFindingHistory from "./OpsFindingHistory.vue"
import OpsProblem from "./OpsProblem.vue"

const {
	findingId,
	customerCode = null,
	titles = {},
	isAdmin = false,
	settings = {}
} = defineProps<{
	findingId: number | null
	customerCode?: string | null
	titles?: Record<string, string | null>
	isAdmin?: boolean
	/** Each job's thresholds (`TalonOpsJob.settings`): `disk_forecast`'s projection reads `horizon_days`. */
	settings?: Record<string, Record<string, unknown>>
}>()
const emit = defineEmits<{
	(e: "close"): void
	(e: "changed", finding: TalonOpsFinding): void
}>()

const { width } = useWindowSize()
const drawerWidth = computed(() => Math.min(720, Math.round(width.value * 0.94)))

const finding = ref<TalonOpsFinding | null>(null)
const failure = ref<TalonOpsFailure | null>(null)
const loading = ref(false)
/** The evidence as its job's view (when it parses), the generic list, or JSON. */
const evidenceMode = ref<"view" | "list" | "json">("view")
const copied = ref(false)
const acting = ref<"acknowledge" | "mute" | "reopen" | null>(null)
const actionFailure = ref<string | null>(null)
const muteUntil = ref<number | null>(defaultMuteUntil())
let controller: AbortController | null = null

const problem = computed(() => problemState(failure.value))

/** Whether the finding's evidence has a view of its job's (`viewKind`); otherwise the list. */
const hasView = computed(() => (finding.value ? viewKind(finding.value) !== null : false))
/** Where JSON goes back to: the view when there is one. */
function toggleJson() {
	evidenceMode.value = evidenceMode.value === "json" ? (hasView.value ? "view" : "list") : "json"
}

/** Where the finding leads: built by code from its fields and evidence ids, never from the model's text. */
const links = computed(() => (finding.value ? findingLinks(finding.value) : []))

async function load() {
	controller?.abort()
	finding.value = null
	failure.value = null
	actionFailure.value = null
	evidenceMode.value = "view"
	copied.value = false
	muteUntil.value = defaultMuteUntil()
	if (findingId === null) return
	const own = new AbortController()
	controller = own
	loading.value = true
	try {
		const { data } = await Api.talonOps.getFinding(findingId, customerCode, own.signal)
		if (controller !== own) return
		finding.value = data.finding
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		failure.value = opsFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

async function act(action: "acknowledge" | "mute" | "reopen") {
	const current = finding.value
	if (!current || acting.value) return
	if (action === "mute" && !isValidMuteUntil(muteUntil.value)) return
	acting.value = action
	actionFailure.value = null
	try {
		const stored = current.customer_code
		const { data } =
			action === "acknowledge"
				? await Api.talonOps.acknowledge(current.id, stored)
				: action === "reopen"
					? await Api.talonOps.reopen(current.id, stored)
					: await Api.talonOps.mute(current.id, new Date(muteUntil.value as number).toISOString(), stored)
		finding.value = data.finding
		emit("changed", data.finding)
	} catch (err) {
		const why = opsFailure(err)
		actionFailure.value =
			why.code === "not_found"
				? "Talon no longer has this finding, or it isn't one of your customers'."
				: why.detail
	} finally {
		acting.value = null
	}
}

async function copyArtifact() {
	if (!finding.value?.artifact) return
	try {
		await navigator.clipboard.writeText(finding.value.artifact.body)
		copied.value = true
		setTimeout(() => (copied.value = false), 2000)
	} catch {
		copied.value = false
	}
}

watch(() => [findingId, customerCode], load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
