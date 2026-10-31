<template>
	<div class="flex flex-col gap-4" data-testid="portal-chat-settings">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Talon chat in the portal</h3>
			<p class="text-secondary text-sm">
				Control whether this customer's portal users can ask Talon, the AI analyst, about their own alerts, its
				reports and their assets
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-col gap-4">
						<div class="flex flex-wrap items-center justify-between gap-4">
							<div class="flex flex-col gap-1">
								<div class="font-semibold">Let portal users chat with Talon</div>
								<div class="text-secondary text-sm" data-testid="portal-chat-state">
									{{ chatState }}
								</div>
							</div>
							<n-switch
								v-model:value="form.enabled"
								:disabled="!isAdmin || saving || (!form.enabled && !aiReportsEnabled)"
								data-testid="portal-chat-switch"
							/>
						</div>

						<div class="border-default flex flex-wrap items-center justify-between gap-4 border-t pt-4">
							<div class="flex flex-col gap-1">
								<div class="font-semibold">Let Talon search the customer's raw logs</div>
								<div class="text-secondary text-sm">
									Off: Talon answers from alerts, its reports and the asset list only. On: it may also
									search this customer's own log indices and show an alert's raw event, which can hold
									what the SOC hasn't reviewed yet.
								</div>
							</div>
							<n-switch
								v-model:value="form.logSearch"
								:disabled="!isAdmin || saving"
								data-testid="portal-chat-log-search-switch"
							/>
						</div>

						<div class="border-default flex flex-col gap-3 border-t pt-4" data-testid="portal-chat-limits">
							<div class="font-semibold">Daily message limits</div>
							<div class="flex flex-wrap items-center gap-3">
								<span class="w-48 text-sm">For the customer, per UTC day</span>
								<n-input-number
									v-model:value="form.daily"
									:min="LIMIT_MIN"
									:max="LIMIT_MAX"
									:precision="0"
									clearable
									size="small"
									class="w-36"
									placeholder="No limit"
									:disabled="!isAdmin || saving"
									data-testid="portal-chat-daily-limit"
								/>
							</div>
							<div class="flex flex-wrap items-center gap-3">
								<span class="w-48 text-sm">For each portal user, per UTC day</span>
								<n-input-number
									v-model:value="form.perUser"
									:min="LIMIT_MIN"
									:max="LIMIT_MAX"
									:precision="0"
									clearable
									size="small"
									class="w-36"
									placeholder="No limit"
									:disabled="!isAdmin || saving"
									data-testid="portal-chat-user-limit"
								/>
							</div>
							<div class="text-secondary text-xs">
								The chat can only be on with a limit for the customer. We propose {{ proposed.daily }} a
								day for the customer and {{ proposed.perUser }} per user; change them to fit. Talon
								counts the messages; the customer sees a message when a limit is reached.
							</div>
						</div>

						<n-alert
							v-if="isAdmin && problem"
							type="warning"
							:bordered="false"
							class="text-sm"
							data-testid="portal-chat-problem"
						>
							{{ problem }}
						</n-alert>

						<div v-if="isAdmin" class="flex justify-end gap-2">
							<n-button size="small" :disabled="!changed || saving" @click="reset()">
								Undo changes
							</n-button>
							<n-button
								size="small"
								type="primary"
								:disabled="!changed || !!problem"
								:loading="saving"
								data-testid="portal-chat-save"
								@click="save()"
							>
								Save
							</n-button>
						</div>
					</div>
				</n-card>

				<n-alert
					v-if="!isAdmin"
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="portal-chat-read-only"
				>
					Only administrators can change these settings.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm">
					<p class="text-default">
						With the chat on, this customer's portal users get an Ask Talon page. They can:
					</p>
					<ul class="ml-4 flex list-disc flex-col gap-1">
						<li>
							ask about their own alerts, Talon's reports on them and their assets, in their portal
							language;
						</li>
						<li>with raw log search on, have Talon search their own logs;</li>
						<li>
							have Talon look up indicators, while the IOC Enrichment tab allows it; each lookup counts
							against that tab's daily limit;
						</li>
						<li>
							accept a question Talon drafts for the SOC, which they edit, give an urgency and send
							through Ask the SOC (marked "Drafted with Talon"), and run an AI analysis where this tab
							allows it.
						</li>
					</ul>
					<p class="text-default">
						They can't: change anything through Talon (Talon takes no action and starts nothing), see other
						customers, the SOC's internal notes, review lessons or costs, or use web search. A read-only
						portal user can chat but gets no SOC drafts or analysis button.
					</p>
					<p class="text-default">
						The portal tells them the SOC may review their chats. Turning the chat off stops it at Talon's
						next step, and keeps the conversations for review. Turning this customer's AI reports off turns
						the chat off too.
					</p>
				</div>

				<div class="flex flex-wrap items-center justify-between gap-2">
					<div v-if="settings?.updated_at" class="text-secondary text-xs" data-testid="portal-chat-updated">
						Version {{ settings.version }}, last changed
						{{ formatDate(settings.updated_at, dFormats.datetime) }}
					</div>
					<n-button size="small" secondary data-testid="portal-chat-review-open" @click="showReview = true">
						Review portal chats
					</n-button>
				</div>
			</div>
		</n-spin>

		<n-modal
			v-model:show="showReview"
			preset="card"
			:style="{ maxWidth: 'min(1100px, 90vw)' }"
			title="Portal chats"
			:bordered="false"
			segmented
			display-directive="if"
		>
			<PortalChatReview :customer-code />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { PortalChatForm } from "./portalChat"
