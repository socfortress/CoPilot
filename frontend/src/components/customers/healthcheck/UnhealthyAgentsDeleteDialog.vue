<template>
	<n-modal
		v-model:show="show"
		preset="card"
		segmented
		:bordered="false"
		:closable="phase !== 'running'"
		:mask-closable="phase !== 'running'"
		:close-on-esc="phase !== 'running'"
		:style="{ width: 'min(720px, calc(100vw - 32px))' }"
		class="unhealthy-delete-dialog"
		content-class="p-0!"
		footer-class="px-4! py-3! sm:px-6!"
		header-class="px-4! py-3! sm:px-6!"
		data-testid="unhealthy-delete-dialog"
	>
		<template #header>
			<div class="flex min-w-0 flex-col gap-0.5">
				<span class="truncate text-base leading-tight font-semibold">Delete unhealthy agents</span>
				<span class="text-secondary truncate text-xs" data-testid="unhealthy-delete-scope">
					{{ toolName(source) }} healthcheck · {{ customerCode }}
				</span>
			</div>
		</template>

		<div class="@container">
			<!-- ── configure: three steps, each on a numbered rail (#1291) ──────────── -->
			<ol v-if="phase === 'configure'" class="steps m-0 list-none p-0" data-testid="unhealthy-delete-steps">
				<li class="step" :class="`is-${stepStates[0]}`" data-step="1">
					<div class="step-rail" aria-hidden="true">
						<span class="step-marker">
							<Icon v-if="stepStates[0] === 'done'" :name="CheckIcon" :size="13" />
							<template v-else>1</template>
						</span>
					</div>
					<section class="step-body" aria-labelledby="uhd-threshold">
						<header class="step-head">
							<span class="step-count">Step 1 of 3</span>
							<h4 id="uhd-threshold" class="step-title">Choose the threshold</h4>
							<p class="step-desc">Agents not seen for longer than this can be deleted.</p>
						</header>
						<div class="threshold-row flex flex-wrap items-center gap-2">
							<n-radio-group
								:value="activePreset"
								size="small"
								name="unhealthy-delete-preset"
								class="presets"
								data-testid="unhealthy-delete-presets"
								@update:value="applyPreset"
							>
								<n-radio-button
									v-for="preset of THRESHOLD_PRESETS"
									:key="preset.key"
									:value="preset.key"
									:label="preset.label"
								/>
							</n-radio-group>
							<div class="flex items-center gap-2">
								<span class="text-tertiary px-1 text-xs">or</span>
								<n-input-group class="w-auto!">
									<n-input-number
										v-model:value="thresholdValue"
										size="small"
										:min="1"
										:precision="0"
										:show-button="false"
										placeholder="—"
										class="w-20! font-mono"
										:input-props="{ 'aria-label': 'Not seen for', inputmode: 'numeric' }"
										data-testid="unhealthy-delete-value"
									/>
									<n-select
										v-model:value="thresholdUnit"
										size="small"
										:options="UNIT_OPTIONS"
										class="w-24!"
										:consistent-menu-width="false"
										aria-label="Unit"
										data-testid="unhealthy-delete-unit"
									/>
								</n-input-group>
							</div>
						</div>
						<p
							v-if="problem"
							class="text-error m-0 text-xs"
							role="alert"
							data-testid="unhealthy-delete-problem"
						>
							{{ problem }}
						</p>
						<p v-else class="text-secondary m-0 text-xs" data-testid="unhealthy-delete-cutoff">
							<template v-if="preview && previewCurrent">
								Last seen before
								<time :datetime="preview.cutoff" class="text-default font-mono">
									{{ formatDate(preview.cutoff, dFormats.datetime, { tz: true }) }}
								</time>
							</template>
							<template v-else>&nbsp;</template>
						</p>
						<div
							v-if="validThreshold && caution"
							class="callout callout-warning"
							role="note"
							data-testid="unhealthy-delete-caution"
						>
							<Icon :name="WarningIcon" :size="15" class="mt-px shrink-0" />
							<span>
								Under 7 days, this can include endpoints that are only switched off — over a weekend or
								a holiday. Check the list before you confirm.
							</span>
						</div>
					</section>
				</li>

				<li class="step" :class="`is-${stepStates[1]}`" data-step="2">
					<div class="step-rail" aria-hidden="true">
						<span class="step-marker">
							<Icon v-if="stepStates[1] === 'done'" :name="CheckIcon" :size="13" />
							<template v-else>2</template>
						</span>
					</div>
					<section class="step-body" aria-labelledby="uhd-impact">
						<header class="step-head">
							<span class="step-count">Step 2 of 3</span>
							<h4 id="uhd-impact" class="step-title">Review the impact</h4>
							<p class="step-desc">
								What the server will do with each of the {{ props.agents.length }} selected
								{{ props.agents.length === 1 ? "agent" : "agents" }}, judged now.
							</p>
						</header>

						<div v-if="previewError" class="callout callout-error" role="alert">
							<Icon :name="ErrorIcon" :size="15" class="mt-px shrink-0" />
							<span class="grow">{{ previewError }}</span>
							<n-button size="tiny" secondary @click="loadPreview()">Retry</n-button>
						</div>

						<!-- The three cells split the selection: an included agent moves to Delete. -->
						<div class="stats stats-split" :class="{ 'is-stale': !previewCurrent }" aria-live="polite">
							<div class="stat stat-danger" data-testid="unhealthy-delete-count">
								<span class="stat-label">Delete</span>
								<span class="stat-value">{{ previewCurrent ? groups.toDelete.length : "—" }}</span>
							</div>
							<div class="stat" :class="{ 'stat-warning': groups.activeElsewhere.length }">
								<span class="stat-label">Seen by {{ toolName(otherTool(source)) }}</span>
								<span class="stat-value" data-testid="unhealthy-delete-active-elsewhere">
									{{ previewCurrent ? groups.activeElsewhere.length : "—" }}
								</span>
							</div>
							<div class="stat">
								<span class="stat-label">Kept</span>
								<span class="stat-value" data-testid="unhealthy-delete-kept">
									{{ previewCurrent ? groups.kept.length : "—" }}
								</span>
							</div>
						</div>

						<!-- The whole row toggles: a label cannot target the switch, which is no native control. -->
						<div
							v-if="previewCurrent && activeElsewhereCount"
							class="include-row flex cursor-pointer items-start gap-3 rounded-lg px-3 py-2.5"
							data-testid="unhealthy-delete-include"
							@click="includeActiveElsewhere = !includeActiveElsewhere"
						>
							<span class="mt-0.5 flex" @click.stop>
								<n-switch
									v-model:value="includeActiveElsewhere"
									size="small"
									aria-labelledby="uhd-include-label"
									data-testid="unhealthy-delete-include-switch"
								/>
							</span>
							<span class="flex min-w-0 flex-col gap-0.5">
								<span id="uhd-include-label" class="text-default text-sm">
									Also delete the {{ activeElsewhereCount }}
									{{ activeElsewhereCount === 1 ? "agent" : "agents" }}
									{{ toolName(otherTool(source)) }} still sees
								</span>
								<span class="text-secondary text-xs">
									{{ toolName(otherTool(source)) }} saw them within the threshold, so the endpoints
									are likely running. Deleting removes them from
									{{ toolName(otherTool(source)) }} too.
								</span>
							</span>
						</div>

						<div
							v-if="preview && previewCurrent"
							class="agent-list rounded-lg"
							data-testid="unhealthy-delete-agents"
						>
							<n-scrollbar class="max-h-72" trigger="none">
								<template v-for="section of sections" :key="section.key">
									<div v-if="section.agents.length" class="agent-group">
										<div
											class="agent-group-header eyebrow flex items-center justify-between gap-3 px-3 py-1.5"
										>
											<span class="truncate">
												{{ section.title }}
												<span class="text-secondary tabular-nums">
													· {{ section.agents.length }}
												</span>
											</span>
											<span class="shrink-0">
												{{ section.key === "kept" ? "Reason" : "Last seen" }}
											</span>
										</div>
										<ul class="m-0 list-none p-0">
											<li
												v-for="agent of section.agents"
												:key="agent.agent_id"
												class="agent-row grid items-center gap-x-3 px-3 py-2"
												:data-agent="agent.agent_id"
												:data-verdict="agent.verdict"
											>
												<Dot :variant="section.dot" />
												<div class="flex min-w-0 flex-col">
													<span
														class="text-default truncate text-sm"
														:title="agent.hostname ?? agent.agent_id"
													>
														<bdi>{{ agent.hostname ?? agent.agent_id }}</bdi>
													</span>
													<span class="text-tertiary truncate font-mono text-[11px]">
														#{{ agent.agent_id }}
														<template v-if="agent.os">· {{ agent.os }}</template>
													</span>
												</div>
												<span
													v-if="section.key === 'kept'"
													class="text-secondary text-right text-xs"
													:title="verdictText(agent.verdict, source).hint"
												>
													{{ verdictText(agent.verdict, source).label }}
												</span>
												<!-- Each tool by name, then how long ago it last saw the agent. -->
												<dl v-else class="seen m-0" data-testid="unhealthy-delete-seen">
													<div
														class="seen-line"
														:title="lastSeenTitle(source, agent.last_seen)"
													>
														<dt>{{ toolName(source) }}</dt>
														<dd class="text-default">
															{{ compactAge(agent.last_seen, now) }}
														</dd>
													</div>
													<div
														class="seen-line"
														:title="lastSeenTitle(otherTool(source), agent.other_last_seen)"
													>
														<dt>{{ toolName(otherTool(source)) }}</dt>
														<dd
															:class="
																section.key === 'elsewhere'
																	? 'text-warning'
																	: 'text-secondary'
															"
														>
															{{ compactAge(agent.other_last_seen, now) }}
														</dd>
													</div>
												</dl>
											</li>
										</ul>
									</div>
								</template>
							</n-scrollbar>
						</div>
						<div
							v-else-if="previewLoading"
							class="agent-list flex h-24 items-center justify-center rounded-lg"
						>
							<n-spin size="small" />
						</div>
					</section>
				</li>

				<li class="step" :class="`is-${stepStates[2]}`" data-step="3">
					<div class="step-rail" aria-hidden="true">
						<span class="step-marker">
							<Icon v-if="stepStates[2] === 'done'" :name="CheckIcon" :size="13" />
							<span v-else class="mt-0.5">3</span>
						</span>
					</div>
					<section class="step-body" aria-labelledby="uhd-confirm">
						<header class="step-head">
							<span class="step-count">Step 3 of 3</span>
							<h4 id="uhd-confirm" class="step-title">Confirm the deletion</h4>
							<p class="step-desc">Read what happens to each agent, then confirm.</p>
						</header>

						<div class="consequences" data-testid="unhealthy-delete-consequences">
							<ul class="m-0 flex list-none flex-col gap-2 p-0">
								<li v-for="item of CONSEQUENCES" :key="item.text" class="flex items-start gap-2.5">
									<Icon :name="item.icon" :size="15" class="text-secondary mt-px shrink-0" />
									<span>{{ item.text }}</span>
								</li>
							</ul>
						</div>

						<div v-if="typedNeeded" class="typed-confirm" data-testid="unhealthy-delete-typed-box">
							<label for="uhd-typed" class="text-default text-sm">
								To confirm, type the number of agents to delete:
								<strong class="count-chip">{{ groups.toDelete.length }}</strong>
							</label>
							<div class="flex items-center gap-3">
								<n-input
									v-model:value="typed"
									size="small"
									class="w-32! font-mono"
									:status="typed && !typedMatches ? 'error' : undefined"
									:placeholder="String(groups.toDelete.length)"
									:input-props="{ id: 'uhd-typed', inputmode: 'numeric', autocomplete: 'off' }"
									data-testid="unhealthy-delete-typed"
									@keyup.enter="startDeletion()"
								/>
								<span
									v-if="typedMatches"
									class="text-success flex items-center gap-1.5 text-xs"
									data-testid="unhealthy-delete-typed-ok"
								>
									<Icon :name="CheckIcon" :size="14" />
									Matches
								</span>
							</div>
						</div>
						<p
							v-else-if="previewCurrent && !groups.toDelete.length"
							class="text-secondary m-0 text-xs"
							data-testid="unhealthy-delete-nothing"
						>
							Nothing to delete at this threshold.
						</p>
					</section>
				</li>
			</ol>

			<!-- ── running ───────────────────────────────────────────────────────── -->
			<div
				v-else-if="phase === 'running'"
				class="section gap-4!"
				aria-live="polite"
				data-testid="unhealthy-delete-running"
			>
				<div class="flex items-end justify-between gap-3">
					<div class="flex flex-col gap-1">
						<span class="eyebrow">{{ stopRequested ? "Stopping after this batch" : "Deleting" }}</span>
						<span class="text-secondary text-xs">
							In batches of {{ DELETE_CHUNK_SIZE }}, one at a time. Keep this window open.
						</span>
					</div>
					<span class="progress-count font-mono tabular-nums" data-testid="unhealthy-delete-progress">
						{{ processed }}
						<span class="text-tertiary">/ {{ total }}</span>
					</span>
				</div>
				<n-progress
					type="line"
					:percentage="total ? Math.round((processed / total) * 100) : 0"
					:show-indicator="false"
					:height="6"
					status="error"
					processing
				/>
				<div class="stats grid grid-cols-2 @md:grid-cols-4">
					<div v-for="cell of totalsCells" :key="cell.key" class="stat" :class="cell.class">
						<span class="eyebrow truncate">{{ cell.label }}</span>
						<span class="stat-value stat-value-sm">{{ cell.value }}</span>
					</div>
				</div>
			</div>

			<!-- ── done ──────────────────────────────────────────────────────────── -->
			<div v-else class="section gap-4!" data-testid="unhealthy-delete-done">
				<div class="flex items-center gap-3" role="status">
					<span
						class="outcome-tile flex size-9 shrink-0 items-center justify-center rounded-lg"
						:class="`is-${outcome.tone}`"
					>
						<Icon :name="outcome.icon" :size="18" />
					</span>
					<div class="flex min-w-0 flex-col">
						<span class="text-default text-sm font-semibold" data-testid="unhealthy-delete-outcome">
							{{ outcome.title }}
						</span>
						<span v-if="outcome.detail" class="text-secondary text-xs">{{ outcome.detail }}</span>
					</div>
				</div>

				<div class="stats grid grid-cols-2 @md:grid-cols-4">
					<div v-for="cell of totalsCells" :key="cell.key" class="stat" :class="cell.class">
						<span class="eyebrow truncate">{{ cell.label }}</span>
						<span class="stat-value stat-value-sm" :data-testid="`unhealthy-delete-total-${cell.key}`">
							{{ cell.value }}
						</span>
					</div>
				</div>

				<div v-if="run && run.totals.unconfirmed" class="callout callout-warning" role="note">
					<Icon :name="WarningIcon" :size="15" class="mt-px shrink-0" />
					<span>
						CoPilot removed
						{{ run.totals.unconfirmed === 1 ? "one agent" : `${run.totals.unconfirmed} agents` }}, but Wazuh
						or Velociraptor did not confirm: they may still be enrolled there, and come back at the next
						agent sync. Remove them in that tool if they do.
					</span>
				</div>

				<div v-if="review.length" class="agent-list rounded-lg" data-testid="unhealthy-delete-review">
					<n-scrollbar class="max-h-60" trigger="none">
						<div class="agent-group-header eyebrow flex items-center justify-between gap-3 px-3 py-1.5">
							<span>
								To review
								<span class="text-secondary tabular-nums">· {{ review.length }}</span>
							</span>
							<span>Outcome</span>
						</div>
						<ul class="m-0 list-none p-0">
							<li
								v-for="result of review"
								:key="result.agent_id"
								class="agent-row grid items-center gap-x-3 px-3 py-2"
								:data-agent="result.agent_id"
							>
								<Dot :variant="resultDot(result)" />
								<div class="flex min-w-0 flex-col">
									<span
										class="text-default truncate text-sm"
										:title="result.hostname ?? result.agent_id"
									>
										<bdi>{{ result.hostname ?? result.agent_id }}</bdi>
									</span>
									<span class="text-tertiary font-mono text-[11px]" :title="resultText(result).hint">
										#{{ result.agent_id }} · {{ resultText(result).detail }}
									</span>
								</div>
								<span class="outcome-tag" :class="`is-${resultDot(result)}`">
									{{ resultText(result).label }}
								</span>
							</li>
						</ul>
					</n-scrollbar>
				</div>
			</div>
		</div>

		<template #footer>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<span
					v-if="phase === 'configure' && validThreshold"
					class="eyebrow mr-auto hidden sm:inline"
					data-testid="unhealthy-delete-summary"
				>
					{{ thresholdLabel(validThreshold) }} · {{ props.agents.length }} selected
				</span>
				<template v-if="phase === 'configure'">
					<n-button size="small" @click="show = false">Cancel</n-button>
					<n-button
						size="small"
						type="error"
						:disabled="!canDelete"
						data-testid="unhealthy-delete-confirm"
						@click="startDeletion()"
					>
						<template #icon><Icon :name="TrashIcon" :size="14" /></template>
						{{ deleteLabel }}
					</n-button>
				</template>
				<n-button
					v-else-if="phase === 'running'"
					size="small"
					:disabled="stopRequested"
					data-testid="unhealthy-delete-stop"
					@click="stopRequested = true"
				>
					<template #icon><Icon :name="StopIcon" :size="14" /></template>
					{{ stopRequested ? "Stopping…" : "Stop after this batch" }}
				</n-button>
				<n-button v-else size="small" type="primary" data-testid="unhealthy-delete-close" @click="show = false">
					Done
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { DeletionRun, ListFilter } from "./unhealthyDelete"
import type { DotVariant } from "@/components/common/Dot.vue"
import type { ApiError } from "@/types/common"
import type {
	CustomerAgentHealth,
	CustomerHealthcheckSource,
	UnhealthyAgentDeleteResult,
	UnhealthyAgentPreview,
	UnhealthyAgentsPreview,
	UnhealthyDeleteThreshold
} from "@/types/customers"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import {
	NButton,
	NInput,
	NInputGroup,
	NInputNumber,
	NModal,
	NProgress,
	NRadioButton,
	NRadioGroup,
	NScrollbar,
	NSelect,
	NSpin,
	NSwitch
} from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import Dot from "@/components/common/Dot.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import {
	chunk,
	compactAge,
	confirmationMatches,
	DELETE_CHUNK_SIZE,
	groupPreview,
	mergePreviews,
	needsCaution,
	otherTool,
	presetKey,
	PREVIEW_CHUNK_SIZE,
	resultsToReview,
	runChunkedDeletion,
	sameThreshold,
	THRESHOLD_PRESETS,
	thresholdFromListFilter,
	thresholdLabel,
	thresholdProblem,
	toolName,
	verdictText
} from "./unhealthyDelete"

