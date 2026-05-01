<template>
	<n-form ref="formRef" :model="form" :rules label-placement="top">
		<n-form-item label="Name" path="name">
			<n-input v-model:value="form.name" placeholder="e.g. SOC team Slack #alerts" :maxlength="128" show-count />
		</n-form-item>

		<n-form-item label="Minimum severity" path="min_severity">
			<n-select v-model:value="form.min_severity" :options="severityOptions" />
			<template v-if="!fieldErrors.min_severity" #feedback>
				<span class="text-tertiary text-xs">
					Route fires when the investigation's severity is at this tier or higher. The route is hard-bound to
					the
					<code>investigation_complete</code>
					event — every Talon-driven investigation runs through these filters.
				</span>
			</template>
		</n-form-item>

		<n-form-item label="Channel" path="channel">
			<n-select
				v-model:value="form.channel"
				:options="channelOptions"
				to="body"
				@update:value="onChannelChange"
			/>
			<template v-if="!fieldErrors.channel" #feedback>
				Email is direct SMTP via CoPilot's deployment config. Shuffle proxies to 3,000+ integrations through a
				customer's authenticated Shuffle org.
			</template>
		</n-form-item>

		<!-- SMTP-specific: recipient emails -->
		<n-form-item v-if="form.channel === 'smtp_email'" label="Recipient email(s)" path="destination">
			<n-input v-model:value="form.destination" placeholder="soc@example.com, ir@example.com" type="text" />
		</n-form-item>

		<!-- Shuffle-specific: integration picker, app picker, destination hint -->
		<template v-if="form.channel === 'shuffle'">
			<n-form-item label="Shuffle integration" path="shuffle_integration_id">
				<n-select
					v-model:value="form.shuffle_integration_id"
					:options="integrationOptions"
					placeholder="Pick a Shuffle org for this customer"
					:loading="loadingIntegrations"
					@update:value="onIntegrationChange"
				/>
				<template
					v-if="!fieldErrors.shuffle_integration_id && !integrationOptions.length && !loadingIntegrations"
					#feedback
				>
					No Shuffle integrations configured for this customer yet — go to the
					<strong>Shuffle integrations</strong>
					tab to add one first.
				</template>
			</n-form-item>

			<n-form-item label="Shuffle app" path="shuffle_app_id">
				<n-select
					v-model:value="form.shuffle_app_id"
					:options="appOptions"
					placeholder="Pick an authenticated app"
					:loading="loadingApps"
					:disabled="!form.shuffle_integration_id || loadingApps"
					filterable
					@update:value="onAppChange"
				/>
				<template
					v-if="
						!fieldErrors.shuffle_app_id &&
						form.shuffle_integration_id &&
						!appOptions.length &&
						!loadingApps &&
						appsError
					"
					#feedback
				>
					Couldn't fetch apps from Shuffle: {{ appsError }}
				</template>
			</n-form-item>

			<n-form-item label="Destination hint" path="destination">
				<n-input
					v-model:value="form.destination"
					placeholder="e.g. #soc-alerts, soc@example.com, @user-id"
					type="text"
				/>
				<template v-if="!fieldErrors.destination" #feedback>
					Free-form — gets prepended to the outgoing message as a
					<code>Send to &lt;destination&gt;: …</code>
					hint so the Shuffle app agent knows where to deliver. Channel name for Slack, email for Outlook,
					etc.
				</template>
			</n-form-item>
		</template>

		<n-form-item label="Custom message template (optional)" path="format_template" :show-feedback="false">
			<n-input
				v-model:value="form.format_template"
				type="textarea"
				:autosize="{ minRows: 4, maxRows: 12 }"
				placeholder="Leave empty to use the default. Substitutions: {{customer_code}} {{alert_id}} {{alert_name}} {{severity}} {{summary}} {{report_url}}"
			/>
		</n-form-item>

		<n-form-item>
			<n-checkbox v-model:checked="form.enabled">Enabled</n-checkbox>
		</n-form-item>

		<div class="flex justify-end gap-2">
			<n-button @click="$emit('close')">Cancel</n-button>
			<n-button type="primary" :loading="submitting" @click="submit">
				{{ editing ? "Save changes" : "Create route" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type {
	NotificationChannel,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationSeverity,
	NotificationTrigger,
	ShuffleApp,
	ShuffleIntegration
} from "@/types/notifications.d"
import { NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, reactive, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCode: string
	editingRoute: NotificationRoute | null
}>()

const emit = defineEmits<{
	(e: "submitted"): void
	(e: "close"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const editing = computed(() => props.editingRoute !== null)
type FeedbackField = "channel" | "destination" | "min_severity" | "shuffle_app_id" | "shuffle_integration_id"

const fieldErrors = reactive<Partial<Record<FeedbackField, string>>>({})

const form = reactive<NotificationRoutePayload>({
	name: props.editingRoute?.name ?? "",
	trigger: props.editingRoute?.trigger ?? ("investigation_complete" as NotificationTrigger),
	channel: props.editingRoute?.channel ?? ("smtp_email" as NotificationChannel),
	destination: props.editingRoute?.destination ?? "",
	min_severity: props.editingRoute?.min_severity ?? ("Medium" as NotificationSeverity),
	format_template: props.editingRoute?.format_template ?? "",
	enabled: props.editingRoute?.enabled ?? true,
	shuffle_integration_id: props.editingRoute?.shuffle_integration_id ?? null,
	shuffle_app_id: props.editingRoute?.shuffle_app_id ?? null,
	shuffle_app_name: props.editingRoute?.shuffle_app_name ?? null
})

// Trigger is a single fixed value today (`investigation_complete`).
// Hidden from the UI — set programmatically on the form. Will become
// a select again when we add more dispatch event types (analyst-review
// hooks, IOC-enrichment alerts, scheduled-sweep findings).

const channelOptions = [
	{ label: "Email (SMTP)", value: "smtp_email" },
	{ label: "Shuffle (Slack / Teams / Outlook / 3,000+ apps)", value: "shuffle" }
]

const severityOptions = [
	{ label: "Critical (only)", value: "Critical" },
	{ label: "High and above", value: "High" },
	{ label: "Medium and above", value: "Medium" },
	{ label: "Low and above", value: "Low" },
	{ label: "Informational and above (everything)", value: "Informational" }
]

// Shuffle integrations + apps state. Integrations are fetched on form
// open; apps are fetched lazily when an integration is picked. Both
// short-circuit on edit so we don't blank a route's existing values.
const integrations = ref<ShuffleIntegration[]>([])
const loadingIntegrations = ref(false)
const apps = ref<ShuffleApp[]>([])
const loadingApps = ref(false)
const appsError = ref<string | null>(null)

const integrationOptions = computed(() =>
	integrations.value
		.filter(i => i.enabled)
		.map(i => ({
			label: `${i.display_name} (${i.shuffle_org_id.slice(0, 8)}…)`,
			value: i.id
		}))
)

const appOptions = computed(() =>
	apps.value.map(a => ({
		label: a.name,
		value: a.id
	}))
)

function clearFieldError(field: FeedbackField) {
	delete fieldErrors[field]
}

function createFieldError(field: FeedbackField, message: string) {
	fieldErrors[field] = message
	return new Error(message)
}

async function loadIntegrations() {
	loadingIntegrations.value = true
	try {
		const res = await Api.notifications.listShuffleIntegrations(props.customerCode)
		if (res.data.success) {
			integrations.value = res.data.integrations
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to load Shuffle integrations")
	} finally {
		loadingIntegrations.value = false
	}
}

async function loadApps(integrationId: number) {
	loadingApps.value = true
	appsError.value = null
	try {
		const res = await Api.notifications.listShuffleApps(props.customerCode, integrationId)
		if (res.data.success) {
			apps.value = res.data.apps
		} else {
			apps.value = []
			appsError.value = res.data.message || "Failed to load apps"
		}
	} catch (err: unknown) {
		apps.value = []
		appsError.value = getApiErrorMessage(err as never) || "Failed to load apps"
	} finally {
		loadingApps.value = false
	}
}

function onChannelChange(value: NotificationChannel) {
	// Clear channel-specific fields when switching, so we don't carry
	// stale Shuffle picks into an SMTP route or vice versa.
	if (value === "smtp_email") {
		form.shuffle_integration_id = null
		form.shuffle_app_id = null
		form.shuffle_app_name = null
	} else {
		// Reset destination — SMTP recipients don't make sense as a
		// Shuffle channel hint.
		if (!editing.value) form.destination = ""
	}
	clearFieldError("destination")
	clearFieldError("shuffle_integration_id")
	clearFieldError("shuffle_app_id")
}

async function onIntegrationChange(integrationId: number | null) {
	apps.value = []
	form.shuffle_app_id = null
	form.shuffle_app_name = null
	if (integrationId) {
		await loadApps(integrationId)
	}
}

function onAppChange(appId: string | null) {
	// Cache the app's display name alongside the UUID so the UI list can
	// render "Slack" instead of a UUID without re-fetching the catalog
	// every render.
	const app = apps.value.find(a => a.id === appId)
	form.shuffle_app_name = app?.name ?? null
}

const rules: FormRules = {
	name: { required: true, message: "Name is required", trigger: ["input", "blur"] },
	channel: {
		validator: (_rule, value: NotificationChannel | null) => {
			if (!value) return createFieldError("channel", "Pick a channel")
			clearFieldError("channel")
			return true
		},
		trigger: ["change", "blur"]
	},
	min_severity: {
		validator: (_rule, value: NotificationSeverity | null) => {
			if (!value) return createFieldError("min_severity", "Pick a severity threshold")
			clearFieldError("min_severity")
			return true
		},
		trigger: ["change", "blur"]
	},
	destination: {
		required: true,
		validator: (_rule, value: string) => {
			if (!value || !value.trim()) {
				return form.channel === "smtp_email"
					? createFieldError("destination", "At least one recipient email required")
					: createFieldError("destination", "Destination hint is required")
			}
			if (form.channel === "smtp_email") {
				const recipients = value
					.split(",")
					.map(s => s.trim())
					.filter(Boolean)
				if (!recipients.length) return createFieldError("destination", "At least one recipient email required")
				const bad = recipients.find(r => !r.includes("@"))
				if (bad) return createFieldError("destination", `Invalid email: ${bad}`)
			}
			clearFieldError("destination")
			return true
		},
		trigger: ["input", "blur"]
	},
	shuffle_integration_id: {
		validator: (_rule, value: number | null) => {
			if (form.channel === "shuffle" && !value) {
				return createFieldError("shuffle_integration_id", "Pick a Shuffle integration")
			}
			clearFieldError("shuffle_integration_id")
			return true
		},
		trigger: ["change", "blur"]
	},
	shuffle_app_id: {
		validator: (_rule, value: string | null) => {
			if (form.channel === "shuffle" && !value) {
				return createFieldError("shuffle_app_id", "Pick a Shuffle app")
			}
			clearFieldError("shuffle_app_id")
			return true
		},
		trigger: ["change", "blur"]
	}
}

async function submit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	submitting.value = true
	try {
		const payload: NotificationRoutePayload = {
			...form,
			format_template: form.format_template?.trim() || null
		}

		const res = props.editingRoute
			? await Api.notifications.updateRoute(props.customerCode, props.editingRoute.id, payload)
			: await Api.notifications.createRoute(props.customerCode, payload)

		if (res.data.success) {
			message.success(editing.value ? "Route updated" : "Route created")
			emit("submitted")
		} else {
			message.warning(res.data.message || "Failed to save route")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to save route")
	} finally {
		submitting.value = false
	}
}

onBeforeMount(async () => {
	await loadIntegrations()
	// If editing a Shuffle route, prefetch the apps for its integration
	// so the picker is populated when the form first renders.
	if (props.editingRoute?.shuffle_integration_id) {
		await loadApps(props.editingRoute.shuffle_integration_id)
	}
})
</script>
