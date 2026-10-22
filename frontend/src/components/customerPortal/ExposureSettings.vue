<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Exposure</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can see their vulnerabilities and compliance across all
				their agents
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Show the Exposure page in the Customer Portal</div>
							<div class="text-secondary text-sm" data-testid="exposure-settings-state">
								{{
									enabled
										? "Portal users of this customer can see their vulnerabilities and compliance across their agents."
										: "Portal users of this customer see vulnerabilities and compliance one agent at a time only."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							data-testid="exposure-settings-switch"
							@update:value="save"
						/>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="exposure-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm" data-testid="exposure-settings-help">
					<p class="text-default">
						Turning this on adds a read-only Exposure page to the Customer Portal, with two tabs:
					</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							<b>Vulnerabilities</b>
							by severity and by CVE, with the agents each one affects and a CSV export
						</li>
						<li>
							<b>Compliance</b>
							by SCA policy, with the agents that score lowest on each
						</li>
					</ul>
					<p class="text-default">
						Both are read live from Wazuh for this customer's agents only, the same data each agent's page
						already shows the customer. Compliance is kept a few minutes, since Wazuh is asked agent by
						agent.
					</p>
					<p class="text-default">
						New customers start with this
						<b>off</b>
						until an administrator turns it on.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="exposure-settings-updated">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerPortalExposureSettings } from "@/types/customer-portal"
import { NAlert, NCard, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
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
const saving = ref(false)
const settings = ref<CustomerPortalExposureSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

const FALLBACK_ERROR = "An error occurred. Please try again later."

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerExposureSettings(customerCode)
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

async function save(value: boolean) {
	saving.value = true
	try {
		const res = await Api.customerPortal.setCustomerExposureSettings(customerCode, { enabled: value })
		if (res.data.success) {
			settings.value = res.data.settings
			message.success(
				value ? "Exposure page enabled for this customer" : "Exposure page disabled for this customer"
			)
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		saving.value = false
	}
}

onBeforeMount(() => {
	getSettings()
})
</script>