import type { CustomerPortalChatSettingsPayload } from "@/api/endpoints/customer-portal"
import type { ApiError } from "@/types/common"
import type { CustomerPortalChatSettings } from "@/types/customer-portal"
import { NAlert, NButton, NCard, NInputNumber, NModal, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, reactive, ref, watch } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { formProblem, LIMIT_MAX, LIMIT_MIN, PROPOSED_DAILY, PROPOSED_PER_USER } from "./portalChat"

const { customerCode, aiReportsEnabled } = defineProps<{
	customerCode: string
	/** The AI Report switch above; null until known. The chat can only be on with it. */
	aiReportsEnabled: boolean | null
}>()

const PortalChatReview = defineAsyncComponent(() => import("./PortalChatReview.vue"))

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const saving = ref(false)
const showReview = ref(false)
const settings = ref<CustomerPortalChatSettings | null>(null)
const serverAiReports = ref<boolean | null>(null)
const proposed = reactive({ daily: PROPOSED_DAILY, perUser: PROPOSED_PER_USER })
const form = reactive<PortalChatForm>({ enabled: false, logSearch: false, daily: null, perUser: null })

/** The AI Report switch as this page last knew it: the prop, else the settings' own answer. */
const aiReports = computed(() => aiReportsEnabled ?? serverAiReports.value ?? false)

/** The form from the stored row. */
function reset() {
	const row = settings.value
	form.enabled = row?.portal_chat_enabled ?? false
	form.logSearch = row?.log_search_enabled ?? false
	form.daily = row?.daily_message_limit ?? null
	form.perUser = row?.user_daily_message_limit ?? null
}

// Switching the chat on without a customer limit proposes the limits (editable, not saved yet).
watch(
	() => form.enabled,
	enabled => {
		if (enabled && form.daily === null) {
			form.daily = proposed.daily
			if (form.perUser === null) form.perUser = proposed.perUser
		}
	}
)

function payload(): CustomerPortalChatSettingsPayload {
	return {
		portal_chat_enabled: form.enabled,
		log_search_enabled: form.logSearch,
		daily_message_limit: form.daily ?? null,
		user_daily_message_limit: form.perUser ?? null
	}
}

const changed = computed(() => {
	const row = settings.value
	const stored = {
		portal_chat_enabled: row?.portal_chat_enabled ?? false,
		log_search_enabled: row?.log_search_enabled ?? false,
		daily_message_limit: row?.daily_message_limit ?? null,
		user_daily_message_limit: row?.user_daily_message_limit ?? null
	}
	return JSON.stringify(stored) !== JSON.stringify(payload())
})

const problem = computed(() =>
	formProblem({ ...form, daily: form.daily ?? null, perUser: form.perUser ?? null }, aiReports.value)
)

const chatState = computed(() => {
	if (!aiReports.value && !form.enabled) {
		return "Turn on the AI findings above first: a customer that can't read Talon's reports can't chat about them."
	}
	return settings.value?.portal_chat_enabled
		? "Portal users of this customer can chat with Talon."
		: "Portal users of this customer can't chat with Talon."
})

function load() {
	loading.value = true
	Api.customerPortal
		.getCustomerPortalChatSettings(customerCode)
		.then(res => {
			settings.value = res.data.settings
			serverAiReports.value = res.data.ai_reports_enabled
			if (res.data.proposed) {
				proposed.daily = res.data.proposed.daily_message_limit
				proposed.perUser = res.data.proposed.user_daily_message_limit
			}
			reset()
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function save() {
	if (problem.value) return
	saving.value = true
	Api.customerPortal
		.setCustomerPortalChatSettings(customerCode, payload())
		.then(res => {
			settings.value = res.data.settings
			serverAiReports.value = res.data.ai_reports_enabled
			reset()
			message.success("Portal chat settings saved")
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = false
		})
}

// Turning AI reports off above turns the chat off on the server too (the cascade): read it again.
watch(
	() => aiReportsEnabled,
	(now, before) => {
		if (before !== undefined && before !== null && now !== before) load()
	}
)

onBeforeMount(load)
</script>
