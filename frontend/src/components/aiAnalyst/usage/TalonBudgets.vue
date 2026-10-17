<template>
	<div class="flex flex-col gap-4" data-testid="talon-budgets">
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Set a customer's budget</span>
				<n-select
					v-model:value="pick"
					:options="customerOptions"
					:loading="customersLoading"
					placeholder="Customer"
					filterable
					size="small"
					class="w-64"
					data-testid="talon-budgets-pick"
				/>
			</label>
			<n-button size="small" :disabled="!pick" data-testid="talon-budgets-pick-edit" @click="pick && edit(pick)">
				Edit
			</n-button>
			<n-button size="small" :loading data-testid="talon-budgets-refresh" @click="load()">Refresh</n-button>
		</div>

		<n-alert v-if="failure" type="error" :bordered="false" size="small" data-testid="talon-budgets-error">
			{{ failure.detail }}
		</n-alert>
		<n-alert v-if="savedNote" type="success" :bordered="false" size="small" closable @close="savedNote = null">
			{{ savedNote }}
		</n-alert>

		<n-spin :show="loading">
			<n-table v-if="budgets" size="small" :bordered="false" data-testid="talon-budgets-table">
				<thead>
					<tr>
						<th>Budget</th>
						<th>Window</th>
						<th>Limit</th>
						<th>Source</th>
						<th class="text-right">Spent (USD)</th>
						<th class="text-right">Remaining (USD)</th>
						<th>State</th>
						<th />
					</tr>
				</thead>
				<tbody>
					<template v-for="customerBudget of budgets.customers" :key="customerBudget.customer_code">
						<tr
							v-for="(win, index) of windowsOf(customerBudget)"
							:key="win.name"
							data-testid="talon-budget-row"
							:data-customer="customerBudget.customer_code"
							:data-window="win.name"
						>
							<td v-if="index === 0" rowspan="2" class="font-mono break-all">
								<bdi>{{ customerBudget.customer_code }}</bdi>
							</td>
							<td>{{ win.label }}</td>
							<td class="font-mono" data-testid="talon-budget-limit">{{ limitText(win.entry) }}</td>
							<td>{{ SOURCE_LABELS[win.entry.source] ?? win.entry.source }}</td>
							<td class="text-right font-mono" data-testid="talon-budget-spent">
								{{ win.entry.spent_usd ?? "—" }}
							</td>
							<td class="text-right font-mono" data-testid="talon-budget-remaining">
								{{ win.entry.remaining_usd ?? "—" }}
							</td>
							<td>
								<TalonBudgetState :entry="win.entry" />
							</td>
							<td v-if="index === 0" rowspan="2" class="text-right">
								<n-button
									size="tiny"
									secondary
									data-testid="talon-budget-edit"
									@click="edit(customerBudget.customer_code)"
								>
									Edit
								</n-button>
							</td>
						</tr>
					</template>
					<tr v-if="!budgets.customers.length">
						<td colspan="8" class="text-secondary text-sm" data-testid="talon-budgets-none">
							No customer has an override or spend this month. Pick one above to set its budget.
						</td>
					</tr>
					<tr data-testid="talon-budget-own-chat">
						<td>Your chat</td>
						<td>Daily</td>
						<td class="font-mono">{{ limitText(budgets.user.daily) }}</td>
						<td>{{ SOURCE_LABELS[budgets.user.daily.source] ?? budgets.user.daily.source }}</td>
						<td class="text-right font-mono">{{ budgets.user.daily.spent_usd ?? "—" }}</td>
						<td class="text-right font-mono">{{ budgets.user.daily.remaining_usd ?? "—" }}</td>
						<td><TalonBudgetState :entry="budgets.user.daily" /></td>
						<td />
					</tr>
					<tr v-if="budgets.general" data-testid="talon-budget-general-chat">
						<td>General chat (all users)</td>
						<td>Daily</td>
						<td class="font-mono">{{ limitText(budgets.general.daily) }}</td>
						<td>{{ SOURCE_LABELS[budgets.general.daily.source] ?? budgets.general.daily.source }}</td>
						<td class="text-right font-mono">{{ budgets.general.daily.spent_usd ?? "—" }}</td>
						<td class="text-right font-mono">{{ budgets.general.daily.remaining_usd ?? "—" }}</td>
						<td><TalonBudgetState :entry="budgets.general.daily" /></td>
						<td />
					</tr>
				</tbody>
			</n-table>
		</n-spin>
		<p class="text-secondary text-xs">
			Chat budgets are set on talon-analyst (TALON_BUDGET_USER_DAILY_USD, TALON_BUDGET_GENERAL_DAILY_USD). A
			warning shows at {{ warnAt }} of a limit.
		</p>

		<TalonBudgetDialog
			v-if="editing"
			:show="!!editing"
			:customer-code="editing"
			:current="currentOf(editing)"
			@close="editing = null"
			@saved="saved"
			@loaded="replaceRow"
		/>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Budgets tab (decision B: admins only; CoPilot refuses anyone else too, by
// the database role): `GET /api/talon/v2/budgets` for every customer's daily and monthly ceiling,
// where it comes from, spent and remaining (the API's strings), with warning and exhausted tags,
// plus the caller's own and general chat's; an edit dialog per customer.
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import type { TalonBudgetEntry, TalonBudgets, TalonCustomerBudget } from "@/types/talonUsage"
import { NAlert, NButton, NSelect, NSpin, NTable, NTag } from "naive-ui"
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { limitText, SOURCE_LABELS, warnAtPercent } from "./budgets"
import TalonBudgetDialog from "./TalonBudgetDialog.vue"

const TalonBudgetState = defineComponent({
	props: { entry: { type: Object as () => TalonBudgetEntry, required: true } },
	setup: props => () =>
		props.entry.exhausted
			? h(NTag, { type: "error", size: "small", "data-testid": "talon-budget-exhausted" }, () => "Exhausted")
			: props.entry.warning
				? h(NTag, { type: "warning", size: "small", "data-testid": "talon-budget-warning" }, () => "Warning")
				: null
})

const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()

const budgets = ref<TalonBudgets | null>(null)
const failure = ref<TalonFailure | null>(null)
const loading = ref(false)
const pick = ref<string | null>(null)
const editing = ref<string | null>(null)
const savedNote = ref<string | null>(null)
let controller: AbortController | null = null

const warnAt = computed(() => warnAtPercent(budgets.value?.warn_at))

function windowsOf(entry: TalonCustomerBudget) {
	return [
		{ name: "daily", label: "Daily", entry: entry.daily },
		{ name: "monthly", label: "Monthly", entry: entry.monthly }
	]
}

function currentOf(code: string): TalonCustomerBudget | null {
	return budgets.value?.customers.find(c => c.customer_code === code) ?? null
}

function edit(code: string) {
	savedNote.value = null
	editing.value = code
}

/** Put one customer's budgets in the table, in code order. */
function replaceRow(report: TalonCustomerBudget) {
	if (budgets.value) {
		const others = budgets.value.customers.filter(c => c.customer_code !== report.customer_code)
		budgets.value.customers = [...others, report].sort((a, b) =>
			a.customer_code < b.customer_code ? -1 : a.customer_code > b.customer_code ? 1 : 0
		)
	}
}

function saved(report: TalonCustomerBudget) {
	replaceRow(report)
	savedNote.value = `Budgets of ${report.customer_code} saved.`
	editing.value = null
}

async function load() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	try {
		const res = await Api.talonUsage.getBudgets(null, own.signal)
		if (controller === own) budgets.value = res.data
	} catch (err) {
		if (controller === own && !own.signal.aborted) {
			budgets.value = null
			failure.value = talonFailure(err)
		}
	} finally {
		if (controller === own) loading.value = false
	}
}

onMounted(() => {
	load()
	loadCustomers()
})
onBeforeUnmount(() => controller?.abort())
</script>