const props = defineProps<{
	source: CustomerHealthcheckSource
	customerCode: string
	/** The selected unhealthy agents. */
	agents: CustomerAgentHealth[]
	/** The filter the list was read with: the dialog starts from it. */
	listFilter: ListFilter
}>()

const emit = defineEmits<{
	/** Some agents were deleted: the list should be read again. */
	(e: "deleted", agentIds: string[]): void
}>()

const show = defineModel<boolean>("show", { required: true })

const TrashIcon = "carbon:trash-can"
const WarningIcon = "carbon:warning-alt"
const ErrorIcon = "carbon:error"
const StopIcon = "carbon:stop-outline"
const DoneIcon = "carbon:checkmark-outline"
const CheckIcon = "carbon:checkmark"

/** What deleting does to each agent, one fact a line (step 3). */
const CONSEQUENCES = [
	{ icon: "carbon:close-outline", text: "It is removed from Wazuh, Velociraptor and CoPilot." },
	{ icon: "carbon:data-base", text: "Its collected artifacts and vulnerabilities are deleted." },
	{ icon: "carbon:plug", text: "It stops reporting: the endpoint has to be enrolled again to come back." },
	{ icon: "carbon:undo", text: "It is permanent: a deleted agent cannot be restored." }
]

const UNIT_OPTIONS = [
	{ label: "hours", value: "hours" },
	{ label: "days", value: "days" }
]

