<template>
	<div
		class="bg-secondary border-default flex flex-col gap-2 rounded-md border border-l-4 px-3 py-2 text-xs"
		:class="toneClass"
		data-testid="talon-approval-card"
		:data-approval-id="approvalId"
		:data-state="action?.state ?? (entry.gone ? 'gone' : 'loading')"
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

		<div v-if="!action && entry.loading" class="text-tertiary" data-testid="talon-approval-loading">
			Reading the proposal...
		</div>
		<div v-if="entry.loadError" class="text-error" data-testid="talon-approval-load-error">
			<TalonUntrusted :text="entry.loadError" />
		</div>

		<template v-if="action">
			<n-alert
				v-if="hiddenChars"
				type="error"
				:bordered="false"
				class="text-xs"
				data-testid="talon-approval-hidden-chars"
			>
				{{ HIDDEN_CHARS_WARNING }}
			</n-alert>
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
				<dd data-testid="talon-approval-customer"><TalonUntrusted :text="action.customer_code" /></dd>

				<dt class="text-tertiary">Target</dt>
				<dd data-testid="talon-approval-target">
					<RouterLink
						v-if="alertId !== null"
						:to="{ name: 'IncidentManagement-Alert', params: { id: String(alertId) } }"
						class="text-primary underline"
						data-testid="talon-approval-alert-link"
					>
						Alert #{{ alertId }}
					</RouterLink>
					<template v-else-if="host">
						<span class="font-mono font-semibold" data-testid="talon-approval-hostname">
							<TalonUntrusted :text="host.hostname" />
						</span>
						<span class="text-secondary" data-testid="talon-approval-agent">
							· agent
							<TalonUntrusted :text="host.agentId" />
						</span>
						<span v-if="host.client" class="text-tertiary font-mono" data-testid="talon-approval-client">
							·
							<TalonUntrusted :text="host.client" />
						</span>
						<span v-if="host.os" class="text-tertiary" data-testid="talon-approval-os">
							·
							<TalonUntrusted :text="host.os" />
						</span>
					</template>
					<span v-else class="text-tertiary">not shown</span>
				</dd>

				<template v-for="arg of args" :key="arg.key">
					<dt class="text-tertiary font-mono"><TalonUntrusted :text="arg.key" /></dt>
					<dd class="font-mono break-all" :data-testid="`talon-approval-arg-${arg.key}`">
						<span v-if="shownBelow.has(arg.key)" class="text-tertiary font-sans">shown below</span>
						<TalonUntrusted v-else :text="arg.text" />
					</dd>
				</template>
			</dl>

			<div
				v-if="action.action === 'collect_artifact'"
				class="flex min-w-0 flex-col gap-1"
				data-testid="talon-approval-collection"
			>
				<div class="flex flex-wrap items-baseline gap-x-2">
					<span class="text-tertiary">Artifact</span>
					<span class="font-mono font-semibold break-all" data-testid="talon-approval-artifact">
						<TalonUntrusted :text="artifactName" />
					</span>
				</div>
				<!-- Plain text: never Markdown or HTML. -->
				<p
					v-if="catalogueNote"
					class="text-secondary m-0 break-words whitespace-pre-wrap"
					data-testid="talon-approval-catalogue-note"
				>
					<TalonUntrusted :text="catalogueNote" />
				</p>
				<span class="text-tertiary">Parameters, sent to Velociraptor as written</span>
				<n-table
					v-if="parameters.ok && parameters.rows.length"
					size="small"
					:single-line="false"
					class="text-xs"
					data-testid="talon-approval-parameters"
				>
					<thead>
						<tr>
							<th>Parameter</th>
							<th>Value</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, index) of parameters.rows" :key="index" data-testid="talon-approval-parameter">
							<td class="font-mono break-all" data-testid="talon-approval-parameter-key">
								<TalonUntrusted :text="row.key" />
							</td>
							<td data-testid="talon-approval-parameter-value">
								<TalonCommandText inline :text="row.value" test-id="talon-approval-parameter-text" />
							</td>
						</tr>
					</tbody>
				</n-table>
				<div v-else-if="parameters.ok" class="text-secondary" data-testid="talon-approval-parameters-none">
					None: the artifact runs with its own defaults.
				</div>
				<template v-else>
					<n-alert
						type="warning"
						:bordered="false"
						class="text-xs"
						data-testid="talon-approval-parameters-raw-note"
					>
						These parameters aren't in the shape CoPilot sends to Velociraptor. They are shown as the record
						holds them.
					</n-alert>
					<div
						class="bg-default max-h-60 overflow-auto rounded p-1.5 font-mono break-all whitespace-pre-wrap"
						data-testid="talon-approval-parameters-raw"
					>
						<TalonUntrusted :text="parametersRaw" />
					</div>
				</template>
				<div
					v-for="warning of parameterLookalikes"
					:key="warning.flag"
					class="text-warning"
					data-testid="talon-approval-parameters-lookalike"
					:data-flag="warning.flag"
				>
					{{ warning.text }}
				</div>
			</div>

			<div
				v-if="action.action === 'endpoint_command'"
				class="flex min-w-0 flex-col gap-1.5"
				data-testid="talon-approval-command"
			>
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<span class="text-tertiary">Shell</span>
					<span class="font-semibold" data-testid="talon-approval-shell">
						{{ shell ?? "not a known shell" }}
					</span>
					<span class="text-tertiary font-mono break-all" data-testid="talon-approval-shell-artifact">
						<TalonUntrusted :text="artifactName" />
					</span>
					<n-tag
						size="small"
						:bordered="false"
						:type="shapeCaution ? 'warning' : 'success'"
						data-testid="talon-approval-shape"
						:data-shape="shape"
						:data-caution="shapeCaution ? 'true' : 'false'"
					>
						{{ shapeLabel }}
					</n-tag>
				</div>
				<n-alert
					v-if="shellMismatch"
					type="warning"
					:bordered="false"
					class="text-xs"
					data-testid="talon-approval-shell-mismatch"
				>
					{{ shellMismatch }}
				</n-alert>
				<div :class="shapeCaution ? 'text-warning' : 'text-tertiary'" data-testid="talon-approval-shape-note">
					{{ shapeNote }}
				</div>
				<div class="flex flex-wrap items-center gap-1.5" data-testid="talon-approval-risks">
					<span class="text-tertiary">Risk labels</span>
					<n-tag
						v-for="risk of risks"
						:key="risk.key"
						size="small"
						type="error"
						:bordered="false"
						data-testid="talon-approval-risk"
						:data-risk="risk.key"
					>
						<TalonUntrusted :text="risk.text" />
					</n-tag>
					<span v-if="!riskListed" class="text-warning" data-testid="talon-approval-risks-unlabelled">
						not labelled
					</span>
					<span v-else-if="!risks.length" class="text-secondary" data-testid="talon-approval-risks-none">
						none matched
					</span>
				</div>
				<div class="text-tertiary" data-testid="talon-approval-risks-note">{{ RISK_LABELS_NOTE }}</div>
				<div class="flex flex-wrap items-baseline gap-x-3">
					<span class="text-tertiary grow">The command, exactly as it runs (plain text, every line)</span>
					<span class="text-secondary" data-testid="talon-approval-command-counts">
						{{ commandCountsText }}
					</span>
				</div>
				<n-alert
					v-for="warning of commandLookalikes"
					:key="warning.flag"
					type="warning"
					:bordered="false"
					class="text-xs"
					data-testid="talon-approval-command-lookalike"
					:data-flag="warning.flag"
				>
					{{ warning.text }}
				</n-alert>
				<TalonCommandText
					:text="command"
					:max-rows="16"
					:total-lines="commandLines"
					test-id="talon-approval-command-text"
				/>
				<div v-if="whitespaceText" class="text-warning" data-testid="talon-approval-whitespace">
					{{ whitespaceText }}
				</div>
			</div>

			<div class="flex flex-col gap-0.5" data-testid="talon-approval-reason">
				<span class="text-tertiary">The model's reason (untrusted: written by the model, not checked)</span>
				<!-- Plain text: never Markdown or HTML. -->
				<p class="text-secondary break-words whitespace-pre-wrap" data-testid="talon-approval-reason-text">
					<TalonUntrusted :text="action.reason || 'none given'" />
				</p>
			</div>

			<div v-if="comment !== null" class="flex flex-col gap-0.5" data-testid="talon-approval-comment">
				<span class="text-tertiary">Comment text (from the model, posted as written)</span>
				<!-- The comment raw and capped, so it can't push the real target away from the buttons. -->
				<div
					class="bg-default max-h-60 overflow-auto rounded p-1.5 font-mono break-words whitespace-pre-wrap"
					data-testid="talon-approval-comment-text"
				>
					<TalonUntrusted :text="comment" links />
				</div>
				<div v-if="action.links" class="text-warning" data-testid="talon-approval-links-note">
					This comment holds links. They are shown, not opened: check them before approving.
				</div>
			</div>

			<div class="text-tertiary flex flex-wrap gap-x-3 gap-y-0.5">
				<span data-testid="talon-approval-requester">
					Requested by
					<TalonUntrusted :text="requester" />
				</span>
				<span v-if="createdAt">{{ formatDate(createdAt, dFormats.datetime) }}</span>
				<span v-if="expiryText" data-testid="talon-approval-expiry">{{ expiryText }}</span>
			</div>

			<div v-if="decisionLine" class="text-secondary" data-testid="talon-approval-decision">
				{{ decisionLine.verb }} by
				<TalonUntrusted :text="decisionLine.who" />
				{{ decisionLine.at }}
			</div>
			<div v-if="resultText" class="text-secondary" data-testid="talon-approval-result">
				Result:
				<TalonUntrusted :text="resultText" />
			</div>
			<div v-if="flowId" class="text-secondary" data-testid="talon-approval-flow">
				Velociraptor flow
				<span class="font-mono"><TalonUntrusted :text="flowId" /></span>
			</div>
			<div v-if="reasonText" class="text-tertiary" data-testid="talon-approval-state-reason">
				<TalonUntrusted :text="reasonText" />
			</div>
			<div v-if="reportText" class="text-tertiary" data-testid="talon-approval-reported">{{ reportText }}</div>
		</template>

		<div v-if="entry.decisionNote" class="text-warning" data-testid="talon-approval-note">
			<TalonUntrusted :text="entry.decisionNote" />
		</div>
		<div v-if="entry.decisionError" class="text-error" data-testid="talon-approval-error">
			<TalonUntrusted :text="entry.decisionError" />
		</div>

		<div
			v-if="action && (action.can_decide || withdrawable)"
			class="border-default flex flex-col gap-1.5 border-t pt-2"
			data-testid="talon-approval-actions"
		>
			<div v-if="action.can_decide" class="text-secondary" data-testid="talon-approval-summary">
				Approve:
				<template v-for="(part, index) of summary" :key="index">
					<TalonUntrusted v-if="part.untrusted" class="font-semibold" :text="part.text" />
					<template v-else>{{ part.text }}</template>
				</template>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<template v-if="action.can_decide">
					<n-button
						size="small"
						type="primary"
						:disabled="busy"
						:loading="entry.busy === 'approve'"
						:aria-label="`Approve: ${summaryText}`"
						data-testid="talon-approval-approve"
						@click="askApprove()"
					>
						Approve
					</n-button>
					<n-button
						size="small"
						secondary
						:disabled="busy"
						:loading="entry.busy === 'deny'"
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
					:loading="entry.busy === 'withdraw'"
					data-testid="talon-approval-withdraw"
					@click="decide('withdraw')"
				>
					Withdraw
				</n-button>
				<span v-if="entry.busy === 'approve'" class="text-tertiary">
					Approving and running it in CoPilot...
				</span>
			</div>
		</div>

		<n-modal
			v-model:show="confirming"
			preset="card"
			:title="confirmTitle"
			:style="{ maxWidth: 'min(520px, 94vw)' }"
			:mask-closable="!busy"
			:closable="!busy"
			segmented
			data-testid="talon-approval-confirm"
		>
			<div v-if="action" class="flex flex-col gap-2 text-sm" data-testid="talon-approval-confirm-text">
				<p>
					<strong>{{ actionLabel(action.action) }}</strong>
				</p>
				<p>
					Approve:
					<template v-for="(part, index) of summary" :key="index">
						<TalonUntrusted v-if="part.untrusted" class="font-mono font-semibold" :text="part.text" />
						<template v-else>{{ part.text }}</template>
					</template>
				</p>
				<div
					v-if="action.action === 'endpoint_command'"
					class="flex min-w-0 flex-col gap-1"
					data-testid="talon-approval-confirm-command"
				>
					<span class="text-secondary text-xs" data-testid="talon-approval-confirm-first-line-label">
						Its first non-blank line, line {{ commandFirst.line }} ({{ commandCountsText }} in all):
					</span>
					<span
						v-if="commandFirst.line > 1"
						class="text-warning text-xs"
						data-testid="talon-approval-confirm-blank-lines"
					>
						The command starts with {{ commandFirst.line - 1 }} blank
						{{ commandFirst.line === 2 ? "line" : "lines" }}.
					</span>
					<TalonCommandText
						:text="commandFirst.text"
						:first-line-number="commandFirst.line"
						:max-rows="6"
						test-id="talon-approval-confirm-first-line"
					/>
					<span
						v-if="commandLines > commandFirst.line"
						class="text-warning text-xs"
						data-testid="talon-approval-confirm-more"
					>
						and {{ commandLines - commandFirst.line }} more
						{{ commandLines - commandFirst.line === 1 ? "line" : "lines" }}: read the whole command on the
						card before running it.
					</span>
					<span
						v-for="warning of confirmWarnings"
						:key="warning.flag"
						class="text-warning text-xs"
						data-testid="talon-approval-confirm-warning"
						:data-flag="warning.flag"
					>
						{{ warning.text }}
					</span>
				</div>
				<p class="text-secondary text-xs">
					<template v-if="action.action === 'quarantine_host'">
						Velociraptor cuts the host off the network but for its connection to Velociraptor.
					</template>
					<template v-else-if="action.action === 'release_host'">
						Velociraptor gives the host its network connections back.
					</template>
					<template v-else-if="action.action === 'collect_artifact'">
						Velociraptor collects the artifact on the host; Talon reads the results.
					</template>
					<template v-else-if="action.action === 'endpoint_command'">
						Velociraptor runs the command on the host with its client's privileges (SYSTEM on Windows, root
						on Linux); Talon reads the output.
					</template>
					CoPilot runs it now, as you. The target and customer are CoPilot's record of the proposal.
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
						{{ confirmVerb }}
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
// model's own arguments, shown in the tool row, apart from this card). Every value from the record
// is untrusted text (`TalonUntrusted`: inside `<bdi>`, invisible and direction-changing characters
// escaped, a warning when there are any); the reason is labelled untrusted, a comment is raw in a
// capped box with its links highlighted and never clickable. Approve and Deny only when CoPilot
// says the caller may decide it; Withdraw for its requester while it is pending. Every Approve asks
// first, naming the action, the target and the customer from the record, which the button row
// also shows. The record, the read and the decision in flight are shared by every card of the
// proposal, and one poll for the page keeps them fresh (`actionCards.ts`).
//
// Endpoint actions (talon-analyst's endpoint actions plan, EA-4; SPEC §9.5, D74-D79): a collection
// shows its artifact and a table of the parameters CoPilot sends; a command shows its shell, its
// read-only / free-form shape, talon-analyst's risk labels, its counts, and the command itself in a
// `<pre>` of text nodes (`TalonCommandText`: whole, scrolled, tabs and trailing spaces marked). The
// confirm names the host and, for a command, its first line.
import type { DecisionKind } from "./actionCards"
import { NAlert, NButton, NModal, NTable, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { useActionCard } from "./actionCards"
import {
	actionLabel,
	collectionParameters,
	commandCounts,
	commandShape,
	countsText,
	expiryDeadline,
	firstContentLine,
	hasHiddenChars,
	hasUnseenChars,
	HIDDEN_CHARS_WARNING,
	isHostAction,
	isWithdrawable,
	lookalikeWarnings,
	parseUtc,
	provenanceWarnings,
	RISK_LABELS_NOTE,
	riskLabelled,
	riskLabels,
	safeSegments,
	shellOf,
	shellOs,
	stateLabel,
	stateTone,
	timeLeft,
	whitespaceCounts
} from "./approvals"
import TalonCommandText from "./TalonCommandText"
import TalonUntrusted from "./TalonUntrusted"

const { approvalId } = defineProps<{ approvalId: string }>()

const dFormats = useSettingsStore().dateFormat

const { entry, decide: decideCard } = useActionCard(approvalId)
const action = computed(() => entry.value.action)
const busy = computed(() => !!entry.value.busy)
const confirming = ref(false)
const now = ref(Date.now())
let clockTimer: ReturnType<typeof setInterval> | null = null

function decide(kind: DecisionKind) {
	decideCard(kind)
}

function askApprove() {
	if (!action.value || busy.value) return
	confirming.value = true
}

function confirmApprove() {
	if (!action.value?.can_decide || busy.value) return
	decideCard("approve")
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
		client: typeof target.velociraptor_id === "string" ? target.velociraptor_id : null,
		os: typeof target.os === "string" ? target.os : null
	}
})

