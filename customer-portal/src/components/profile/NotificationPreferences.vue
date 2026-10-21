<template>
	<n-spin :show="loading">
		<n-card data-testid="notification-preferences">
			<div class="flex flex-col gap-1 pb-4">
				<div class="font-display text-lg font-semibold">Notifications</div>
				<p class="text-secondary max-w-prose text-sm">
					Choose what reaches you in the portal's bell and by email. You are never told about something you
					did yourself.
				</p>
			</div>

			<n-alert
				v-if="emailUnavailable"
				type="info"
				:bordered="false"
				class="mb-4 text-xs"
				data-testid="notification-email-unavailable"
			>
				{{ emailUnavailable }}
			</n-alert>

			<!-- On wide screens every row is a grid on the same tracks, so the controls line up
			     in columns whether or not a row has the severity picker. -->
			<div class="divide-border border-border flex flex-col divide-y rounded-lg border">
				<div
					v-for="row of rows"
					:key="row.event"
					class="flex flex-col gap-3 p-4 md:flex-row md:items-center md:gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_8.5rem_18.5rem_16rem]"
					:data-testid="`notification-pref-${row.event}`"
				>
					<div class="flex min-w-0 grow items-start gap-3">
						<Icon :name="row.icon" :size="18" class="text-secondary mt-0.5 shrink-0" />
						<div class="flex min-w-0 flex-col gap-0.5">
							<div class="font-semibold">{{ row.label }}</div>
							<div class="text-secondary text-xs">{{ row.description }}</div>
						</div>
					</div>

					<div class="flex flex-wrap items-center gap-x-5 gap-y-3 md:shrink-0 xl:contents">
						<label class="flex items-center gap-2 text-sm">
							<n-switch
								v-model:value="draft[row.event].in_app"
								size="small"
								:data-testid="`notification-pref-${row.event}-in-app`"
							/>
							In the portal
						</label>

						<label class="flex items-center gap-2 text-sm">
							<span class="text-secondary shrink-0">Email</span>
							<n-select
								v-model:value="draft[row.event].email"
								size="small"
								class="w-60!"
								:options="emailOptions"
								:disabled="!!emailUnavailable"
								:data-testid="`notification-pref-${row.event}-email`"
							/>
						</label>

						<label v-if="row.event === 'alert_created'" class="flex items-center gap-2 text-sm">
							<span class="text-secondary shrink-0">From</span>
							<n-select
								v-model:value="draft.alert_created.min_severity"
								size="small"
								class="w-48!"
								:options="severityOptions"
								data-testid="notification-pref-alert_created-severity"
							/>
						</label>
						<div v-else class="hidden xl:block" aria-hidden="true" data-testid="notification-pref-spacer" />
					</div>
				</div>
			</div>

			<div class="flex items-center justify-end gap-3 pt-4">
				<span v-if="dirty" class="text-secondary text-xs">Unsaved changes</span>
				<n-button
					type="primary"
					:disabled="!dirty"
					:loading="saving"
					data-testid="notification-preferences-save"
					@click="save()"
				>
					Save
				</n-button>
			</div>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationEventName, NotificationPreference } from "@/types/notifications"
import { NAlert, NButton, NCard, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useServerNotifications } from "@/composables/common/useServerNotifications"
import { NOTIFICATION_EVENTS, SEVERITIES } from "@/types/notifications"
import { getApiErrorMessage } from "@/utils"
import { digestLabel, emailUnavailableText, EVENT_COPY, samePreferences } from "./notificationPreferences"

const message = useMessage()
const server = useServerNotifications()

const loading = ref(false)
const saving = ref(false)
/** Saving is offered only over choices that were read: never the defaults over a failed load. */
const loaded = ref(false)
const saved = ref<NotificationPreference[]>([])
const draft = reactive(
	Object.fromEntries(
		NOTIFICATION_EVENTS.map(event => [event, { event, in_app: true, email: "off", min_severity: null }])
	) as Record<NotificationEventName, NotificationPreference>
)

const rows = NOTIFICATION_EVENTS.map(event => ({ event, ...EVENT_COPY[event] }))
const severityOptions = SEVERITIES.map(severity => ({ label: `${severity} and up`, value: severity }))
const emailOptions = computed(() => [
	{ label: "Off", value: "off" },
	{ label: "Immediately", value: "immediate" },
	{ label: digestLabel(server.availability.value?.digest_hour_utc ?? 7), value: "digest" }
])
const emailUnavailable = computed(() => emailUnavailableText(server.availability.value))
const current = computed(() => NOTIFICATION_EVENTS.map(event => ({ ...draft[event] })))
const dirty = computed(() => loaded.value && !samePreferences(current.value, saved.value))

function apply(preferences: NotificationPreference[]) {
	saved.value = preferences.map(pref => ({ ...pref }))
	for (const pref of preferences) Object.assign(draft[pref.event], pref)
}

async function load() {
	loading.value = true
	try {
		await server.loadAvailability()
		apply((await Api.notifications.getPreferences()).data.preferences)
		loaded.value = true
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Your notification settings could not be loaded.")
	} finally {
		loading.value = false
	}
}

async function save() {
	saving.value = true
	try {
		apply((await Api.notifications.setPreferences(current.value)).data.preferences)
		message.success("Notification settings saved")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Your notification settings could not be saved.")
	} finally {
		saving.value = false
	}
}

onBeforeMount(() => {
	load()
})
</script>