const dFormats = useSettingsStore().dateFormat

type Phase = "configure" | "running" | "done"
const phase = ref<Phase>("configure")

const thresholdValue = ref<number | null>(null)
const thresholdUnit = ref<UnhealthyDeleteThreshold["unit"]>("days")
const threshold = computed<Partial<UnhealthyDeleteThreshold>>(() => ({
	value: thresholdValue.value ?? undefined,
	unit: thresholdUnit.value
}))
const problem = computed(() => thresholdProblem(threshold.value))
const validThreshold = computed<UnhealthyDeleteThreshold | null>(() =>
	problem.value ? null : { value: thresholdValue.value as number, unit: thresholdUnit.value }
)
const activePreset = computed(() => presetKey(threshold.value))
const caution = computed(() => !!validThreshold.value && needsCaution(validThreshold.value))

function applyPreset(key: string) {
	const preset = THRESHOLD_PRESETS.find(item => item.key === key)
	if (!preset) return
	thresholdValue.value = preset.threshold.value
	thresholdUnit.value = preset.threshold.unit
}

// ── the preview ───────────────────────────────────────────────────────────────────────────────

const preview = ref<UnhealthyAgentsPreview | null>(null)
/** The threshold the preview was read at: a preview for another one is never acted on. */
const previewFor = ref<UnhealthyDeleteThreshold | null>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)
let previewController: AbortController | null = null
/** The threshold of the latest preview asked for, answered or not: the same one is never asked twice. */
let requestedFor: UnhealthyDeleteThreshold | null = null
const now = ref(Date.now())

