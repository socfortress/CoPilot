<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Audit Log</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's administrators can see who did what in their tenant
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Show the Audit Log page in the Customer Portal</div>
							<div class="text-secondary text-sm" data-testid="audit-settings-state">
								{{
									enabled
										? "This customer's administrators can see the audit log of their tenant."
										: "Nobody at this customer can see the audit log."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							data-testid="audit-settings-switch"
							@update:value="save"
						/>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="audit-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm" data-testid="audit-settings-help">
					<p class="text-default">
						Turning this on adds a read-only Audit Log page to the Customer Portal, for the portal users
						appointed customer administrators in the
						<b>Security</b>
						tab. It lists, newest first:
					</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>status changes and comments on the customer's alerts and cases, and cases opened</li>
						<li>reports generated, downloaded and deleted, and AI analyses requested</li>
						<li>
							their portal users' sign-ins, failed sign-ins, password and two-factor changes,
							invitations and disabled accounts
						</li>
					</ul>
					<p class="text-default">
						What the SOC did is shown as done by
						<b>SOC</b>
						without an analyst's name or address. The SOC's internal work (verdicts, connectors, AI
						Analyst actions, settings) and reports the customer can't see are never listed. Comment text is
						never shown, only that a comment was written.
					</p>
					<p class="text-default">
						New customers start with this
						<b>off</b>
						until an administrator turns it on.
					</p>
				</div>

				<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="audit-settings-updated">
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerPortalAuditSettings } from "@/types/customer-portal"
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
const settings = ref<CustomerPortalAuditSettings | null>(null)

const enabled = computed(() => settings.value?.enabled ?? false)

const FALLBACK_ERROR = "An error occurred. Please try again later."

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerAuditSettings(customerCode)
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
		const res = await Api.customerPortal.setCustomerAuditSettings(customerCode, { enabled: value })
		if (res.data.success) {
			settings.value = res.data.settings
			message.success(
				value ? "Audit Log page enabled for this customer" : "Audit Log page disabled for this customer"
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
