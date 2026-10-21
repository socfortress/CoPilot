<template>
	<n-modal
		:show
		preset="card"
		:title="`Talon budget: ${customerCode}`"
		class="max-w-lg"
		:mask-closable="!saving"
		:closable="!saving"
		data-testid="talon-budget-dialog"
		@update:show="value => !value && close()"
	>
		<div v-if="step === 'edit'" class="flex flex-col gap-4">
			<p v-if="reading" class="text-secondary text-xs" data-testid="talon-budget-reading">
				Reading the current budgets...
			</p>
			<n-alert v-if="readError" type="error" :bordered="false" size="small" data-testid="talon-budget-read-error">
				{{ readError }}
			</n-alert>
			<div
				v-for="win of WINDOWS"
				:key="win.key"
				class="flex flex-col gap-2"
				:data-testid="`talon-budget-${win.key}`"
			>
				<div class="text-sm font-semibold">{{ win.label }}</div>
				<n-radio-group
					v-model:value="forms[win.key].choice"
					size="small"
					:name="`talon-budget-${win.key}-choice`"
				>
					<n-radio value="default">Default</n-radio>
					<n-radio value="unlimited">Unlimited</n-radio>
					<n-radio value="amount">Amount</n-radio>
				</n-radio-group>
				<n-input
					v-if="forms[win.key].choice === 'amount'"
					v-model:value="forms[win.key].amount"
					size="small"
					placeholder="USD, such as 25 or 12.50"
					:status="problems[win.key] ? 'error' : undefined"
					:data-testid="`talon-budget-${win.key}-amount`"
				/>
				<p v-if="problems[win.key]" class="text-error text-xs" :data-testid="`talon-budget-${win.key}-problem`">
					{{ problems[win.key] }}
				</p>
			</div>
			<p class="text-secondary text-xs">
				"Default" follows talon-analyst's TALON_BUDGET_DAILY_USD / TALON_BUDGET_MONTHLY_USD; "Unlimited" sets no
				ceiling for this customer. Both windows are saved together.
			</p>
			<div class="flex justify-end gap-2">
				<n-button size="small" @click="close()">Cancel</n-button>
				<n-button
					size="small"
					type="primary"
					:disabled="invalid"
					data-testid="talon-budget-save"
					@click="step = 'confirm'"
				>
					Save
				</n-button>
			</div>
		</div>

		<div v-else class="flex flex-col gap-4" data-testid="talon-budget-confirm">
			<p class="text-sm">
				Set the Talon budgets of
				<b>{{ customerCode }}</b>
				<span>?</span>
				This change is audited.
			</p>
			<ul class="flex flex-col gap-1 text-sm">
				<li>
					Daily:
					<b data-testid="talon-budget-confirm-daily">{{ describeWindow(forms.daily) }}</b>
				</li>
				<li>
					Monthly:
					<b data-testid="talon-budget-confirm-monthly">{{ describeWindow(forms.monthly) }}</b>
				</li>
			</ul>
			<n-alert v-if="error" type="error" :bordered="false" size="small" data-testid="talon-budget-error">
				{{ error }}
			</n-alert>
			<div class="flex justify-end gap-2">
				<n-button size="small" :disabled="saving" @click="step = 'edit'">Back</n-button>
				<n-button
					size="small"
					type="primary"
					:loading="saving"
					data-testid="talon-budget-confirm-button"
					@click="save()"
				>
					Confirm
				</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
// The Budgets tab's edit dialog: each window "Default", "Unlimited" or an amount (a positive decimal
// string, checked as CoPilot checks it), then a confirmation naming both, then
// `PUT /api/talon/v2/budgets/{code}` with both windows (the PUT replaces both). Opening it re-reads
// that customer's budgets (`GET /budgets?customer_code=`) and starts from them, so a change another
// admin made since the table loaded is what is edited, never silently replaced; Save waits for it.
import type { BudgetWindowForm } from "./budgets"
import type { TalonBudgetEntry, TalonCustomerBudget } from "@/types/talonUsage"
import { NAlert, NButton, NInput, NModal, NRadio, NRadioGroup } from "naive-ui"
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { budgetPayload, describeWindow, windowFormFromEntry, windowProblem } from "./budgets"

const props = defineProps<{
	show: boolean
	customerCode: string
	current: TalonCustomerBudget | null
}>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "saved", value: TalonCustomerBudget): void
	/** The customer's budgets as just re-read, for the table. */
	(e: "loaded", value: TalonCustomerBudget): void
}>()

type WindowKey = "daily" | "monthly"
const WINDOWS: { key: WindowKey; label: string }[] = [
	{ key: "daily", label: "Daily (UTC day)" },
	{ key: "monthly", label: "Monthly (UTC month)" }
]

const forms = reactive<Record<WindowKey, BudgetWindowForm>>({
	daily: windowFormFromEntry(null),
	monthly: windowFormFromEntry(null)
})
const step = ref<"edit" | "confirm">("edit")
const saving = ref(false)
const error = ref<string | null>(null)
const reading = ref(false)
const readError = ref<string | null>(null)
let readController: AbortController | null = null

const problems = computed(() => ({ daily: windowProblem(forms.daily), monthly: windowProblem(forms.monthly) }))
const invalid = computed(() => !!problems.value.daily || !!problems.value.monthly || reading.value || !!readError.value)

function reset(entry: { daily?: TalonBudgetEntry; monthly?: TalonBudgetEntry } | null) {
	Object.assign(forms.daily, windowFormFromEntry(entry?.daily))
	Object.assign(forms.monthly, windowFormFromEntry(entry?.monthly))
	step.value = "edit"
	error.value = null
	saving.value = false
}

/** The customer's budgets now, as the form's starting point. */
async function reread(code: string) {
	readController?.abort()
	const own = new AbortController()
	readController = own
	reading.value = true
	readError.value = null
	try {
		const res = await Api.talonUsage.getBudgets(code, own.signal)
		if (readController !== own) return
		const fresh = res.data?.customers?.find(c => c.customer_code === code) ?? null
		reset(fresh)
		if (fresh) emit("loaded", fresh)
	} catch (err) {
		if (readController === own && !own.signal.aborted) {
			readError.value = `The current budgets couldn't be read: ${talonFailure(err).detail}`
		}
	} finally {
		if (readController === own) reading.value = false
	}
}

watch(
	() => [props.show, props.customerCode] as const,
	([show, code]) => {
		if (!show) return
		reset(props.current)
		reread(code)
	},
	{ immediate: true }
)
onBeforeUnmount(() => readController?.abort())

function close() {
	if (!saving.value) emit("close")
}

async function save() {
	if (invalid.value || saving.value) return
	saving.value = true
	error.value = null
	try {
		const res = await Api.talonUsage.putBudget(props.customerCode, budgetPayload(forms.daily, forms.monthly))
		saving.value = false
		emit("saved", res.data)
	} catch (err) {
		saving.value = false
		error.value = talonFailure(err).detail
	}
}
</script>