const previewCurrent = computed(
	() => !!preview.value && !previewLoading.value && sameThreshold(previewFor.value, validThreshold.value)
)

async function loadPreview() {
	previewController?.abort()
	const wanted = validThreshold.value
	if (!wanted || !props.agents.length) {
		// Whatever was in flight is dropped: coming back to its threshold must ask again.
		previewController = null
		requestedFor = null
		previewLoading.value = false
		return
	}
	const controller = new AbortController()
	previewController = controller
	requestedFor = wanted
	previewLoading.value = true
	previewError.value = null
	try {
		const parts: UnhealthyAgentsPreview[] = []
		for (const ids of chunk(
			props.agents.map(agent => agent.agent_id),
			PREVIEW_CHUNK_SIZE
		)) {
			const response = await Api.customers.previewUnhealthyAgentsDeletion(
				props.customerCode,
				props.source,
				{ agent_ids: ids, not_seen_for: wanted },
				controller.signal
			)
			parts.push(response.data)
		}
		if (controller.signal.aborted) return
		now.value = Date.now()
		preview.value = mergePreviews(parts)
		previewFor.value = wanted
	} catch (error) {
		if (controller.signal.aborted || axios.isCancel(error)) return
		previewError.value =
			getApiErrorMessage(error as ApiError) || "Could not read which agents would be deleted. Try again."
	} finally {
		if (previewController === controller) previewLoading.value = false
	}
}

