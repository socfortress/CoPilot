<template>
	<div class="flex flex-col gap-4" data-testid="customer-talon-automation">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">AI Analyst automation</h3>
			<p class="text-secondary text-sm">
				What the AI Analyst's automatic investigations may run on an alert's own host for this customer. Chat
				never runs anything automatically.
			</p>
		</div>

		<n-alert type="info" :bordered="false" size="small" data-testid="automation-help">
			Every level starts off, and you can pick any mode directly. We suggest
			<b>shadow</b>
			first: it runs every check and records what would have run, without running anything, so you can review the
			would-have-run list before switching a level to auto. Shadow is optional. Nothing runs while the global
			automation switch on the AI Analyst page's Settings tab is off.
		</n-alert>

		<n-alert v-if="failure" type="error" :bordered="false" size="small" data-testid="automation-error">
			{{ failure.detail }}
		</n-alert>

		<n-spin :show="loading">
			<div v-if="policy" class="flex flex-col gap-4">
				<n-card
					v-for="level of AUTOMATION_LEVELS"
					:key="level"
					size="small"
					:data-testid="`automation-level-${level}`"
				>
					<div class="flex flex-col gap-3">
						<div class="flex flex-wrap items-center gap-2">
							<span class="font-semibold">Level {{ level }}: {{ LEVEL_TEXT[level].title }}</span>
							<n-tag v-if="RISK_LEVELS.includes(level)" size="small" type="warning" :bordered="false">
								Needs a risk acknowledgement
							</n-tag>
						</div>
						<p class="text-secondary text-sm">{{ LEVEL_TEXT[level].detail }}</p>
						<n-radio-group
							:value="modes[modeKey(level)]"
							size="small"
							:name="`automation-level-${level}-mode`"
							:disabled="saving"
							@update:value="(mode: TalonAutomationMode) => (modes[modeKey(level)] = mode)"
						>
							<n-radio-button
								v-for="mode of AUTOMATION_MODES"
								:key="mode"
								:value="mode"
								:data-testid="`automation-level-${level}-${mode}`"
							>
								{{ MODE_TEXT[mode].label }}
							</n-radio-button>
						</n-radio-group>
						<p class="text-secondary text-xs" :data-testid="`automation-level-${level}-mode-text`">
							{{ MODE_TEXT[modes[modeKey(level)]].detail }}
						</p>
						<p v-if="level === 2" class="text-secondary text-xs">
							Level 2's artifact list and file path rules are not edited on this tab yet ({{
								policy.level_2_artifacts.length
							}}
							artifacts chosen); they are kept as they are when you save.
						</p>
					</div>
				</n-card>

				<n-card size="small" title="Caps" data-testid="automation-caps">
					<p class="text-secondary mb-3 text-sm">
						Caps apply in both Talon and CoPilot. You can only lower a cap below its default; leave the
						field empty to keep the default.
					</p>
					<n-table v-if="capKeys.length" size="small" :bordered="false">
						<thead>
							<tr>
								<th>Cap</th>
								<th>Window</th>
								<th class="text-right">Default</th>
								<th>Override</th>
								<th class="text-right">In force</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="key of capKeys" :key :data-testid="`automation-cap-${key}`">
								<td>{{ capLabel(key).label }}</td>
								<td class="text-secondary">{{ capLabel(key).unit }}</td>
								<td class="text-right font-mono">{{ policy.caps[key]?.default }}</td>
								<td>
									<n-input-number
										v-model:value="capOverrides[key]"
										size="small"
										clearable
										:min="0"
										:max="policy.caps[key]?.default"
										:precision="0"
										:placeholder="String(policy.caps[key]?.default ?? '')"
										:disabled="saving"
										class="w-32"
										:data-testid="`automation-cap-${key}-override`"
									/>
								</td>
								<td class="text-right font-mono">{{ policy.caps[key]?.effective }}</td>
							</tr>
						</tbody>
					</n-table>
					<p v-else class="text-secondary text-sm">CoPilot reported no caps.</p>
				</n-card>

				<n-card size="small" title="Would-have-run" data-testid="automation-would-have-run">
					<p class="text-secondary text-sm">
						The list of what shadow mode would have run, with counts per level and an optional "reviewed"
						mark, arrives in a later release. It is information only: it never gates switching a level to
						auto.
					</p>
				</n-card>

				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="text-secondary flex flex-col gap-1 text-xs">
						<span v-if="!policy.exists" data-testid="automation-no-row">
							No policy saved for this customer yet: every level is off.
						</span>
						<span v-if="policy.updated_at">
							Last changed {{ formatDate(policy.updated_at, dFormats.datetime) }}
							<template v-if="policy.updated_by">by {{ policy.updated_by }}</template>
						</span>
						<span v-if="policy.risk_acknowledged_at" data-testid="automation-risk-recorded">
							Risk of levels 3–4 acknowledged
							{{ formatDate(policy.risk_acknowledged_at, dFormats.datetime) }}
							<template v-if="policy.risk_acknowledged_by">by {{ policy.risk_acknowledged_by }}</template>
						</span>
					</div>
					<div class="flex gap-2">
						<n-button
							size="small"
							:disabled="!dirty || saving"
							data-testid="automation-reset"
							@click="reset()"
						>
							Reset
						</n-button>
						<n-button
							size="small"
							type="primary"
							:disabled="!dirty || !capsValid"
							:loading="saving && !riskLevels.length"
							data-testid="automation-save"
							@click="requestSave()"
						>
							Save
						</n-button>
					</div>
				</div>
			</div>
		</n-spin>

		<TalonAutomationRiskDialog
			:show="riskLevels.length > 0"
			:customer-code
			:levels="riskLevels"
			:saving
			@cancel="riskLevels = []"
			@confirm="save(true)"
		/>
	</div>
