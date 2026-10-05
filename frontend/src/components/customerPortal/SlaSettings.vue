<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">SLA</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can see how the SOC is meeting the service levels
				promised to them
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Show the SLA page in the Customer Portal</div>
							<div class="text-secondary text-sm" data-testid="sla-settings-state">
								{{
									enabled
										? "Portal users of this customer can see their SLA targets and how they were kept."
										: "SLA figures stay internal to the SOC for this customer."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							data-testid="sla-settings-switch"
							@update:value="save"
						/>
					</div>
				</n-card>

				<n-alert v-if="!isAdmin" type="info" :bordered="false" class="text-xs" data-testid="sla-settings-readonly">
					Only administrators can change this setting.
				</n-alert>

				<div class="text-secondary flex flex-col gap-3 text-sm">
					<p>Turning this on adds a read-only SLA page to the Customer Portal, with:</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							the
							<b>targets</b>
							promised for each severity of alert and case, and whether they count business hours;
						</li>
						<li>
							<b>compliance</b>
							— the share of acknowledge and resolve targets met — and the median
							<b>response and resolution times</b>
							, compared with the previous period;
						</li>
						<li>
							the
							<b>trend</b>
							over the period, and what is open now, including the items waiting on the customer.
						</li>
					</ul>
					<p>
						The page is computed from the same figures as SOC Management, but never names a person: no
						analyst, assignee or resolver reaches the customer, and nothing about other customers or the
						SOC's internal workload.
					</p>
					<p>
						This only decides what the customer can
						<b>see</b>
						. SLA clocks run for every customer either way, and the targets themselves are set under
						<b>SOC Management → Policies</b>
						.
					</p>
					<p>
						New customers start with this
						<b>off</b>
						, so response-time figures are never published to a customer without an explicit decision.
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
import type { ApiError } from "@/types/common"
import type { CustomerPortalSlaSettings } from "@/types/customer-portal"
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
const settings = ref<CustomerPortalSlaSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

const FALLBACK_ERROR = "An error occurred. Please try again later."

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerSlaSettings(customerCode)
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
		const res = await Api.customerPortal.setCustomerSlaSettings(customerCode, { enabled: value })
		if (res.data.success) {
			settings.value = res.data.settings
			message.success(value ? "SLA page enabled for this customer" : "SLA page disabled for this customer")
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