watchDebounced(
	() => [validThreshold.value?.value, validThreshold.value?.unit],
	() => {
		if (!show.value || phase.value !== "configure") return
		if (validThreshold.value && sameThreshold(requestedFor, validThreshold.value)) return
		loadPreview()
	},
	{ debounce: 300 }
)

// ── what will be deleted ──────────────────────────────────────────────────────────────────────

const includeActiveElsewhere = ref(false)
const typed = ref("")

const groups = computed(() => groupPreview(preview.value?.agents ?? [], includeActiveElsewhere.value))
const activeElsewhereCount = computed(() => preview.value?.counts.active_elsewhere ?? 0)

const sections = computed<
	{ key: "delete" | "elsewhere" | "kept"; title: string; dot: DotVariant; agents: UnhealthyAgentPreview[] }[]
>(() => [
	{ key: "delete", title: "Will be deleted", dot: "danger", agents: groups.value.toDelete },
	{
		key: "elsewhere",
		title: `Kept · seen by ${toolName(otherTool(props.source))}`,
		dot: "warning",
		agents: groups.value.activeElsewhere
	},
	{ key: "kept", title: "Kept", dot: "muted", agents: groups.value.kept }
])

// Every deletion asks for the count, two agents at 90 days as much as fifty at one: it cannot be undone.
const typedNeeded = computed(() => previewCurrent.value && groups.value.toDelete.length > 0)
const typedMatches = computed(() => confirmationMatches(typed.value, groups.value.toDelete.length))
const canDelete = computed(
	() => previewCurrent.value && groups.value.toDelete.length > 0 && (!typedNeeded.value || typedMatches.value)
)

type StepState = "todo" | "current" | "done"

/** Where the user is in the three steps: each is done only once the one before it is. */
const stepStates = computed<StepState[]>(() => {
	const threshold: StepState = validThreshold.value ? "done" : "current"
	const reviewed = previewCurrent.value && groups.value.toDelete.length > 0
	const review: StepState = threshold !== "done" ? "todo" : reviewed ? "done" : "current"
	const confirm: StepState = review !== "done" ? "todo" : canDelete.value ? "done" : "current"
	return [threshold, review, confirm]
})
const deleteLabel = computed(() => {
	const count = previewCurrent.value ? groups.value.toDelete.length : 0
	return count ? `Delete ${count} ${count === 1 ? "agent" : "agents"}` : "Delete"
})

// A count typed for another set never confirms this one.
watch(
	() => groups.value.toDelete.length,
	() => {
		typed.value = ""
	}
)

function lastSeenTitle(source: CustomerHealthcheckSource, lastSeen: string | null) {
	const when = lastSeen ? formatDate(lastSeen, dFormats.datetime, { tz: true }) : "never"
	return `${toolName(source)} last saw it: ${when}`
}

// ── the run ───────────────────────────────────────────────────────────────────────────────────

const stopRequested = ref(false)
const processed = ref(0)
const total = ref(0)
const run = ref<DeletionRun | null>(null)