</template>

<script setup lang="ts">
import type {
	TalonAutomationLevel,
	TalonAutomationMode,
	TalonAutomationModes,
	TalonAutomationPolicy
} from "@/api/endpoints/talonAutomation"
// The customer's "AI Automation" tab (talon-analyst D85, plan AP-2 frontend): each level's mode,
// any mode selectable directly (Q2), with shadow suggested; the caps; the would-have-run list's
// place (AP-4). Raising level 3 or 4 asks for the honest-risk acknowledgement first (Q7). Admins
// only: the tab is hidden for anyone else, and CoPilot refuses anyone else by the database role.
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import {
	NAlert,
	NButton,
	NCard,
	NInputNumber,
	NRadioButton,
	NRadioGroup,
	NSpin,
	NTable,
	NTag,
	useMessage
} from "naive-ui"
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue"
import Api from "@/api"
import {
	AUTOMATION_LEVELS,
	AUTOMATION_MODES,
	buildPolicyUpdate,
	modeKey,
	modesOf,
	RISK_LEVELS,
	riskRaises
} from "@/api/endpoints/talonAutomation"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { capLabel, LEVEL_TEXT, MODE_TEXT } from "./automation"
import TalonAutomationRiskDialog from "./TalonAutomationRiskDialog.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const saving = ref(false)
const failure = ref<TalonFailure | null>(null)
const policy = ref<TalonAutomationPolicy | null>(null)

const modes = reactive<TalonAutomationModes>({
	level_1_mode: "off",
	level_2_mode: "off",
	level_3_mode: "off",
	level_4_mode: "off"
})
const capOverrides = reactive<Record<string, number | null>>({})
/** The levels 3–4 a pending save raises: non-empty while the risk dialog is open. */
const riskLevels = ref<TalonAutomationLevel[]>([])

const capKeys = computed(() => Object.keys(policy.value?.caps ?? {}))

function reset() {
	const current = policy.value
	if (!current) return
	Object.assign(modes, modesOf(current))
	for (const key of Object.keys(capOverrides)) delete capOverrides[key]
	for (const [key, cap] of Object.entries(current.caps)) capOverrides[key] = cap.override ?? null
}

const dirty = computed(() => {
	const current = policy.value
	if (!current) return false
	if (AUTOMATION_LEVELS.some(level => modes[modeKey(level)] !== current[modeKey(level)])) return true
	return capKeys.value.some(key => (capOverrides[key] ?? null) !== (current.caps[key]?.override ?? null))
})

const capsValid = computed(() =>
	capKeys.value.every(key => {
		const value = capOverrides[key]
		const cap = policy.value?.caps[key]
		return value === null || value === undefined || (cap !== undefined && value >= 0 && value <= cap.default)
	})
)

let controller: AbortController | null = null

async function load() {
	controller?.abort()
	controller = new AbortController()
	const signal = controller.signal
	loading.value = true
	failure.value = null
	try {
		const res = await Api.talonAutomation.getPolicy(customerCode, signal)
		policy.value = res.data.policy
		reset()
	} catch (err) {
		if (signal.aborted) return
		failure.value = talonFailure(err)
	} finally {
		if (!signal.aborted) loading.value = false
	}
}

function requestSave() {
	const current = policy.value
	if (!current || !dirty.value || !capsValid.value) return
	const raised = riskRaises(modesOf(current), modesOf(modes))
	if (raised.length) {
		riskLevels.value = raised
		return
	}
	save(false)
}

async function save(acknowledgeRisk: boolean) {
	const current = policy.value
	if (!current || saving.value) return
	saving.value = true
	failure.value = null
	try {
		const body = buildPolicyUpdate(current, modes, capOverrides, acknowledgeRisk)
		const res = await Api.talonAutomation.putPolicy(customerCode, body)
		policy.value = res.data.policy
		reset()
		riskLevels.value = []
		message.success("Automation policy saved")
	} catch (err) {
		failure.value = talonFailure(err)
		riskLevels.value = []
	} finally {
		saving.value = false
	}
}

watch(() => customerCode, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
