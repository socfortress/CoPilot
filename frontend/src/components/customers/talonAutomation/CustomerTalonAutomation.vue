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
			would-have-run list before switching a level to auto. Shadow is optional.
		</n-alert>

		<n-alert v-if="failure" type="error" :bordered="false" size="small" data-testid="automation-error">
			{{ failure.detail }}
		</n-alert>

		<n-spin :show="loading">
			<div v-if="policy" class="flex flex-col gap-4">
				<n-alert
					v-if="!policy.automation_enabled"
					type="warning"
					:bordered="false"
					size="small"
					data-testid="automation-switch-off"
				>
					The global automation switch (AI Analyst, Settings) is off: nothing starts for any customer,
					whatever this policy says.
				</n-alert>
				<n-alert
					v-if="!policy.service_user_assigned"
					type="warning"
					:bordered="false"
					size="small"
					data-testid="automation-unassigned"
				>
					The Talon service user isn't assigned this customer, so CoPilot refuses to raise any level. Assign
					it first.
				</n-alert>

				<n-card
					v-for="level of AUTOMATION_LEVELS"
					:key="level"
					size="small"
					:data-testid="`automation-level-${level}`"
				>
					<div class="flex flex-col gap-3">
						<div class="flex flex-wrap items-center gap-2">
							<span class="font-semibold">Level {{ level }}: {{ LEVEL_TEXT[level].title }}</span>
							<n-tag
								v-if="!policy.startable_levels.includes(level)"
								size="small"
								:bordered="false"
								:data-testid="`automation-level-${level}-unavailable`"
							>
								Not available yet
							</n-tag>
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
						<p v-if="!policy.startable_levels.includes(level)" class="text-secondary text-xs">
							CoPilot can't start this level's automated actions yet: its mode is saved, and an auto start
							is refused until a later release.
						</p>
						<p v-if="level === 2" class="text-secondary text-xs">
							Level 2's artifact list and file path rules are not edited on this tab yet ({{
								policy.level_2_artifacts?.length ?? 0
							}}
							artifacts stored); they are kept as they are when you save.
						</p>
					</div>
				</n-card>

				<n-card size="small" title="Caps" data-testid="automation-caps">
					<p class="text-secondary mb-3 text-sm">
						You can only lower a cap below its default; leave the field empty to keep the default. CoPilot
						enforces the caps marked "Enforced" today; the others are stored for the levels that use them.
					</p>
					<n-table size="small" :bordered="false">
						<thead>
							<tr>
								<th>Cap</th>
								<th class="text-right">Default</th>
								<th>Override</th>
								<th class="text-right">In force</th>
								<th />
							</tr>
						</thead>
						<tbody>
							<tr v-for="name of capNames" :key="name" :data-testid="`automation-cap-${name}`">
								<td>
									<div>{{ capLabel(name) }}</div>
									<div class="text-secondary font-mono text-xs">{{ name }}</div>
								</td>
								<td class="text-right font-mono">{{ policy.cap_defaults[name] }}</td>
								<td>
									<n-input-number
										v-model:value="capOverrides[name]"
										size="small"
										clearable
										:min="0"
										:max="policy.cap_defaults[name]"
										:precision="0"
										:placeholder="String(policy.cap_defaults[name])"
										:disabled="saving"
										class="w-40"
										:data-testid="`automation-cap-${name}-override`"
									/>
								</td>
								<td class="text-right font-mono">{{ policy.effective_caps[name] }}</td>
								<td>
									<n-tag
										v-if="policy.enforced_caps.includes(name)"
										size="small"
										type="info"
										:bordered="false"
									>
										Enforced
									</n-tag>
								</td>
							</tr>
						</tbody>
					</n-table>
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
							Version {{ policy.version }}, last changed
							{{ formatDate(policy.updated_at, dFormats.datetime) }}
							<template v-if="policy.updated_by_username">by {{ policy.updated_by_username }}</template>
						</span>
						<span v-if="policy.risk_acknowledged_at" data-testid="automation-risk-recorded">
							Risk of levels 3–4 acknowledged
							{{ formatDate(policy.risk_acknowledged_at, dFormats.datetime) }}
							<template v-if="policy.risk_acknowledged_by_username">
								by {{ policy.risk_acknowledged_by_username }}
							</template>
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
			:risk-text="policy?.risk_acknowledgement_text ?? ''"
			:saving
			@cancel="riskLevels = []"
			@confirm="save(true)"
		/>
	</div>
</template>

<script setup lang="ts">
// The customer's "AI Automation" tab (talon-analyst D85, plan AP-2 frontend; CoPilot's
// `GET`/`PUT /api/talon/v2/automation/{customer_code}`): each level's mode, any mode selectable
// directly (Q2), with shadow suggested; the caps CoPilot reports; the would-have-run list's place
// (AP-4). Raising level 3 or 4 asks for CoPilot's honest-risk acknowledgement first (Q7). Admins
// only: the tab is hidden for anyone else, and CoPilot refuses anyone else by the database role.
import type {
	TalonAutomationLevel,
	TalonAutomationMode,
	TalonAutomationModes,
	TalonAutomationPolicy
} from "@/api/endpoints/talonAutomation"
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

/** The caps as CoPilot names them, in its order. */
const capNames = computed(() => Object.keys(policy.value?.cap_defaults ?? {}))

function storedOverride(name: string): number | null {
	return policy.value?.caps?.[name] ?? null
}

function reset() {
	const current = policy.value
	if (!current) return
	Object.assign(modes, modesOf(current))
	for (const name of Object.keys(capOverrides)) delete capOverrides[name]
	for (const name of capNames.value) capOverrides[name] = storedOverride(name)
}

const dirty = computed(() => {
	const current = policy.value
	if (!current) return false
	if (AUTOMATION_LEVELS.some(level => modes[modeKey(level)] !== current[modeKey(level)])) return true
	return capNames.value.some(name => (capOverrides[name] ?? null) !== storedOverride(name))
})

const capsValid = computed(() =>
	capNames.value.every(name => {
		const value = capOverrides[name]
		const max = policy.value?.cap_defaults[name]
		return value === null || value === undefined || (max !== undefined && value >= 0 && value <= max)
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
		policy.value = res.data
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
		policy.value = res.data
		reset()
		message.success("Automation policy saved")
	} catch (err) {
		// The edit stays; a 409 (another admin's change, or the service user unassigned) says so.
		failure.value = talonFailure(err)
	} finally {
		riskLevels.value = []
		saving.value = false
	}
}

watch(() => customerCode, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