async function startDeletion() {
	if (!canDelete.value || !previewFor.value || phase.value !== "configure") return
	const notSeenFor = previewFor.value
	const ids = groups.value.toDelete.map(agent => agent.agent_id)
	const include = includeActiveElsewhere.value

	phase.value = "running"
	stopRequested.value = false
	processed.value = 0
	total.value = ids.length
	run.value = null

	const finished = await runChunkedDeletion({
		ids,
		send: async part => {
			const response = await Api.customers.deleteUnhealthyAgents(props.customerCode, props.source, {
				agent_ids: part,
				not_seen_for: notSeenFor,
				include_active_elsewhere: include
			})
			return response.data
		},
		onChunk: (progress, done) => {
			processed.value = done
			run.value = { ...progress, totals: { ...progress.totals }, results: [...progress.results] }
		},
		shouldStop: () => stopRequested.value
	})
	run.value = finished
	phase.value = "done"

	const deleted = finished.results.filter(result => result.outcome === "deleted").map(result => result.agent_id)
	if (deleted.length) emit("deleted", deleted)
}

const totalsCells = computed(() => {
	const totals = run.value?.totals
	const cells = [
		{ key: "deleted", label: "Deleted", value: totals?.deleted ?? 0, class: "stat-success" },
		{
			key: "unconfirmed",
			label: "Not confirmed",
			value: totals?.unconfirmed ?? 0,
			class: totals?.unconfirmed ? "stat-warning" : ""
		},
		{ key: "skipped", label: "Skipped", value: totals?.skipped ?? 0, class: "" },
		{ key: "failed", label: "Failed", value: totals?.failed ?? 0, class: totals?.failed ? "stat-danger" : "" }
	]
	if (phase.value === "done" && totals?.notSent) {
		cells.push({ key: "notSent", label: "Not sent", value: totals.notSent, class: "stat-warning" })
	}
	return cells
})

const review = computed(() => resultsToReview(run.value?.results ?? []))

const outcome = computed(() => {
	const current = run.value
	if (!current) return { tone: "success", icon: DoneIcon, title: "", detail: "" }
	const { deleted, requested, failed, unconfirmed, notSent } = current.totals
	if (current.error) {
		return {
			tone: "error",
			icon: ErrorIcon,
			title: `Stopped after ${deleted} of ${requested} deleted`,
			detail:
				getApiErrorMessage(current.error as ApiError) || "A request failed; the agents not yet sent were kept."
		}
	}
	if (current.stopped) {
		return {
			tone: "warning",
			icon: StopIcon,
			title: `Stopped: ${deleted} of ${requested} deleted`,
			detail: `${notSent} ${notSent === 1 ? "agent was" : "agents were"} not sent and kept.`
		}
	}
	if (deleted === requested && !unconfirmed) {
		return {
			tone: "success",
			icon: DoneIcon,
			title: `${deleted} ${deleted === 1 ? "agent" : "agents"} deleted`,
			detail: "Removed from Wazuh, Velociraptor and CoPilot."
		}
	}
	return {
		tone: failed ? "error" : "warning",
		icon: failed ? ErrorIcon : WarningIcon,
		title: `${deleted} of ${requested} deleted`,
		detail: "Some agents need a look: see below."
	}
})

function resultDot(result: UnhealthyAgentDeleteResult): DotVariant {
	if (result.outcome === "failed") return "danger"
	if (result.outcome === "deleted") return "warning"
	return "muted"
}

/** A short tag, a few words under the name, and a sentence for its title. */
function resultText(result: UnhealthyAgentDeleteResult): { label: string; detail: string; hint: string } {
	if (result.outcome === "failed") {
		return {
			label: "Failed",
			detail: "kept, not deleted",
			hint: "CoPilot could not delete it, so it was kept. The audit log has the reason."
		}
	}
	if (result.outcome === "deleted") {
		const tools = result.unconfirmed.map(toolName).join(" and ")
		return {
			label: "Unconfirmed",
			detail: `${tools} did not confirm`,
			hint: `Removed from CoPilot, but ${tools} did not confirm: it may still be enrolled there.`
		}
	}
	const verdict = result.reason ? verdictText(result.reason, props.source) : null
	return { label: "Skipped", detail: verdict?.label.toLowerCase() ?? "skipped", hint: verdict?.hint ?? "" }
}

// ── open / close ──────────────────────────────────────────────────────────────────────────────

function reset() {
	const start = thresholdFromListFilter(props.listFilter)
	thresholdValue.value = start.value
	thresholdUnit.value = start.unit
	phase.value = "configure"
	preview.value = null
	previewFor.value = null
	previewError.value = null
	requestedFor = null
	includeActiveElsewhere.value = false
	typed.value = ""
	stopRequested.value = false
	processed.value = 0
	total.value = 0
	run.value = null
}

watch(
	show,
	value => {
		if (value) {
			reset()
			loadPreview()
		} else {
			previewController?.abort()
		}
	},
	{ immediate: true }
)

onBeforeUnmount(() => previewController?.abort())
</script>

<style scoped>
.eyebrow {
	font-family: var(--font-family-mono), monospace;
	font-size: 10px;
	line-height: 1.4;
	letter-spacing: 0.12em;
	text-transform: uppercase;
	color: var(--fg-tertiary-color);
}

