<template>
	<div class="flex flex-col gap-3" data-testid="talon-approvals">
		<div class="flex flex-wrap items-center gap-3">
			<SegmentedToggle
				v-model="scope"
				:options="[
					{ value: 'pending', label: 'Pending' },
					{ value: 'mine', label: 'Mine' }
				]"
				label="Show"
				test-id="talon-approvals-scope"
			/>
			<span class="text-tertiary grow text-xs">
				{{
					scope === "pending"
						? "Talon's proposals you may decide now, and your own that wait."
						: "Every proposal Talon made in your threads."
				}}
			</span>
			<n-button size="tiny" secondary :loading data-testid="talon-approvals-refresh" @click="reload()">
				Refresh
			</n-button>
		</div>

		<n-alert v-if="error" type="error" :bordered="false" class="text-sm" data-testid="talon-approvals-error">
			{{ error }}
		</n-alert>

		<div v-if="loading && !rows.length" class="flex items-center justify-center gap-2 py-8">
			<n-spin size="small" />
		</div>
		<div
			v-else-if="!rows.length"
			class="text-tertiary py-8 text-center text-sm"
			data-testid="talon-approvals-empty"
		>
			{{
				scope === "pending"
					? "Nothing waits for a decision."
					: "Talon hasn't proposed anything in your threads."
			}}
		</div>

		<div v-else class="flex flex-col gap-2" data-testid="talon-approvals-list">
			<div
				v-for="row of rows"
				:key="row.id"
				role="button"
				tabindex="0"
				class="border-default hover:bg-secondary flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 rounded-md border px-3 py-2 text-sm"
				data-testid="talon-approvals-row"
				:data-approval-id="row.id"
				:data-state="row.state"
				@click="open(row.id)"
				@keydown.enter.prevent="open(row.id)"
				@keydown.space.prevent="open(row.id)"
			>
				<span class="font-semibold" data-testid="talon-approvals-row-action">
					{{ actionLabel(row.action) }}
				</span>
				<n-tag
					v-if="endpointKind(row)"
					size="small"
					:type="endpointKind(row)?.kind === 'command' ? 'warning' : 'info'"
					:bordered="false"
					data-testid="talon-approvals-row-kind"
					:data-kind="endpointKind(row)?.kind"
				>
					{{ endpointKind(row)?.label }}
					<template v-if="endpointKind(row)?.detail">
						·
						<TalonUntrusted class="font-mono" :text="endpointKind(row)?.detail" />
					</template>
				</n-tag>
				<span class="text-secondary font-mono" data-testid="talon-approvals-row-target">
					<TalonUntrusted :text="targetOf(row)" />
				</span>
				<n-tag size="small" :bordered="false" data-testid="talon-approvals-row-customer">
					<TalonUntrusted :text="row.customer_code" />
				</n-tag>
				<n-tag
					v-if="hiddenIn(row)"
					size="small"
					type="error"
					:bordered="false"
					data-testid="talon-approvals-row-hidden"
				>
					Hidden characters
				</n-tag>
				<span class="grow" />
				<n-tag
					v-if="row.can_decide"
					size="small"
					type="warning"
					:bordered="false"
					data-testid="talon-approvals-row-decide"
				>
					You can decide
				</n-tag>
				<n-tag v-if="row.is_requester" size="small" :bordered="false" data-testid="talon-approvals-row-mine">
					Yours
				</n-tag>
				<span class="text-tertiary text-xs" data-testid="talon-approvals-row-status">
					{{ stateLabel(row) }}
				</span>
			</div>
		</div>

		<n-modal
			:show="!!openId"
			preset="card"
			title="Action proposal"
			:style="{ maxWidth: 'min(640px, 94vw)' }"
			segmented
			data-testid="talon-approvals-modal"
			@update:show="value => !value && close()"
		>
			<TalonApprovalCard v-if="openId" :key="openId" :approval-id="openId" @changed="onChanged" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Approvals tab (plan M5-11b, decision b; behind the "Talon v2" setting):
// Talon's chat action proposals waiting in CoPilot, from CoPilot's mirror. "Pending" is the shared,
// polled list (`useTalonApprovals`): what the user may decide now and their own that wait. "Mine"
// is every proposal of theirs, read when shown. A row opens its approval card, which reads the
// record from talon-analyst again and decides it. A collection or a command (EA-4) shows its kind,
// with the artifact or the shell. Every value is text.
import type { TalonAction, TalonActionScope } from "@/types/talonActions"
import axios from "axios"
import { NAlert, NButton, NModal, NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import { TALON_V2_FAILED } from "@/api/talonV2Parser"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import { refreshApprovals, useTalonApprovals } from "@/composables/useTalonApprovals"
import { actionLabel, endpointKind, hasHiddenChars, isHostAction, stateLabel } from "./approvals"
import TalonApprovalCard from "./TalonApprovalCard.vue"
import TalonUntrusted from "./TalonUntrusted"

const scope = ref<TalonActionScope>("pending")
const openId = ref<string | null>(null)
const pending = useTalonApprovals()
const mine = ref<TalonAction[]>([])
const mineLoading = ref(false)
const mineError = ref<string | null>(null)
let mineController: AbortController | null = null

const rows = computed(() => (scope.value === "pending" ? pending.actions.value : mine.value))
const loading = computed(() =>
	scope.value === "pending" ? !pending.loaded.value && !pending.error.value : mineLoading.value
)
const error = computed(() => (scope.value === "pending" ? pending.error.value : mineError.value))

function targetOf(row: TalonAction): string {
	const target = row.target ?? {}
	if (isHostAction(row)) return typeof target.hostname === "string" ? target.hostname : "a host"
	return typeof target.alert_id === "number" ? `alert #${target.alert_id}` : "an alert"
}

/** The row's values hold invisible or direction-changing characters (its card says which). */
function hiddenIn(row: TalonAction): boolean {
	const values = [row.customer_code, row.reason, ...Object.values(row.target ?? {}), ...Object.values(row.args ?? {})]
	return values.some(
		value =>
			(typeof value === "string" && hasHiddenChars(value)) ||
			// A collection's parameters (`{env: [{key, value}]}`): JSON keeps format characters as they are.
			(!!value && typeof value === "object" && hasHiddenChars(JSON.stringify(value)))
	)
}

async function loadMine() {
	mineController?.abort()
	const own = new AbortController()
	mineController = own
	mineLoading.value = true
	try {
		const res = await Api.talonActions.list("mine", own.signal)
		if (own.signal.aborted) return
		mine.value = Array.isArray(res.data?.actions) ? res.data.actions : []
		mineError.value = null
	} catch (err) {
		if (own.signal.aborted || axios.isCancel(err)) return
		mineError.value = axios.isAxiosError(err) ? refusalDetail(err.response?.data) : TALON_V2_FAILED
	} finally {
		if (mineController === own) {
			mineController = null
			mineLoading.value = false
		}
	}
}

function reload() {
	if (scope.value === "pending") refreshApprovals()
	else loadMine()
}

function open(id: string) {
	openId.value = id
}

function close() {
	openId.value = null
	reload()
}

/** The open card's proposal moved: the lists follow (it may have left "Pending"). */
function onChanged() {
	refreshApprovals()
	if (scope.value === "mine") loadMine()
}

watch(scope, value => {
	if (value === "mine") loadMine()
})

onBeforeUnmount(() => mineController?.abort())
</script>