const args = computed(() =>
	Object.entries(action.value?.args ?? {}).map(([key, value]) => ({ key, text: asText(value) }))
)
const comment = computed(() => {
	const value = action.value?.args?.comment
	return value === undefined ? null : asText(value)
})

// ── a collection or a command ──

/** Arguments shown in their own view below the list, not inline. */
const shownBelow = computed(() => {
	const keys = new Set(["comment"])
	if (action.value?.action === "collect_artifact") keys.add("parameters")
	if (action.value?.action === "endpoint_command") keys.add("command")
	return keys
})
const artifactName = computed(() => asText(action.value?.args?.artifact_name ?? ""))
const parameters = computed(() => collectionParameters(action.value?.args?.parameters))
const parameterLookalikes = computed(() =>
	lookalikeWarnings(parameters.value.rows.map(row => row.value).join("\n"), "A parameter value")
)
/** The catalogue's one-line note for the artifact (talon-analyst's `provenance.catalogue_note`). */
const catalogueNote = computed(() => {
	const note = action.value?.provenance?.catalogue_note
	return typeof note === "string" && note.trim() ? note : null
})
const parametersRaw = computed(() => {
	const value = action.value?.args?.parameters
	try {
		return JSON.stringify(value, null, 2) ?? String(value)
	} catch {
		return String(value)
	}
})