.section {
	display: flex;
	flex-direction: column;
	gap: calc(var(--spacing) * 3);
	padding: calc(var(--spacing) * 4);
}

.section + .section {
	border-top: 1px solid var(--border-color);
}

@container (min-width: 32rem) {
	.section {
		padding: calc(var(--spacing) * 5) calc(var(--spacing) * 6);
	}
}

/* ── the three steps: a numbered rail, a line joining each marker to the next ── */
.steps {
	display: flex;
	flex-direction: column;
	padding: calc(var(--spacing) * 4) calc(var(--spacing) * 4) 0;
}

@container (min-width: 32rem) {
	.steps {
		padding: calc(var(--spacing) * 5) calc(var(--spacing) * 6) 0;
	}
}

.step {
	display: grid;
	grid-template-columns: 26px minmax(0, 1fr);
	column-gap: calc(var(--spacing) * 3.5);
}

.step-rail {
	position: relative;
	display: flex;
	justify-content: center;
}

.step-rail::after {
	content: "";
	position: absolute;
	top: 32px;
	bottom: 6px;
	left: 50%;
	width: 1px;
	transform: translateX(-50%);
	background-color: var(--border-color);
	transition: background-color 0.2s;
}

.step:last-child .step-rail::after {
	display: none;
}

.step.is-done .step-rail::after {
	background-color: rgb(var(--primary-color-rgb) / 0.55);
}

.step-marker {
	position: relative;
	z-index: 1;
	display: flex;
	width: 26px;
	height: 26px;
	align-items: center;
	justify-content: center;
	border: 1px solid var(--border-color);
	border-radius: 999px;
	background-color: var(--bg-default-color);
	color: var(--fg-tertiary-color);
	font-family: var(--font-family-mono), monospace;
	font-size: 12px;
	font-variant-numeric: tabular-nums;
	transition:
		background-color 0.2s,
		border-color 0.2s,
		color 0.2s,
		box-shadow 0.2s;
}

.step.is-current .step-marker {
	border-color: var(--primary-color);
	color: var(--primary-color);
	box-shadow: 0 0 0 3px rgb(var(--primary-color-rgb) / 0.15);
}

.step.is-done .step-marker {
	border-color: var(--primary-color);
	background-color: var(--primary-color);
	/* Dark on the primary in both themes: the check must read on amber. */
	color: rgb(0 0 0 / 0.85);
}

.step-body {
	display: flex;
	min-width: 0;
	flex-direction: column;
	gap: calc(var(--spacing) * 3);
	padding-bottom: calc(var(--spacing) * 6);
}

.step-head {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding-top: 1px;
}

.step-count {
	font-size: 11px;
	line-height: 1.3;
	color: var(--fg-tertiary-color);
}

.step-title {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	line-height: 1.3;
	color: var(--fg-default-color);
}

.step-desc {
	margin: 0;
	font-size: 12px;
	line-height: 1.45;
	color: var(--fg-secondary-color);
}

.step.is-todo .step-head {
	opacity: 0.75;
}

/* A phone cannot spare a column for it: the last-seen lines go under the name, which keeps the
   row's whole width. */
@container (max-width: 31.99rem) {
	.agent-row:has(.seen) {
		grid-template-columns: auto minmax(0, 1fr);
		row-gap: 3px;
	}

	.agent-row .seen {
		grid-column: 2;
		flex-direction: row;
		flex-wrap: wrap;
		align-items: baseline;
		column-gap: calc(var(--spacing) * 3);
	}

	.agent-row .seen-line dd {
		min-width: 0;
		text-align: left;
	}
}

/* ── step 3: what deleting does, then the typed count ── */
.consequences {
	display: flex;
	flex-direction: column;
	gap: calc(var(--spacing) * 2.5);
	padding: calc(var(--spacing) * 3) calc(var(--spacing) * 3.5);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	font-size: 12.5px;
	line-height: 1.45;
	color: var(--fg-default-color);
}

.typed-confirm {
	display: flex;
	flex-direction: column;
	gap: calc(var(--spacing) * 2);
	padding: calc(var(--spacing) * 3) calc(var(--spacing) * 3.5);
	border: 1px solid rgb(var(--error-color-rgb) / 0.35);
	border-radius: var(--border-radius);
	background-color: rgb(var(--error-color-rgb) / 0.05);
}

.count-chip {
	margin-left: 4px;
	padding: 1px 7px;
	border-radius: var(--border-radius-small);
	background-color: rgb(var(--error-color-rgb) / 0.14);
	color: var(--error-color);
	font-family: var(--font-family-mono), monospace;
	font-variant-numeric: tabular-nums;
}

/* ── the last-seen column: each tool by name, then how long ago ── */
.seen {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 1px;
	font-size: 11px;
	line-height: 1.35;
}

