<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">AI Report</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can read the AI Analyst findings produced for their alerts,
				and whether they can ask for one
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Show AI Analyst findings in the Customer Portal</div>
							<div class="text-secondary text-sm">
								{{
									enabled
										? "Portal users of this customer can see the AI investigation results."
										: "AI investigation results stay internal to the SOC for this customer."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || !!saving"
							:loading="saving === 'enabled'"
							data-testid="ai-report-switch"
							@update:value="value => save({ enabled: value }, 'enabled')"
						/>
					</div>
				</n-card>

				<n-card size="small" data-testid="ai-requests-card">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Let portal users request an AI analysis</div>
							<div class="text-secondary text-sm" data-testid="ai-requests-state">{{ requestsState }}</div>
						</div>

						<n-switch
							:value="allowRequests"
							:disabled="!isAdmin || !enabled || loading || !!saving"
							:loading="saving === 'requests'"
							data-testid="ai-requests-switch"
							@update:value="value => save({ allow_customer_requests: value }, 'requests')"
						/>
					</div>

					<div
						v-if="enabled && allowRequests"
						class="border-default mt-4 flex flex-col gap-2 border-t pt-4"
						data-testid="ai-requests-limit"
					>
						<div class="flex flex-wrap items-center gap-3">
							<span class="text-sm font-medium">Daily limit</span>
							<n-radio-group
								v-model:value="limitMode"
								size="small"
								:disabled="!isAdmin || !!saving"
								data-testid="ai-requests-limit-mode"
							>
								<n-radio-button value="unlimited">Unlimited</n-radio-button>
								<n-radio-button value="limited">Limited</n-radio-button>
							</n-radio-group>
							<template v-if="limitMode === 'limited'">
								<n-input-number
									v-model:value="limitValue"
									:min="1"
									:max="10000"
									:precision="0"
									size="small"
									class="w-28"
									:disabled="!isAdmin || !!saving"
									data-testid="ai-requests-limit-value"
								/>
								<span class="text-secondary text-sm">requests per 24 hours</span>
							</template>
							<n-button
								v-if="isAdmin && limitChanged"
								size="small"
								type="primary"
								:disabled="!limitValid"
								:loading="saving === 'limit'"
								data-testid="ai-requests-limit-save"
								@click="saveLimit"
							>
								Save limit
							</n-button>
						</div>
						<div class="text-secondary text-xs" data-testid="ai-requests-usage">{{ usage }}</div>
					</div>
				</n-card>

				<n-alert v-if="!isAdmin" type="info" :bordered="false" class="text-xs">
					Only administrators can change this setting.
				</n-alert>

				<div class="text-secondary flex flex-col gap-3 text-sm">
					<p>Turning this on adds two read-only surfaces to the Customer Portal:</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							an
							<b>AI Analyst Insights</b>
							card on the Overview page, summarising how many alerts have been investigated and the
							severity the AI assigned to them;
						</li>
						<li>
							an
							<b>AI Report</b>
							tab on each alert detail page, with the summary, recommended actions, the full report and
							the indicators the AI extracted.
						</li>
					</ul>
					<p>
						Both surfaces are read-only. Analyst tooling — the Talon chat, report reviews, memory palace
						lessons and investigation replay — is never exposed to the customer, and internal details such
						as job identifiers, investigation templates and agent error messages are stripped from the
						payload.
					</p>
					<p>
						Letting portal users
						<b>request an analysis</b>
						adds a Run AI analysis button to the AI Report tab, also to re-run a finished one. An alert is
						analysed at most once every 30 minutes and never while an analysis is still running, and each
						request is noted on the alert's timeline and in the audit log. The daily limit is never shown
						to the customer: a request over it is refused with a message.
					</p>
					<p>
						This is independent of
						<b>AI Triggers</b>
						: that decides whether investigations run for this customer, this decides whether the customer
						gets to read the result. Running investigations while keeping them internal is a valid setup.
					</p>
					<p>
						New customers start with this
						<b>off</b>
						, so AI-written findings are never published to a customer without an explicit decision.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CustomerPortalAiReportSettingsPayload } from "@/api/endpoints/customer-portal"
import type { ApiError } from "@/types/common"
import type { CustomerPortalAiReportSettings } from "@/types/customer-portal"
import {
	NAlert,
	NButton,
	NCard,
	NInputNumber,
	NRadioButton,
	NRadioGroup,
	NSpin,
	NSwitch,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
/** Which control is saving, so only its spinner turns. */
const saving = ref<"enabled" | "requests" | "limit" | null>(null)
const settings = ref<CustomerPortalAiReportSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)
const allowRequests = computed(() => settings.value?.allow_customer_requests ?? false)

const requestsState = computed(() => {
	if (!enabled.value) return "Turn on the AI findings above first: a customer can only ask for analyses it can read."
	if (!allowRequests.value) return "Only the SOC and AI Triggers start investigations for this customer."
	return "Portal users of this customer can ask the AI Analyst to analyse, or re-analyse, one of their alerts."
})

// The limit is edited locally and saved with its own button: saving on every keystroke would
// spread one change over several audit entries.
const limitMode = ref<"unlimited" | "limited">("unlimited")
const limitValue = ref<number | null>(null)

function resetLimit() {
	const stored = settings.value?.daily_request_limit ?? null
	limitMode.value = stored === null ? "unlimited" : "limited"
	limitValue.value = stored ?? 20
}
watch(settings, resetLimit)

const editedLimit = computed(() => (limitMode.value === "unlimited" ? null : limitValue.value))
const limitValid = computed(() => editedLimit.value === null || (Number.isInteger(editedLimit.value) && editedLimit.value >= 1))
const limitChanged = computed(() => editedLimit.value !== (settings.value?.daily_request_limit ?? null))

const usage = computed(() => {
	const used = settings.value?.requests_last_24h ?? 0
	const limit = settings.value?.daily_request_limit ?? null
	const requests = `${used} request${used === 1 ? "" : "s"}`
	return limit === null ? `${requests} in the last 24 hours, no limit.` : `${used} of ${limit} requests used in the last 24 hours.`
})

function getSettings() {
	loading.value = true

	Api.customerPortal
		.getCustomerAiReportSettings(customerCode)
		.then(res => {
			if (res.data.success) {
				settings.value = res.data.settings
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function save(change: Omit<CustomerPortalAiReportSettingsPayload, "enabled"> & { enabled?: boolean }, control: typeof saving.value) {
	saving.value = control

	Api.customerPortal
		.setCustomerAiReportSettings(customerCode, { enabled: enabled.value, ...change })
		.then(res => {
			if (res.data.success) {
				settings.value = res.data.settings
				message.success(savedMessage(change))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = null
		})
}

function saveLimit() {
	if (limitValid.value) save({ daily_request_limit: editedLimit.value }, "limit")
}

function savedMessage(change: Partial<CustomerPortalAiReportSettingsPayload>) {
	if (change.enabled !== undefined) {
		return change.enabled ? "AI reports enabled for this customer" : "AI reports disabled for this customer"
	}
	if (change.allow_customer_requests !== undefined) {
		return change.allow_customer_requests ? "Portal users can now request AI analyses" : "AI analysis requests turned off"
	}
	return "Daily limit saved"
}

onBeforeMount(() => {
	getSettings()
})
</script>