const command = computed(() => {
	const value = action.value?.args?.command
	return value === undefined || value === null ? "" : asText(value)
})
const commandLines = computed(() => commandCounts(command.value).lines)
const commandCountsText = computed(() => countsText(command.value))
const commandFirst = computed(() => firstContentLine(command.value))
const shell = computed(() => shellOf(action.value?.args?.artifact_name))
const shellMismatch = computed(() => {
	const os = host.value?.os
	const runsOn = shellOs(action.value?.args?.artifact_name)
	if (!os || !runsOn || os.toLowerCase() === runsOn) return null
	return `The shell (${shell.value}) is for ${runsOn === "windows" ? "Windows" : "Linux"} hosts, but this host's OS is recorded as ${os}. CoPilot should refuse it: don't approve it.`
})
const shape = computed(() => commandShape(action.value?.provenance))
const risks = computed(() => riskLabels(action.value?.provenance))
const riskListed = computed(() => riskLabelled(action.value?.provenance))
const copied = computed(() => action.value?.provenance?.copied_from_output === true)
/** Read-only gets the caution style too when the command carries risk labels or copied output. */
const shapeCaution = computed(() => shape.value !== "read-only" || risks.value.length > 0 || copied.value)
const shapeLabel = computed(() => (shape.value === "unknown" ? "shape not labelled" : shape.value))
const shapeNote = computed(() => {
	switch (shape.value) {
		case "read-only":
			if (shapeCaution.value) {
				const why = [
					risks.value.length ? "risk labels" : "",
					copied.value ? "parts copied from endpoint output" : ""
				]
					.filter(Boolean)
					.join(" and ")
				return `Labelled read-only, but it carries ${why}: read every line before approving.`
			}
			return "Read-only shape: talon-analyst found only read commands and filters, by a short allowlist. A heuristic: read it anyway."
		case "free-form":
			return "Free-form: not only plain reads. It may change the host: read every line before approving."
		default:
			return "talon-analyst didn't label this command's shape: treat it as free-form and read every line."
	}
})
const commandLookalikes = computed(() => lookalikeWarnings(command.value))
const confirmWarnings = computed(() => {
	const out = commandLookalikes.value.map(w => ({ flag: w.flag as string, text: w.text }))
	if (hasUnseenChars(command.value)) out.unshift({ flag: "hidden", text: HIDDEN_CHARS_WARNING })
	return out
})
const whitespace = computed(() => whitespaceCounts(command.value))
const whitespaceText = computed(() => {
	const { tabs, trailingLines, spaceRuns } = whitespace.value
	const parts: string[] = []
	if (tabs) parts.push(`${tabs} ${tabs === 1 ? "tab" : "tabs"}, marked →`)
	if (spaceRuns) {
		parts.push(`${spaceRuns} ${spaceRuns === 1 ? "run" : "runs"} of 4 or more spaces, shown as ␠×N`)
	}
	if (trailingLines) {
		parts.push(`${trailingLines} ${trailingLines === 1 ? "line ends" : "lines end"} in whitespace, highlighted`)
	}
	return parts.length ? `Whitespace: ${parts.join("; ")}.` : null
})

