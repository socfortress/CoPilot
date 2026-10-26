<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Ask the SOC</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can ask the SOC a question about one of their alerts or
				cases
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Let portal users ask the SOC</div>
							<div class="text-secondary text-sm" data-testid="ask-soc-settings-state">
								{{
									enabled
										? "Portal users of this customer can ask the SOC about their alerts and cases."
										: "Portal users of this customer cannot ask the SOC from the portal."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || !!saving"
							:loading="saving === 'enabled'"
							data-testid="ask-soc-settings-switch"
							@update:value="(value: boolean) => save({ enabled: value }, 'enabled')"
						/>
					</div>

					<div
						v-if="enabled"
						class="border-default mt-4 flex flex-wrap items-center gap-3 border-t pt-4"
						data-testid="ask-soc-settings-limit"
					>
						<span class="text-sm font-medium">Daily limit</span>
						<n-radio-group
							v-model:value="limitMode"
							size="small"
							:disabled="!isAdmin || !!saving"
							data-testid="ask-soc-settings-limit-mode"
						>
							<n-radio-button value="unlimited">Unlimited</n-radio-button>
							<n-radio-button value="limited">Limited</n-radio-button>
						</n-radio-group>
						<template v-if="limitMode === 'limited'">
							<n-input-number
								v-model:value="limitValue"
								:min="1"
								:max="MAX_LIMIT"
								:precision="0"
								size="small"
								class="w-28"
								:disabled="!isAdmin || !!saving"
								data-testid="ask-soc-settings-limit-value"
							/>
							<span class="text-secondary text-sm">questions per 24 hours</span>
						</template>
						<n-button
							v-if="isAdmin && limitChanged"
							size="small"
							type="primary"
							:disabled="!limitValid"
							:loading="saving === 'limit'"
							data-testid="ask-soc-settings-limit-save"
							@click="saveLimit()"
						>
							Save limit
						</n-button>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="ask-soc-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm" data-testid="ask-soc-settings-help">
					<p class="text-default">
						Turning this on adds an Ask the SOC button to the alerts and cases of the Customer Portal. A
						question on an alert goes on the alert's open case, on a new case made from the alert, or on the
						alert itself, as the user chooses; a question on a case goes on the case. Either way it is a
						comment signed by the user.
					</p>
					<p class="text-default">
						The SOC hears about it through notification routes on the
						<b>Customer question</b>
						trigger (internal routes only, never the customer's own channel), and sees it under
						<b>Incidents, Customer questions</b>
						until it is answered: by a SOC comment on the case or alert, or marked answered by an analyst.
					</p>
					<p class="text-default">
						One question per alert or case every 10 minutes. The daily limit counts the customer's questions
						over any 24 hours and is never shown to the customer. New customers start with this
						<b>off</b>
						until an administrator turns it on.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="ask-soc-settings-updated">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CustomerPortalSocRequestSettingsPayload } from "@/api/endpoints/customer-portal"
import type { ApiError } from "@/types/common"
import type { CustomerPortalSocRequestSettings } from "@/types/soc-requests"
import { NAlert, NButton, NCard, NInputNumber, NRadioButton, NRadioGroup, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

/** The backend's own ceiling for the daily limit. */
const MAX_LIMIT = 1000
const FALLBACK_ERROR = "An error occurred. Please try again later."

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const saving = ref<"enabled" | "limit" | null>(null)
const settings = ref<CustomerPortalSocRequestSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

// The limit is edited locally and saved with its own button: saving on every keystroke would
// spread one change over several audit entries.
const limitMode = ref<"unlimited" | "limited">("unlimited")
const limitValue = ref<number | null>(null)

function resetLimit() {
	const stored = settings.value?.daily_request_limit ?? null
	limitMode.value = stored === null ? "unlimited" : "limited"
	limitValue.value = stored ?? 10
}
watch(settings, resetLimit)

const editedLimit = computed(() => (limitMode.value === "unlimited" ? null : limitValue.value))
const limitValid = computed(
	() =>
		editedLimit.value === null ||
		(Number.isInteger(editedLimit.value) && editedLimit.value >= 1 && editedLimit.value <= MAX_LIMIT)
)
const limitChanged = computed(() => editedLimit.value !== (settings.value?.daily_request_limit ?? null))

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerSocRequestSettings(customerCode)
		if (res.data.success) {
			settings.value = res.data.settings
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		loading.value = false
	}
}

async function save(change: Partial<CustomerPortalSocRequestSettingsPayload>, control: "enabled" | "limit") {
	saving.value = control
	const payload: CustomerPortalSocRequestSettingsPayload = {
		enabled: enabled.value,
		daily_request_limit: settings.value?.daily_request_limit ?? null,
		...change
	}
	try {
		const res = await Api.customerPortal.setCustomerSocRequestSettings(customerCode, payload)
		if (res.data.success) {
			settings.value = res.data.settings
			if (change.enabled !== undefined) {
				message.success(
					change.enabled ? "Ask the SOC enabled for this customer" : "Ask the SOC disabled for this customer"
				)
			} else {
				message.success("Daily limit saved")
			}
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		saving.value = null
	}
}

function saveLimit() {
	if (limitValid.value) save({ daily_request_limit: editedLimit.value }, "limit")
}

onBeforeMount(() => {
	getSettings()
})
</script>
