<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Portal Notifications</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can be told, in the portal and by email, about what happens
				to their alerts, cases and reports
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div class="flex flex-col gap-1">
							<div class="font-semibold">Notify this customer's portal users</div>
							<div class="text-secondary text-sm" data-testid="notification-settings-state">
								{{
									enabled
										? "Each portal user chooses what reaches their bell and their inbox, under Profile → Notifications."
										: "Portal users of this customer receive no notifications."
								}}
							</div>
						</div>

						<n-switch
							:value="enabled"
							:disabled="!isAdmin || loading || saving"
							:loading="saving"
							data-testid="notification-settings-switch"
							@update:value="save"
						/>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="notification-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<n-alert
					v-if="loaded && !emailConfigured"
					type="warning"
					:bordered="false"
					class="text-xs"
					data-testid="notification-settings-no-smtp"
				>
					SMTP is not configured on this deployment, so notifications reach the portal's bell only. Set
					<code>SMTP_HOST</code>
					and the related
					<code>SMTP_*</code>
					variables to let users receive them by email.
				</n-alert>

				<div class="text-secondary flex flex-col gap-3 text-sm">
					<p>Turning this on lets each portal user of this customer choose to be told when:</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							a
							<b>new alert</b>
							arrives, from the severity they pick (High by default);
						</li>
						<li>
							the SOC is
							<b>waiting on their reply</b>
							on an alert or a case;
						</li>
						<li>
							one of their
							<b>cases is closed</b>
							;
						</li>
						<li>
							a
							<b>report is ready</b>
							: one they generated, or one the SOC shared with them.
						</li>
					</ul>
					<p>
						Each event can reach their bell, their inbox at once, or a
						<b>daily summary</b>
						sent at
						<b data-testid="notification-settings-digest-hour">{{ digestHourLabel }}</b>
						. Until they choose, they get the bell only: email is theirs to turn on.
					</p>
					<p>
						A user is never told about something they caused, and never about an alert or a case the portal
						would not show them. The emails use the
						<b>Portal —</b>
						message templates under
						<b>Notifications → Message Templates</b>
						, which can be copied and adapted for this customer.
					</p>
					<p>
						New customers start with this
						<b>off</b>
						.
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
import type { CustomerPortalNotificationSettings } from "@/types/customer-portal"
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
const loaded = ref(false)
const saving = ref(false)
const settings = ref<CustomerPortalNotificationSettings | null>(null)
const emailConfigured = ref(true)
const digestHour = ref(7)

const enabled = computed(() => settings.value?.enabled ?? false)
const digestHourLabel = computed(() => `${String(digestHour.value).padStart(2, "0")}:00 UTC`)

const FALLBACK_ERROR = "An error occurred. Please try again later."

function apply(data: { settings: CustomerPortalNotificationSettings; email_configured: boolean; digest_hour_utc: number }) {
	settings.value = data.settings
	emailConfigured.value = data.email_configured
	digestHour.value = data.digest_hour_utc
	loaded.value = true
}

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerNotificationSettings(customerCode)
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

async function save(value: boolean) {
	saving.value = true
	try {
		const res = await Api.customerPortal.setCustomerNotificationSettings(customerCode, { enabled: value })
		if (res.data.success) {
			apply(res.data)
			message.success(
				value ? "Portal notifications enabled for this customer" : "Portal notifications disabled for this customer"
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