/** "set Alert #840 to CLOSED (ACME)": the decision in the record's own words; untrusted parts marked. */
const summary = computed(() => {
	const a = action.value
	if (!a) return []
	const plain = (text: string) => ({ text, untrusted: false })
	const untrusted = (text: string) => ({ text, untrusted: true })
	const alert = alertId.value !== null ? plain(`Alert #${alertId.value}`) : plain("an alert")
	const argText = (key: string) => untrusted(asText(a.args?.[key] ?? ""))
	const onHost = () => [
		untrusted(host.value?.hostname ?? ""),
		plain(" (agent "),
		untrusted(host.value?.agentId ?? ""),
		plain(")")
	]
	let parts: { text: string; untrusted: boolean }[]
	switch (a.action) {
		case "set_alert_status":
			parts = [plain("set "), alert, plain(" to "), argText("status")]
			break
		case "assign_alert":
			parts = [plain("assign "), alert, plain(" to "), argText("assigned_to")]
			break
		case "comment_on_alert":
			parts = [plain("comment on "), alert]
			break
		case "quarantine_host":
		case "release_host":
			parts = [plain(a.action === "quarantine_host" ? "quarantine " : "release "), ...onHost()]
			break
		case "collect_artifact":
			parts = [plain("collect "), untrusted(artifactName.value), plain(" on "), ...onHost()]
			break
		case "endpoint_command":
			parts = shell.value
				? [plain(`run a ${shell.value} command on `), ...onHost()]
				: [plain("run a command ("), untrusted(artifactName.value), plain(") on "), ...onHost()]
			break
		default:
			parts = [plain(actionLabel(a.action))]
	}
	return [...parts, plain(" for customer "), untrusted(a.customer_code)]
})
const summaryText = computed(() =>
	summary.value
		.map(part =>
			part.untrusted
				? safeSegments(part.text)
						.map(s => s.text)
						.join("")
				: part.text
		)
		.join("")
)

