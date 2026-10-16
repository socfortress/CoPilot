<template>
	<div
		class="bg-secondary border-default flex flex-col gap-2 rounded-md border border-l-4 px-3 py-2 text-xs"
		:class="toneClass"
		data-testid="talon-approval-card"
		:data-approval-id="approvalId"
		:data-state="action?.state ?? 'loading'"
		:data-talon-status="action?.talon_status ?? ''"
	>
		<div class="flex flex-wrap items-center gap-2">
			<Icon name="carbon:user-certification" :size="14" />
			<span class="text-sm font-semibold" data-testid="talon-approval-title">
				{{ action ? actionLabel(action.action) : "Action proposal" }}
			</span>
			<span class="text-tertiary">proposed by Talon, decided in CoPilot</span>
			<span class="grow" />
			<n-tag v-if="action" size="small" :bordered="false" :type="tagType" data-testid="talon-approval-status">
				{{ stateLabel(action) }}
			</n-tag>
		</div>

		<div v-if="!action && loading" class="text-tertiary" data-testid="talon-approval-loading">
			Reading the proposal...
		</div>
		<div v-if="loadError" class="text-error" data-testid="talon-approval-load-error">{{ loadError }}</div>

		<template v-if="action">
			<n-alert
				v-for="warning of warnings"
				:key="warning.flag"
				:type="warning.severity"
				:bordered="false"
				class="text-xs"
				data-testid="talon-approval-provenance"
				:data-flag="warning.flag"
			>
				{{ warning.text }}
			</n-alert>

			<dl class="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
				<dt class="text-tertiary">Customer</dt>
				<dd data-testid="talon-approval-customer">{{ action.customer_code }}</dd>

				<dt class="text-tertiary">Target</dt>
				<dd data-testid="talon-approval-target">
					<template v-if="alertId !== null">
						<RouterLink
							:to="{ name: 'IncidentManagement-Alert', params: { id: String(alertId) } }"
							class="text-primary underline"
							data-testid="talon-approval-alert-link"
						>
							Alert #{{ alertId }}
						</RouterLink>
					</template>
					<template v-else-if="host">
						<span class="font-mono font-semibold" data-testid="talon-approval-hostname">
							{{ host.hostname }}
						</span>
						<span class="text-secondary" data-testid="talon-approval-agent">
							· agent {{ host.agentId }}
						</span>
						<span v-if="host.client" class="text-tertiary font-mono">· {{ host.client }}</span>
					</template>
					<span v-else class="text-tertiary">not shown</span>
				</dd>

				<template v-for="arg of args" :key="arg.key">
					<dt class="text-tertiary font-mono">{{ arg.key }}</dt>
					<dd v-if="arg.key === 'comment'" data-testid="talon-approval-comment">
						<!-- The comment raw, as it will be posted; links highlighted, never clickable. -->
						<div class="bg-default rounded p-1.5 font-mono break-words whitespace-pre-wrap">
							<template v-for="(segment, index) of arg.segments" :key="index">
								<span
									v-if="segment.link"
									class="rounded-sm bg-[rgba(var(--warning-color-rgb)/0.18)] px-0.5 underline decoration-dotted"
									data-testid="talon-approval-comment-link"
								>
									{{ segment.text }}
								</span>
								<template v-else>{{ segment.text }}</template>
							</template>
						</div>
						<div v-if="action.links" class="text-warning mt-1" data-testid="talon-approval-links-note">
							This comment holds links. They are shown, not opened: check them before approving.
						</div>
					</dd>
					<dd v-else class="font-mono break-all" :data-testid="`talon-approval-arg-${arg.key}`">
						{{ arg.text }}
					</dd>
				</template>
			</dl>

			<div class="flex flex-col gap-0.5" data-testid="talon-approval-reason">
				<span class="text-tertiary">The model's reason (untrusted: written by the model, not checked)</span>
				<!-- Plain text: never Markdown or HTML. -->
				<p class="text-secondary break-words whitespace-pre-wrap" data-testid="talon-approval-reason-text">
					{{ action.reason || "none given" }}
				</p>
			</div>

			<div class="text-tertiary flex flex-wrap gap-x-3 gap-y-0.5">
				<span data-testid="talon-approval-requester">Requested by {{ requester }}</span>
				<span v-if="createdAt">{{ formatDate(createdAt, dFormats.datetime) }}</span>
				<span v-if="countdown" data-testid="talon-approval-expiry">Expires in {{ countdown }}</span>
				<span v-else-if="action.state === 'pending'" data-testid="talon-approval-expiry">
					Expired {{ expiresAt ? formatDate(expiresAt, dFormats.datetime) : "" }}
				</span>
			</div>

			<div v-if="decisionLine" class="text-secondary" data-testid="talon-approval-decision">
				{{ decisionLine }}
			</div>
			<div v-if="resultText" class="text-secondary" data-testid="talon-approval-result">
				Result: {{ resultText }}
			</div>
			<div v-if="reasonText" class="text-tertiary" data-testid="talon-approval-state-reason">
				{{ reasonText }}
			</div>
			<div v-if="reportText" class="text-tertiary" data-testid="talon-approval-reported">{{ reportText }}</div>
		</template>

		<div v-if="decisionNote" class="text-warning" data-testid="talon-approval-note">{{ decisionNote }}</div>
		<div v-if="decisionError" class="text-error" data-testid="talon-approval-error">{{ decisionError }}</div>

		<div v-if="action && (action.can_decide || withdrawable)" class="flex flex-wrap items-center gap-2">
			<template v-if="action.can_decide">
				<n-button
					size="small"
					type="primary"
					:disabled="busy"
					:loading="busy && pendingKind === 'approve'"
					data-testid="talon-approval-approve"
					@click="askApprove()"
				>
					Approve
				</n-button>
				<n-button
					size="small"
					secondary
					:disabled="busy"
					:loading="busy && pendingKind === 'deny'"
					data-testid="talon-approval-deny"
					@click="decide('deny')"
				>
					Deny
				</n-button>
			</template>
			<n-button
				v-if="withdrawable"
				size="small"
				tertiary
				:disabled="busy"
				:loading="busy && pendingKind === 'withdraw'"
				data-testid="talon-approval-withdraw"
				@click="decide('withdraw')"
			>
				Withdraw
			</n-button>
			<span v-if="busy && pendingKind === 'approve'" class="text-tertiary">
				Approving and running it in CoPilot...
			</span>
		</div>

		<n-modal
			v-model:show="confirming"
			preset="card"
			:title="confirmTitle"
			:style="{ maxWidth: 'min(480px, 94vw)' }"
			:mask-closable="!busy"
			:closable="!busy"
			segmented
			data-testid="talon-approval-confirm"
		>
			<div class="flex flex-col gap-2 text-sm" data-testid="talon-approval-confirm-text">
				<p>
					{{ action?.action === "release_host" ? "Release" : "Quarantine" }}
					<strong class="font-mono">{{ host?.hostname }}</strong>
					(agent {{ host?.agentId }}) of customer
					<strong>{{ action?.customer_code }}</strong>
					?
				</p>
				<p class="text-secondary text-xs">
					{{
						action?.action === "release_host"
							? "Velociraptor gives the host its network connections back."
							: "Velociraptor cuts the host off the network but for its connection to Velociraptor."
					}}
					CoPilot runs it now, as you.
				</p>
			</div>
			<template #footer>
				<div class="flex justify-end gap-2">
					<n-button :disabled="busy" data-testid="talon-approval-confirm-cancel" @click="confirming = false">
						Cancel
					</n-button>
					<n-button
						type="warning"
						:disabled="busy"
						:loading="busy"
						data-testid="talon-approval-confirm-run"
						@click="confirmApprove()"
					>
						{{ action?.action === "release_host" ? "Release" : "Quarantine" }}
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
// An action proposal's approval card (plan M5-11b; talon-analyst SPEC §5.3 M5-11, §9.5).
//
// Everything shown comes from CoPilot's `GET /api/talon/actions/{id}`, which reads the record back
// from talon-analyst as the caller: never from the chat stream (`tool-input-available` is the
// model's own arguments, shown in the tool row, apart from this card). The model's reason and a
// comment are text: the reason labelled untrusted, a comment raw with its links highlighted and
// never clickable. Approve and Deny only when CoPilot says the caller may decide it; Withdraw for
// its requester while it is pending; a host action asks first, naming the host and the customer.
// The card reads the record again every `TALON_APPROVAL_POLL_MS` until nothing more can change.
import type { TalonAction } from "@/types/talonActions"
import axios from "axios"
import { NAlert, NButton, NModal, NTag } from "naive-ui"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import { TALON_V2_FAILED } from "@/api/talonV2Parser"
import Icon from "@/components/common/Icon.vue"
import { noteApprovalsChanged } from "@/composables/useTalonApprovals"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import {
	actionLabel,
	forgetAction,
	isHostAction,
	isSettled,
	isWithdrawable,
	linkSegments,
	parseUtc,
	provenanceWarnings,
	rememberAction,
	stateLabel,
	stateTone,
	TALON_APPROVAL_POLL_MS,
	timeLeft
} from "./approvals"