.seen-line {
	display: flex;
	align-items: baseline;
	gap: 6px;
	white-space: nowrap;

	/* The theme bolds every dl dt and spaces it: here it is a quiet label beside its value. */
	dt {
		margin: 0;
		font-weight: 400;
		color: var(--fg-tertiary-color);
	}

	dd {
		min-width: 4.6em;
		margin: 0;
		font-family: var(--font-family-mono), monospace;
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
}

.outcome-tile {
	&.is-success {
		color: var(--success-color);
		background-color: rgb(var(--success-color-rgb) / 0.1);
		box-shadow: inset 0 0 0 1px rgb(var(--success-color-rgb) / 0.25);
	}
	&.is-warning {
		color: var(--warning-color);
		background-color: rgb(var(--warning-color-rgb) / 0.1);
		box-shadow: inset 0 0 0 1px rgb(var(--warning-color-rgb) / 0.25);
	}
	&.is-error {
		color: var(--error-color);
		background-color: rgb(var(--error-color-rgb) / 0.1);
		box-shadow: inset 0 0 0 1px rgb(var(--error-color-rgb) / 0.25);
	}
}

/* One outlined strip of figures, split by hairlines: a reading, not a set of cards. */
.stats {
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	overflow: hidden;
	transition: opacity 0.2s;

	&.is-stale {
		opacity: 0.55;
	}
}

.stat {
	display: flex;
	min-width: 0;
	flex-direction: column;
	/* A label that wraps keeps the figures on one baseline across the strip. */
	justify-content: space-between;
	gap: calc(var(--spacing) * 1);
	padding: calc(var(--spacing) * 2.5) calc(var(--spacing) * 3);
	/* Hairlines between cells whatever the wrap: each cell draws its right and bottom edge, the
	   strip's own border hides the outer ones. */
	box-shadow:
		1px 0 0 0 var(--border-color),
		0 1px 0 0 var(--border-color);
}

.stat-label {
	font-family: var(--font-family-mono), monospace;
	font-size: 10px;
	line-height: 1.4;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	color: var(--fg-tertiary-color);
}

.stats-split {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
}

/* A third of a phone is too narrow for "Seen by Velociraptor": the figures become rows. */
@container (max-width: 31.99rem) {
	.stats-split {
		grid-template-columns: minmax(0, 1fr);

		.stat {
			flex-direction: row;
			align-items: center;
			padding-block: calc(var(--spacing) * 2);
		}

		.stat-value {
			font-size: 1.125rem;
		}
	}
}

.stat-value {
	font-family: var(--font-family-mono), monospace;
	font-size: 1.5rem;
	line-height: 1.1;
	font-variant-numeric: tabular-nums;
	color: var(--fg-default-color);
}

.stat-value-sm {
	font-size: 1.125rem;
}

.stat-danger {
	background-color: rgb(var(--error-color-rgb) / 0.06);

	.stat-value {
		color: var(--error-color);
	}
}

.stat-warning .stat-value {
	color: var(--warning-color);
}

.stat-success .stat-value {
	color: var(--success-color);
}

.include-row {
	border: 1px solid rgb(var(--warning-color-rgb) / 0.35);
	background-color: rgb(var(--warning-color-rgb) / 0.05);
}

.callout {
	display: flex;
	align-items: flex-start;
	gap: calc(var(--spacing) * 2);
	padding: calc(var(--spacing) * 2.5) calc(var(--spacing) * 3);
	border-radius: var(--border-radius);
	font-size: 12px;
	line-height: 1.5;
	color: var(--fg-default-color);
}

.callout-warning {
	border: 1px solid rgb(var(--warning-color-rgb) / 0.35);
	background-color: rgb(var(--warning-color-rgb) / 0.07);

	> :first-child {
		color: var(--warning-color);
	}
}

.callout-error {
	align-items: center;
	border: 1px solid rgb(var(--error-color-rgb) / 0.35);
	background-color: rgb(var(--error-color-rgb) / 0.07);

	> :first-child {
		color: var(--error-color);
	}
}

.agent-list {
	border: 1px solid var(--border-color);
	background-color: var(--bg-default-color);
	/* The box draws the frame; NScrollbar inside it scrolls. */
	overflow: hidden;

	:deep(.n-scrollbar-container) {
		overscroll-behavior: contain;
	}
}

.agent-group + .agent-group {
	border-top: 1px solid var(--border-color);
}

.agent-group-header {
	position: sticky;
	top: 0;
	z-index: 1;
	background-color: var(--bg-secondary-color);
	border-bottom: 1px solid var(--border-color);
}

.agent-row {
	grid-template-columns: auto minmax(0, 1fr) auto;

	& + .agent-row {
		border-top: 1px solid rgb(var(--border-color-rgb) / 0.6);
	}
}

.progress-count {
	font-size: 1.5rem;
	line-height: 1;
	/* "0 / 14" is one reading: on a phone it must not break after the slash. */
	flex-shrink: 0;
	white-space: nowrap;
}

.presets :deep(.n-radio-button) {
	font-family: var(--font-family-mono), monospace;
	font-size: 12px;
}

/* A narrow dialog: the presets take the whole row, the custom value goes under them. */
@container (max-width: 31.99rem) {
	.presets {
		display: flex;
		width: 100%;
	}

	.presets :deep(.n-radio-button) {
		flex: 1 1 0;
		text-align: center;
	}
}

.outcome-tag {
	font-family: var(--font-family-mono), monospace;
	font-size: 10px;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	padding: 2px 6px;
	border-radius: var(--border-radius-small);
	white-space: nowrap;
	color: var(--fg-secondary-color);
	background-color: rgb(var(--hover-color-rgb) / 0.5);

	&.is-danger {
		color: var(--error-color);
		background-color: rgb(var(--error-color-rgb) / 0.1);
	}

	&.is-warning {
		color: var(--warning-color);
		background-color: rgb(var(--warning-color-rgb) / 0.12);
	}
}
</style>
