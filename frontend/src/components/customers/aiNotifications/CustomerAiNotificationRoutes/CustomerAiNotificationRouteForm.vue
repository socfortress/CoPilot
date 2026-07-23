<template>
	<n-form ref="formRef" :model="form" :rules label-placement="top" class="flex flex-col gap-1">
		<n-form-item label="Name" path="name">
			<n-input v-model:value="form.name" placeholder="e.g. SOC team Slack #alerts" :maxlength="128" show-count />
		</n-form-item>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			<n-form-item label="Trigger" path="trigger">
				<n-select v-model:value="form.trigger" :options="triggerOptions" />
			</n-form-item>

			<n-form-item label="Minimum severity" path="min_severity">
				<n-select v-model:value="form.min_severity" :options="severityOptions" />
			</n-form-item>
		</div>

		<!--
			Channel picks the delivery path. Shuffle proxies to a customer's
			authenticated Shuffle org (Slack / Teams / Outlook / 3,000+ apps);
			Webhook POSTs directly to any URL (automation platforms, chat
			webhooks, custom endpoints) with no Shuffle in the path.
		-->
		<n-form-item label="Channel" path="channel">
			<n-select v-model:value="form.channel" :options="channelOptions" @update:value="onChannelChange" />
			<template #feedback>
				<span v-if="isWebhook">
					Direct HTTP POST/PUT to a URL you control — automation platforms, chat incoming webhooks, custom
					endpoints, etc. No Shuffle org required.
				</span>
				<span v-else>
					Shuffle proxies to 3,000+ integrations through a customer's authenticated Shuffle org.
				</span>
			</template>
		</n-form-item>

		<!-- ===== Shuffle channel fields ===== -->
		<template v-if="isShuffle">
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
				<template v-if="showShuffleAppsFetchError" #feedback>
					<div class="text-error">Couldn't fetch apps from Shuffle: {{ appsError }}</div>
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
					hint so the Shuffle app agent knows where to deliver. Channel name for Slack, email for Outlook /
					Gmail, handle for chat apps, etc.
				</template>
			</n-form-item>
		</template>

		<!-- ===== Webhook channel fields ===== -->
		<template v-else-if="isWebhook">
			<div class="grid grid-cols-1 gap-4 md:grid-cols-[1fr_140px]">
				<n-form-item label="Webhook URL" path="webhook_url">
					<n-input
						v-model:value="form.webhook_url"
						placeholder="https://example.com/webhook/abc-123"
						type="text"
					/>
				</n-form-item>

				<n-form-item label="Method" path="webhook_method">
					<n-select v-model:value="form.webhook_method" :options="methodOptions" />
				</n-form-item>
			</div>

			<n-form-item label="Custom headers (optional)" :show-feedback="false">
				<n-dynamic-input v-model:value="headerPairs" :on-create="() => ({ key: '', value: '' })" class="w-full">
					<template #default="{ value }">
						<div class="flex w-full items-center gap-2">
							<n-input v-model:value="value.key" placeholder="Header name (e.g. Authorization)" />
							<n-input v-model:value="value.value" placeholder="Header value (e.g. Bearer …)" />
						</div>
					</template>
				</n-dynamic-input>
			</n-form-item>
			<div class="text-secondary mb-2 text-xs">
				Sent on every request. Use for auth tokens (e.g.
				<code>Authorization: Bearer …</code>
				or
				<code>X-API-Key</code>
				). Leave empty if the URL itself carries the secret (Discord / Slack).
			</div>

			<n-form-item :show-feedback="false">
				<n-checkbox v-model:checked="form.include_full_report" :disabled="fullReportDisabled">
					Include full AI report
				</n-checkbox>
			</n-form-item>
			<div class="text-secondary mb-2 text-xs">
				Adds the full AI report to the payload — the recommended actions, the full markdown write-up, and the
				IOC list — for automation agents that need more than the summary. Leave off for chat targets to keep the
				payload small.
				<template v-if="fullReportDisabled">
					<br />
					<em>
						Unavailable while a custom template is set — use the
						<code>{{ reportToken }}</code>
						token in the template instead.
					</em>
				</template>
			</div>
		</template>

		<n-form-item label="Custom message template (optional)" path="format_template" :show-feedback="false">
			<n-input
				v-model:value="form.format_template"
				type="textarea"
				:autosize="{ minRows: 4, maxRows: 12 }"
				:placeholder="templatePlaceholder"
				:disabled="templateDisabled"
			/>
		</n-form-item>
		<div class="text-secondary mb-2 text-xs">
			<template v-if="templateDisabled">
				<em>
					Unavailable while
					<strong>Include full AI report</strong>
					is ticked — the full structured payload is sent. Untick it to write a custom body.
				</em>
			</template>
			<template v-else-if="isWebhook">
				Leave empty to send a structured JSON payload (
				<code>customer_code</code>
				,
				<code>alert_id</code>
				,
				<code>severity</code>
				,
				<code>summary</code>
				,
				<code>report_url</code>
				,
				<code>text</code>
				). Set a template to send a custom body instead — if it's valid JSON it's sent as JSON (e.g.
				<code>{"content": "…"}</code>
				), otherwise as plain text. Available tokens:
				<code>{{ substitutionTokens }}</code>
				. To include the full AI report, place
				<code>{{ reportToken }}</code>
				unquoted as a JSON value (e.g.
				<code>"report": {{ reportToken }}</code>
				).
			</template>
			<template v-else>
				Leave empty to use the default. Substitutions:
				<code>{{ substitutionTokens }}</code>
			</template>
		</div>

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
} from "@/types/notifications"
import { NButton, NCheckbox, NDynamicInput, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
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
type FeedbackField =
	"channel" | "destination" | "min_severity" | "shuffle_app_id" | "shuffle_integration_id" | "webhook_url"

const fieldErrors = reactive<Partial<Record<FeedbackField, string>>>({})

const form = reactive<NotificationRoutePayload>({
	name: props.editingRoute?.name ?? "",
	trigger: props.editingRoute?.trigger ?? ("investigation_complete" as NotificationTrigger),
	channel: props.editingRoute?.channel ?? "shuffle",
	destination: props.editingRoute?.destination ?? "",
	min_severity: props.editingRoute?.min_severity ?? ("Medium" as NotificationSeverity),
	format_template: props.editingRoute?.format_template ?? "",
	enabled: props.editingRoute?.enabled ?? true,
	shuffle_integration_id: props.editingRoute?.shuffle_integration_id ?? null,
	shuffle_app_id: props.editingRoute?.shuffle_app_id ?? null,
	shuffle_app_name: props.editingRoute?.shuffle_app_name ?? null,
	webhook_url: props.editingRoute?.webhook_url ?? null,
	webhook_method: props.editingRoute?.webhook_method ?? "POST",
	include_full_report: props.editingRoute?.include_full_report ?? false
})

const isShuffle = computed(() => form.channel === "shuffle")
const isWebhook = computed(() => form.channel === "webhook")

// Mutual exclusivity (webhook only): "include full report" and a custom
// template are two alternative body modes. Ticking the box disables the
// template; writing a template disables the box. Each lane can still get
// the report — the box for the structured payload, the {{report}} token
// for the template.
const templateDisabled = computed(() => isWebhook.value && form.include_full_report)
const fullReportDisabled = computed(() => isWebhook.value && Boolean(form.format_template?.trim()))
// Shown literally in the help text. Kept as a constant so the template
// doesn't nest {{ }} inside an interpolation (Vue can't parse that).
const reportToken = "{{report}}"

// Custom headers are edited as an ordered key/value list and converted to
// a Record on submit. Seed from the editing route's stored headers.
const headerPairs = ref<{ key: string; value: string }[]>(
	props.editingRoute?.webhook_headers
		? Object.entries(props.editingRoute.webhook_headers).map(([key, value]) => ({ key, value }))
		: []
)

// Trigger is a single fixed value today (`investigation_complete`).
// Will become a richer select again when we add more dispatch event
// types (analyst-review hooks, IOC-enrichment alerts, scheduled sweeps).
const triggerOptions = [
	{ label: "Every investigation completes", value: "investigation_complete" },
	{ label: "Critical / High severity only", value: "severity_critical_or_high" }
]

const channelOptions = [
	{ label: "Shuffle (Slack / Teams / Outlook / 3,000+ apps)", value: "shuffle" },
	{ label: "Webhook (direct HTTP to any URL)", value: "webhook" }
]

const methodOptions = [
	{ label: "POST", value: "POST" },
	{ label: "PUT", value: "PUT" }
]

const severityOptions = [
	{ label: "Critical (only)", value: "Critical" },
	{ label: "High and above", value: "High" },
	{ label: "Medium and above", value: "Medium" },
	{ label: "Low and above", value: "Low" },
	{ label: "Informational and above (everything)", value: "Informational" }
]

const templatePlaceholder = computed(() =>
	isWebhook.value
		? 'Leave empty for structured JSON. Example custom body: {"content": "[{{severity}}] {{alert_name}} — {{summary}}"}'
		: "Leave empty to use the default. Substitutions: {{customer_code}} {{alert_id}} {{alert_name}} {{severity}} {{summary}} {{report_url}}"
)

// Displayed as literal text in the help line. Kept as a script constant so
// the template doesn't nest `{{ }}` inside an interpolation — Vue's compiler
// closes the interpolation at the first inner `}}` and fails to parse.
const substitutionTokens = "{{customer_code}} {{alert_id}} {{alert_name}} {{severity}} {{summary}} {{report_url}}"

// Shuffle integrations + apps state. Integrations are fetched on form
// open; apps are fetched lazily when an integration is picked.
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

const showShuffleAppsFetchError = computed(
	() =>
		!fieldErrors.shuffle_app_id &&
		Boolean(form.shuffle_integration_id) &&
		appOptions.value.length === 0 &&
		!loadingApps.value &&
		Boolean(appsError.value)
)

function clearFieldError(field: FeedbackField) {
	delete fieldErrors[field]
}

function createFieldError(field: FeedbackField, message: string) {
	fieldErrors[field] = message
	return new Error(message)
}

function onChannelChange(channel: NotificationChannel) {
	// Clear any stale per-channel validation feedback when switching.
	clearFieldError("shuffle_integration_id")
	clearFieldError("shuffle_app_id")
	clearFieldError("destination")
	clearFieldError("webhook_url")
	if (channel === "webhook" && !form.webhook_method) {
		form.webhook_method = "POST"
	}
}

async function loadIntegrations() {
	loadingIntegrations.value = true
	try {
		const res = await Api.notifications.listShuffleIntegrations(props.customerCode)
		if (res.data.success) {
			integrations.value = res.data.integrations
		}
	} catch (err) {
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
	} catch (err) {
		apps.value = []
		appsError.value = getApiErrorMessage(err as never) || "Failed to load apps"
	} finally {
		loadingApps.value = false
	}
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
	// render "Slack" instead of a UUID without re-fetching the catalog.
	const app = apps.value.find(a => a.id === appId)
	form.shuffle_app_name = app?.name ?? null
}

const rules: FormRules = {
	name: { required: true, message: "Name is required", trigger: ["input", "blur"] },
	trigger: { required: true, message: "Pick a trigger", trigger: ["change", "blur"] },
	min_severity: {
		validator: (_rule, value: NotificationSeverity | null) => {
			if (!value) return createFieldError("min_severity", "Pick a severity threshold")
			clearFieldError("min_severity")
			return true
		},
		trigger: ["change", "blur"]
	},
	destination: {
		// Required for Shuffle only — webhook routes don't use it.
		validator: (_rule, value: string) => {
			if (isShuffle.value && (!value || !value.trim())) {
				return createFieldError("destination", "Destination hint is required")
			}
			clearFieldError("destination")
			return true
		},
		trigger: ["input", "blur"]
	},
	shuffle_integration_id: {
		validator: (_rule, value: number | null) => {
			if (isShuffle.value && !value) {
				return createFieldError("shuffle_integration_id", "Pick a Shuffle integration")
			}
			clearFieldError("shuffle_integration_id")
			return true
		},
		trigger: ["change", "blur"]
	},
	shuffle_app_id: {
		validator: (_rule, value: string | null) => {
			if (isShuffle.value && !value) return createFieldError("shuffle_app_id", "Pick a Shuffle app")
			clearFieldError("shuffle_app_id")
			return true
		},
		trigger: ["change", "blur"]
	},
	webhook_url: {
		validator: (_rule, value: string | null) => {
			if (!isWebhook.value) {
				clearFieldError("webhook_url")
				return true
			}
			if (!value || !value.trim()) {
				return createFieldError("webhook_url", "Webhook URL is required")
			}
			if (!/^https?:\/\//i.test(value.trim())) {
				return createFieldError("webhook_url", "URL must start with http:// or https://")
			}
			clearFieldError("webhook_url")
			return true
		},
		trigger: ["input", "blur"]
	}
}

function buildHeaders(): Record<string, string> | null {
	const entries = headerPairs.value.map(p => [p.key.trim(), p.value]).filter(([k]) => k.length > 0) as [
		string,
		string
	][]
	return entries.length ? Object.fromEntries(entries) : null
}

async function submit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	submitting.value = true
	try {
		// Build a channel-clean payload: only send the fields relevant to
		// the selected channel so we don't persist stale values from the
		// other branch (e.g. a Shuffle app id left over after switching).
		// Full report and a custom template are mutually exclusive — if the
		// box is ticked, never persist a template (the structured payload is
		// sent). Keeps stored data consistent with the UI's grey-out.
		const sendTemplate = isWebhook.value && form.include_full_report ? null : form.format_template?.trim() || null

		const base = {
			name: form.name,
			trigger: form.trigger,
			channel: form.channel,
			min_severity: form.min_severity,
			format_template: sendTemplate,
			enabled: form.enabled
		}

		const payload: NotificationRoutePayload = isWebhook.value
			? {
					...base,
					destination: null,
					webhook_url: form.webhook_url?.trim() || null,
					webhook_method: form.webhook_method || "POST",
					webhook_headers: buildHeaders(),
					include_full_report: form.include_full_report,
					shuffle_integration_id: null,
					shuffle_app_id: null,
					shuffle_app_name: null
				}
			: {
					...base,
					destination: form.destination,
					shuffle_integration_id: form.shuffle_integration_id,
					shuffle_app_id: form.shuffle_app_id,
					shuffle_app_name: form.shuffle_app_name,
					webhook_url: null,
					webhook_method: null,
					webhook_headers: null,
					include_full_report: false
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
	} catch (err) {
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