const { approvalId } = defineProps<{ approvalId: string }>()

const emit = defineEmits<{
	/** The proposal's state (CoPilot's or talon-analyst's) moved. */
	(e: "changed", value: TalonAction): void
}>()

type DecisionKind = "approve" | "deny" | "withdraw"

const dFormats = useSettingsStore().dateFormat

const action = ref<TalonAction | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const busy = ref(false)
const pendingKind = ref<DecisionKind | null>(null)
const decisionError = ref<string | null>(null)
const decisionNote = ref<string | null>(null)
const confirming = ref(false)
const now = ref(Date.now())

let controller: AbortController | null = null
let pollTimer: ReturnType<typeof setTimeout> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null
/** Bumped by every record taken: a read started before a decision's answer is dropped. */
let version = 0
let gone = false
let unmounted = false

function errorOf(err: unknown): { status: number | null; detail: string } {
	if (axios.isAxiosError(err)) {
		return { status: err.response?.status ?? null, detail: refusalDetail(err.response?.data) }
	}
	return { status: null, detail: TALON_V2_FAILED }
}

/** CoPilot's answer carries the record: anything else is no answer. */
function recordOf(data: unknown): TalonAction {
	const next = (data as { action?: unknown } | null)?.action as TalonAction | undefined
	if (!next || typeof next !== "object" || next.id !== approvalId || typeof next.state !== "string") {
		throw new Error("not the proposal's record")
	}
	return next
}

