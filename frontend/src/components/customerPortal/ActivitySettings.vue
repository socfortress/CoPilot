<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Activity</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can see what the SOC handled for them, broken down by
				source, asset, detection and verdict
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Show the Activity page in the Customer Portal</div>
							<div class="text-secondary text-sm" data-testid="activity-settings-state">
								{{
									enabled
										? "Portal users of this customer can see what reached the SOC and how it was judged."
										: "The activity breakdown stays internal to the SOC for this customer."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							data-testid="activity-settings-switch"
							@update:value="save"
						/>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="activity-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="text-secondary flex flex-col gap-3 text-sm" data-testid="activity-settings-help">
					<p>
						Turning this on adds a read-only Activity page to the Customer Portal, for the last 7, 30 or 90
						days beside the period before:
					</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							the
							<b>alerts</b>
							that reached the SOC, by source and severity
						</li>
						<li>
							the busiest
							<b>detections, assets and tags</b>
						</li>
						<li>
							the SOC's
							<b>verdicts</b>
							with the false-positive rate and its reasons
						</li>
						<li>
							the
							<b>cases</b>
							opened, by type and where they stand now
						</li>
					</ul>
					<p>
						Every figure counts only alerts and cases the customer can already open in the portal, and a
						click on a slice lists exactly those alerts. Items count from when they reached the SOC, so an
						alert that keeps firing is not counted again as new.
					</p>
					<p>
						The figures are the ones the customer already receives in the PDF report, never a person's name.
					</p>
					<p>
						New customers start with this
						<b>off</b>
						until an administrator turns it on.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="activity-settings-updated">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerPortalActivitySettings } from "@/types/customer-portal"
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
const settings = ref<CustomerPortalActivitySettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

const FALLBACK_ERROR = "An error occurred. Please try again later."

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerActivitySettings(customerCode)
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
		const res = await Api.customerPortal.setCustomerActivitySettings(customerCode, { enabled: value })
		if (res.data.success) {
			settings.value = res.data.settings
			message.success(
				value ? "Activity page enabled for this customer" : "Activity page disabled for this customer"
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
