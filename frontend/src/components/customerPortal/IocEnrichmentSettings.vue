<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">IOC Enrichment</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can check the IOCs of their alerts against Threat Intel
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Let portal users check their IOCs</div>
							<div class="text-secondary text-sm" data-testid="ioc-enrichment-settings-state">
								{{
									enabled
										? "Portal users of this customer can check the IOCs of their alerts against Threat Intel."
										: "Portal users of this customer cannot check IOCs from the portal."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || !!saving"
							:loading="saving === 'enabled'"
							data-testid="ioc-enrichment-settings-switch"
							@update:value="(value: boolean) => save({ enabled: value }, 'enabled')"
						/>
					</div>

					<div
						v-if="enabled"
						class="border-default mt-4 flex flex-wrap items-center gap-3 border-t pt-4"
						data-testid="ioc-enrichment-settings-limit"
					>
						<span class="text-sm font-medium">Daily limit</span>
						<n-radio-group
							v-model:value="limitMode"
							size="small"
							:disabled="!isAdmin || !!saving"
							data-testid="ioc-enrichment-settings-limit-mode"
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
								data-testid="ioc-enrichment-settings-limit-value"
							/>
							<span class="text-secondary text-sm">lookups per 24 hours</span>
						</template>
						<n-button
							v-if="isAdmin && limitChanged"
							size="small"
							type="primary"
							:disabled="!limitValid"
							:loading="saving === 'limit'"
							data-testid="ioc-enrichment-settings-limit-save"
							@click="saveLimit()"
						>
							Save limit
						</n-button>
					</div>
				</n-card>

				<n-card v-if="connectors" size="small" data-testid="ioc-enrichment-settings-sources">
					<div class="flex flex-col gap-2">
						<div class="font-semibold">Sources</div>
						<div
							v-for="source of SOURCES"
							:key="source.key"
							class="flex items-center gap-2 text-sm"
							:data-testid="`ioc-enrichment-settings-source-${source.key}`"
						>
							<Icon
								:name="connectors[source.key] ? CheckIcon : WarningIcon"
								:size="16"
								:class="connectors[source.key] ? 'text-success' : 'text-warning'"
							/>
							<span class="font-medium">{{ source.label }}</span>
							<span class="text-secondary">
								{{ connectors[source.key] ? "connector verified" : "connector not verified: not asked" }}
							</span>
						</div>
					</div>
				</n-card>

				<n-alert
					v-if="enabled && connectors && !connectors.virustotal && !connectors.opencti"
					type="warning"
					:bordered="false"
					class="text-xs"
					data-testid="ioc-enrichment-settings-no-source"
				>
					No source can be asked: verify the VirusTotal or the OpenCTI connector under Connectors. Until then
					the portal does not offer IOC checks.
				</n-alert>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="ioc-enrichment-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm" data-testid="ioc-enrichment-settings-help">
					<p class="text-default">
						Turning this on lets the customer's portal users check an IOC of one of their alerts against
						VirusTotal and OpenCTI, on request, and shows the verdict beside it. Only the IOCs of alerts
						they can see, and never another customer's answers: each customer's results are kept apart.
					</p>
					<p class="text-default">
						Private addresses and internal names are never sent anywhere. VirusTotal is only read (a URL is
						looked up, never submitted for scanning). From OpenCTI, anything marked beyond what may be
						passed to a client (TLP:RED, TLP:AMBER+STRICT, other statements) is left out.
					</p>
					<p class="text-default" data-testid="ioc-enrichment-settings-cache">
						An answer is kept {{ cacheHours }} hours before it can be asked again, and checking a kept answer
						costs nothing. The daily limit counts the lookups that reached a source over any 24 hours and is
						never shown to the customer. New customers start with this
						<b>off</b>
						until an administrator turns it on.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="ioc-enrichment-settings-updated">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CustomerPortalIocEnrichmentSettingsPayload } from "@/api/endpoints/customer-portal"
import type { ApiError } from "@/types/common"
import type { CustomerPortalIocEnrichmentSettings, IocEnrichmentConnectors } from "@/types/ioc-enrichment"
import { NAlert, NButton, NCard, NInputNumber, NRadioButton, NRadioGroup, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { customerCode } = defineProps<{
	customerCode: string
}>()

/** The backend's own ceiling for the daily limit. */
const MAX_LIMIT = 10000
const FALLBACK_ERROR = "An error occurred. Please try again later."
const CheckIcon = "carbon:checkmark-filled"
const WarningIcon = "carbon:warning-alt-filled"
const SOURCES: { key: keyof IocEnrichmentConnectors; label: string }[] = [
	{ key: "virustotal", label: "VirusTotal" },
	{ key: "opencti", label: "OpenCTI" }
]

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const saving = ref<"enabled" | "limit" | null>(null)
const settings = ref<CustomerPortalIocEnrichmentSettings | null>(null)
const connectors = ref<IocEnrichmentConnectors | null>(null)
const cacheHours = ref(24)

const enabled = computed(() => settings.value?.enabled ?? false)

// The limit is edited locally and saved with its own button: saving on every keystroke would
// spread one change over several audit entries.
const limitMode = ref<"unlimited" | "limited">("unlimited")
const limitValue = ref<number | null>(null)

function resetLimit() {
	const stored = settings.value?.daily_lookup_limit ?? null
	limitMode.value = stored === null ? "unlimited" : "limited"
	limitValue.value = stored ?? 100
}
watch(settings, resetLimit)

const editedLimit = computed(() => (limitMode.value === "unlimited" ? null : limitValue.value))
const limitValid = computed(
	() =>
		editedLimit.value === null ||
		(Number.isInteger(editedLimit.value) && editedLimit.value >= 1 && editedLimit.value <= MAX_LIMIT)
)
const limitChanged = computed(() => editedLimit.value !== (settings.value?.daily_lookup_limit ?? null))

function apply(data: { settings: CustomerPortalIocEnrichmentSettings; connectors: IocEnrichmentConnectors; cache_hours: number }) {
	settings.value = data.settings
	connectors.value = data.connectors
	cacheHours.value = data.cache_hours
}

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerIocEnrichmentSettings(customerCode)
		if (res.data.success) {
			apply(res.data)
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		loading.value = false
	}
}

async function save(change: Partial<CustomerPortalIocEnrichmentSettingsPayload>, control: "enabled" | "limit") {
	saving.value = control
	const payload: CustomerPortalIocEnrichmentSettingsPayload = {
		enabled: enabled.value,
		daily_lookup_limit: settings.value?.daily_lookup_limit ?? null,
		...change
	}
	try {
		const res = await Api.customerPortal.setCustomerIocEnrichmentSettings(customerCode, payload)
		if (res.data.success) {
			apply(res.data)
			if (change.enabled !== undefined) {
				message.success(
					change.enabled ? "IOC enrichment enabled for this customer" : "IOC enrichment disabled for this customer"
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
	if (limitValid.value) save({ daily_lookup_limit: editedLimit.value }, "limit")
}

onBeforeMount(() => {
	getSettings()
})
</script>