function take(next: TalonAction) {
	const before = action.value
	version += 1
	action.value = next
	rememberAction(next)
	if (before && (before.state !== next.state || before.talon_status !== next.talon_status)) {
		emit("changed", next)
		noteApprovalsChanged() // the Approvals badge follows
	}
}

function stopPolling() {
	if (pollTimer) clearTimeout(pollTimer)
	pollTimer = null
}

function schedule() {
	stopPolling()
	if (unmounted || gone || (action.value && isSettled(action.value))) return
	pollTimer = setTimeout(() => {
		pollTimer = null
		if (busy.value) schedule()
		else load()
	}, TALON_APPROVAL_POLL_MS)
}

async function load() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	const started = version
	try {
		const res = await Api.talonActions.get(approvalId, own.signal)
		if (own.signal.aborted || unmounted) return
		const next = recordOf(res.data)
		loadError.value = null
		if (started === version) take(next)
	} catch (err) {
		if (own.signal.aborted || unmounted || axios.isCancel(err)) return
		const { status, detail } = errorOf(err)
		loadError.value = detail
		if (status === 404) {
			gone = true
			forgetAction(approvalId)
		}
	} finally {
		if (controller === own) {
			controller = null
			loading.value = false
			schedule()
		}
	}
}

async function decide(kind: DecisionKind) {
	if (busy.value || !action.value) return
	busy.value = true
	pendingKind.value = kind
	decisionError.value = null
	decisionNote.value = null
	stopPolling()
	controller?.abort()
	controller = null
	let reread = false
	try {
		const call =
			kind === "approve"
				? Api.talonActions.approve
				: kind === "deny"
					? Api.talonActions.deny
					: Api.talonActions.withdraw
		const res = await call(approvalId)
		if (unmounted) return
		take(recordOf(res.data))
		// CoPilot answers 200 with `success: false` when it decided but the run didn't succeed.
		if (res.data.success === false && res.data.message) decisionNote.value = res.data.message
	} catch (err) {
		if (unmounted) return
		decisionError.value = errorOf(err).detail
		reread = true // what the record is now (another approver, an expiry...)
	} finally {
		busy.value = false
		pendingKind.value = null
		confirming.value = false
		if (!unmounted) {
			if (reread) load()
			else schedule()
		}
	}
}