const hiddenChars = computed(() => {
	const a = action.value
	if (!a) return false
	const values = [
		a.reason,
		a.customer_code,
		a.state_reason,
		a.requester_username,
		a.execution_result?.message,
		...Object.keys(a.args ?? {}),
		...args.value.map(arg => arg.text),
		...Object.values(a.target ?? {}).map(asText),
		...riskLabels(a.provenance).map(risk => risk.text),
		...parameters.value.rows.flatMap(row => [row.key, row.value])
	]
	return (
		values.some(value => typeof value === "string" && hasHiddenChars(value)) ||
		(a.action === "endpoint_command" && hasUnseenChars(command.value)) ||
		parameters.value.rows.some(row => hasUnseenChars(row.key) || hasUnseenChars(row.value))
	)
})

const warnings = computed(() => provenanceWarnings(action.value?.provenance))
const requester = computed(() => {
	const a = action.value
	if (!a) return ""
	if (a.is_requester) return "you"
	return a.requester_username || `CoPilot user #${a.requester_user_id}`
})
const withdrawable = computed(() => !!action.value && isWithdrawable(action.value))
const createdAt = computed(() => parseUtc(action.value?.created_at))
const expiryText = computed(() => {
	const a = action.value
	if (!a || a.state !== "pending") return null
	if (a.expired) return "Expired"
	const deadline = expiryDeadline(a, entry.value.receivedAt)
	if (deadline === null) return "Expiry unknown"
	const left = timeLeft(deadline, now.value)
	return left ? `Expires in ${left}` : "Expired"
})

