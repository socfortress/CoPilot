<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">AI Report</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can read the AI Analyst findings produced for their alerts
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
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							@update:value="save"
						/>
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
						Both surfaces are strictly read-only. Analyst tooling — the Talon chat, report reviews, memory
						palace lessons and investigation replay — is never exposed to the customer, and internal details
						such as job identifiers, investigation templates and agent error messages are stripped from the
						payload.
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
import type { ApiError } from "@/types/common"
import type { CustomerPortalAiReportSettings } from "@/types/customer-portal"
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
const settings = ref<CustomerPortalAiReportSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

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

function save(value: boolean) {
	saving.value = true

	Api.customerPortal
		.setCustomerAiReportSettings(customerCode, { enabled: value })
		.then(res => {
			if (res.data.success) {
				settings.value = res.data.settings
				message.success(value ? "AI reports enabled for this customer" : "AI reports disabled for this customer")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = false
		})
}

onBeforeMount(() => {
	getSettings()
})
</script>