function askApprove() {
	if (!action.value || busy.value) return
	if (isHostAction(action.value)) confirming.value = true
	else decide("approve")
}

function confirmApprove() {
	decide("approve")
}

// ── what the card shows ──────────────────────────────────────────────────────

function integer(value: unknown): number | null {
	return typeof value === "number" && Number.isSafeInteger(value) ? value : null
}

function asText(value: unknown): string {
	if (typeof value === "string") return value
	try {
		return JSON.stringify(value) ?? String(value)
	} catch {
		return String(value)
	}
}

const alertId = computed(() => {
	if (!action.value || isHostAction(action.value)) return null
	return integer(action.value.target?.alert_id)
})

const host = computed(() => {
	if (!action.value || !isHostAction(action.value)) return null
	const target = action.value.target ?? {}
	return {
		hostname: asText(target.hostname ?? ""),
		agentId: asText(target.agent_id ?? ""),
		client: typeof target.velociraptor_id === "string" ? target.velociraptor_id : null
	}
})

const args = computed(() =>
	Object.entries(action.value?.args ?? {}).map(([key, value]) => {
		const text = asText(value)
		return { key, text, segments: key === "comment" ? linkSegments(text) : [] }
	})
)

const warnings = computed(() => provenanceWarnings(action.value?.provenance))
const withdrawable = computed(() => !!action.value && isWithdrawable(action.value))
const requester = computed(() =>
	action.value?.is_requester ? "you" : `CoPilot user #${action.value?.requester_user_id ?? "?"}`
)
const createdAt = computed(() => parseUtc(action.value?.created_at))
const expiresAt = computed(() => parseUtc(action.value?.expires_at))
const countdown = computed(() => {
	if (!action.value || action.value.state !== "pending" || action.value.expired) return null
	return timeLeft(expiresAt.value, now.value)
})

const decisionLine = computed(() => {
	const a = action.value
	if (!a?.approver_username || !a.decision) return null
	const verb = a.decision === "deny" ? "Denied" : "Approved"
	const at = parseUtc(a.decided_at)
	return `${verb} by ${a.approver_username}${at ? ` on ${formatDate(at, dFormats.datetime)}` : ""}`
})
const resultText = computed(() => {
	const message = action.value?.execution_result?.message
	return typeof message === "string" && message ? message : null
})
const reasonText = computed(() => {
	const reason = action.value?.state_reason
	return reason && reason !== resultText.value ? reason : null
})
const reportText = computed(() => {
	const a = action.value
	if (!a || !["executed", "failed"].includes(a.state)) return null
	return a.outcome_reported ? "Reported to Talon." : "Not reported to Talon yet: CoPilot keeps trying."
})

const confirmTitle = computed(() =>
	action.value?.action === "release_host" ? "Release this host from quarantine?" : "Quarantine this host?"
)

const toneClass = computed(() => {
	switch (action.value ? stateTone(action.value) : "waiting") {
		case "waiting":
			return "border-l-warning"
		case "running":
			return "border-l-info"
		case "success":
			return "border-l-success"
		case "error":
			return "border-l-error"
		default:
			return "border-l-default"
	}
})

const tagType = computed(() => {
	switch (action.value ? stateTone(action.value) : "neutral") {
		case "waiting":
			return "warning"
		case "running":
			return "info"
		case "success":
			return "success"
		case "error":
			return "error"
		default:
			return "default"
	}
})

// The expiry countdown ticks only while the proposal waits.
watch(
	() => !!action.value && action.value.state === "pending" && !action.value.expired,
	ticking => {
		if (clockTimer) clearInterval(clockTimer)
		clockTimer = null
		if (ticking && !unmounted) clockTimer = setInterval(() => (now.value = Date.now()), 1000)
	}
)

onMounted(() => load())

// Nothing outlives the card: no read in flight, no poll, no clock.
onBeforeUnmount(() => {
	unmounted = true
	controller?.abort()
	stopPolling()
	if (clockTimer) clearInterval(clockTimer)
})
</script>