const decisionLine = computed(() => {
	const a = action.value
	if (!a?.approver_username || !a.decision) return null
	const at = parseUtc(a.decided_at)
	return {
		verb: a.decision === "deny" ? "Denied" : "Approved",
		who: a.approver_username,
		at: at ? ` on ${formatDate(at, dFormats.datetime)}` : ""
	}
})
const resultText = computed(() => {
	const message = action.value?.execution_result?.message
	return typeof message === "string" && message ? message : null
})
const flowId = computed(() => {
	const flow = action.value?.execution_result?.flow_id
	return typeof flow === "string" && flow ? flow : null
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

const confirmTitle = computed(() => {
	if (action.value?.action === "quarantine_host") return "Quarantine this host?"
	if (action.value?.action === "release_host") return "Release this host from quarantine?"
	if (action.value?.action === "collect_artifact") return "Collect this artifact on the host?"
	if (action.value?.action === "endpoint_command") return "Run this command on the host?"
	return "Approve this action?"
})
const confirmVerb = computed(() => {
	if (action.value?.action === "quarantine_host") return "Quarantine"
	if (action.value?.action === "release_host") return "Release"
	if (action.value?.action === "collect_artifact") return "Collect"
	if (action.value?.action === "endpoint_command") return "Run the command"
	return "Approve and run"
})

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

// A confirm opened on an older record never sends: it closes when the record moves on.
watch(
	() => [action.value?.state, action.value?.talon_status, action.value?.can_decide],
	() => {
		if (confirming.value && !busy.value) confirming.value = false
	}
)
watch(
	() => !!action.value?.can_decide,
	can => {
		if (!can) confirming.value = false
	}
)
watch(busy, (running, wasRunning) => {
	// The decision this confirm sent has its answer: the dialog's job is done.
	if (wasRunning && !running) confirming.value = false
})

// The expiry countdown ticks only while the proposal waits.
watch(
	() => !!action.value && action.value.state === "pending" && !action.value.expired,
	ticking => {
		if (clockTimer) clearInterval(clockTimer)
		clockTimer = null
		if (ticking) clockTimer = setInterval(() => (now.value = Date.now()), 1000)
	},
	{ immediate: true }
)

onBeforeUnmount(() => {
	if (clockTimer) clearInterval(clockTimer)
})
</script>
