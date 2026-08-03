<template>
	<n-form ref="formRef" :model="form" :rules label-placement="top" class="flex flex-col gap-1.5">
		<!--
			The legacy per-customer Shuffle workflow also fires on alert creation.
			Both are opt-in, so duplication only happens when an operator configures
			both — which is exactly the moment to say so.
		-->
		<n-alert
			v-if="showsLegacyWorkflowWarning"
			type="warning"
			:bordered="false"
			title="This customer already notifies on alert creation"
			class="mb-3"
		>
			A legacy Notification Workflow is enabled for this customer, under the
			<strong>Notification Workflows</strong>
			tab. Saving this route means new alerts will notify twice — once through each. Disable one if that isn't
			what you want.
		</n-alert>

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

			<n-form-item label="Shuffle app" path="config.app_id">
				<n-select
					v-model:value="cfg.app_id"
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
				<n-form-item label="Webhook URL" path="config.url">
					<n-input v-model:value="cfg.url" placeholder="https://example.com/webhook/abc-123" type="text" />
				</n-form-item>

				<n-form-item label="Method" path="config.method">
					<n-select v-model:value="cfg.method" :options="methodOptions" />
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
				<n-checkbox v-model:checked="cfg.include_full_report" :disabled="fullReportDisabled">
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

		<!-- ===== Resend (email) channel fields ===== -->
		<template v-else-if="isResend">
			<n-form-item label="Deliver to" path="recipient_mode">
				<n-select v-model:value="form.recipient_mode" :options="recipientModeOptions" />
				<template #feedback>
					<span v-if="isAssigneeMode">
						Sent to whoever the alert or task is assigned to, resolved from their CoPilot account at
						delivery time. Events with no assignee are skipped.
					</span>
					<span v-else>Sent to a fixed list of addresses.</span>
				</template>
			</n-form-item>

			<n-form-item v-if="!isAssigneeMode" label="To" path="config.to">
				<n-dynamic-input
					v-model:value="toAddresses"
					:on-create="() => ''"
					placeholder="soc@example.com"
					class="w-full"
				/>
			</n-form-item>

			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<n-form-item label="From (optional)" path="config.from_address">
					<n-input v-model:value="cfg.from_address" placeholder="alerts@yourdomain.com" />
					<template #feedback>
						Must be on a domain verified in Resend. Leave empty to use the deployment default.
					</template>
				</n-form-item>

				<n-form-item label="Reply-to (optional)" path="config.reply_to">
					<n-input v-model:value="cfg.reply_to" placeholder="soc@yourdomain.com" />
				</n-form-item>
			</div>

			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<n-form-item label="Subject prefix" path="config.subject_prefix">
					<n-input v-model:value="cfg.subject_prefix" placeholder="[CoPilot]" />
				</n-form-item>

				<n-form-item label="Max emails per hour" path="config.max_per_hour">
					<n-input-number v-model:value="cfg.max_per_hour" :min="1" clearable class="w-full" />
					<template #feedback>Clear to disable the throttle.</template>
				</n-form-item>
			</div>

			<n-alert v-if="quota" :type="quotaTone" :bordered="false" class="mb-3">
				<template v-if="!quota.configured">
					The Resend connector has no API key set — routes on this channel will fail until it is configured.
				</template>
				<template v-else>
					{{ quota.sent_this_month }} of {{ quota.limit }} emails sent this month, across all customers.
					Resend's allowance is deployment-wide, so every route draws from the same pool.
				</template>
			</n-alert>
		</template>

		<!-- Any channel without a hand-written block above renders from the JSON
		     Schema its provider advertises, so adding one needs no frontend work. -->
		<template v-else-if="activeDescriptor">
			<ChannelConfigFields
				:descriptor="activeDescriptor"
				:model="cfg"
				@update="(key, value) => (cfg[key as keyof EditableChannelConfig] = value as never)"
			/>
		</template>

		<n-form-item label="Shared template (optional)" :show-feedback="false">
			<n-select
				v-model:value="form.template_id"
				:options="templateOptions"
				:loading="loadingTemplates"
				:disabled="templateDisabled"
				clearable
				placeholder="Use the channel default"
			/>
		</n-form-item>
		<div class="text-secondary mb-2 text-xs">
			Only templates this route can actually render are listed — a template scoped to another trigger or customer,
			or in a format this channel can't render, is left out.
			<router-link :to="{ name: 'NotificationTemplates' }" class="underline">Manage templates</router-link>
		</div>

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
				Leave empty to use the shared template above, or the channel default when there is none. Substitutions:
				<code>{{ substitutionTokens }}</code>
			</template>
		</div>
		<div v-if="overridesSharedTemplate" class="text-secondary mb-2 text-xs italic">
			This one-off template overrides the shared one for this route only.
		</div>

		<n-form-item>
			<n-checkbox v-model:checked="form.enabled">Enabled</n-checkbox>
		</n-form-item>

		<div class="flex flex-wrap items-center justify-end gap-2">
			<!--
				Only offered on a saved route: the test sends through the STORED
				config, so offering it on unsaved edits would test something the
				operator isn't looking at.
			-->
			<n-button v-if="editing" secondary :loading="testing" class="mr-auto" @click="sendTest">
				<template #icon>
					<Icon :name="TestIcon" :size="14" />
				</template>
				Send test
			</n-button>
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
	NotificationChannelDescriptor,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationScope,
	NotificationSeverity,
	NotificationTemplate,
	NotificationTrigger,
	ResendQuota,
	ShuffleApp,
	ShuffleIntegration
} from "@/types/notifications"
import {
	NAlert,
	NButton,
	NCheckbox,
	NDynamicInput,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NSelect,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import ChannelConfigFields from "./ChannelConfigFields.vue"

const props = defineProps<{
	// Empty for internal-scope routes, which belong to no tenant.
	customerCode?: string
	editingRoute: NotificationRoute | null
	scope?: NotificationScope
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

// Channel settings live in a JSON `config` blob on the route, whose shape each
// backend provider owns. The form keeps them in a flat reactive object and
// serialises on submit, so adding a field to a provider's schema doesn't
// require a matching field here.
// Union of the keys the hand-written channel blocks below bind to. Channels
// without a bespoke block are rendered generically from their advertised JSON
// Schema instead, so this deliberately does NOT try to cover every channel.
interface EditableChannelConfig {
	app_id?: string | null
	app_name?: string | null
	url?: string | null
	method?: string
	headers?: Record<string, string> | null
	include_full_report?: boolean
	to?: string[]
	cc?: string[]
	from_address?: string | null
	reply_to?: string | null
	subject_prefix?: string
	max_per_hour?: number | null
}

const cfg = reactive<EditableChannelConfig>({ ...(props.editingRoute?.config ?? {}) })

const fieldErrors = reactive<Partial<Record<FeedbackField, string>>>({})

const form = reactive<NotificationRoutePayload>({
	name: props.editingRoute?.name ?? "",
	trigger:
		props.editingRoute?.trigger ??
		((props.scope === "internal" ? "alert_assigned" : "alert_created") as NotificationTrigger),
	channel: props.editingRoute?.channel ?? (props.scope === "internal" ? "resend" : "shuffle"),
	destination: props.editingRoute?.destination ?? "",
	min_severity: props.editingRoute?.min_severity ?? ("Medium" as NotificationSeverity),
	format_template: props.editingRoute?.format_template ?? "",
	template_id: props.editingRoute?.template_id ?? null,
	enabled: props.editingRoute?.enabled ?? true,
	scope: props.editingRoute?.scope ?? "customer",
	recipient_mode: props.editingRoute?.recipient_mode ?? "static",
	notify_on_self_assign: props.editingRoute?.notify_on_self_assign ?? false,
	shuffle_integration_id: props.editingRoute?.shuffle_integration_id ?? null,
	config: {}
})

const isShuffle = computed(() => form.channel === "shuffle")
// The same form serves both surfaces. They differ in exactly two ways — which
// triggers apply and which channels are possible — so a prop is cheaper and
// safer than extracting shared parts out of a 700-line component. If the
// conditionals multiply beyond these, that's the signal to split it.
const isInternalScope = computed(() => props.scope === "internal")

// Non-null only when the customer has a legacy workflow enabled. Fetched once
// per form open; a failure leaves it null so the warning simply doesn't show
// rather than blocking the form.
const legacyWorkflowEnabled = ref<boolean | null>(null)

const showsLegacyWorkflowWarning = computed(
	() => !isInternalScope.value && form.trigger === "alert_created" && legacyWorkflowEnabled.value === true
)

async function loadLegacyWorkflowState() {
	if (isInternalScope.value || !props.customerCode) return
	try {
		const res = await Api.incidentManagement.notification.getNotifications(props.customerCode)
		const rows = res.data?.notifications ?? []
		legacyWorkflowEnabled.value = rows.some(n => n.enabled)
	} catch {
		legacyWorkflowEnabled.value = null
	}
}

// The channel catalog drives the generic fallback renderer. Loaded once per
// form open; a failure just means an unknown channel shows no config fields
// rather than the form breaking.
const channels = ref<NotificationChannelDescriptor[]>([])
const activeDescriptor = computed(() => channels.value.find(c => c.key === form.channel) ?? null)

async function loadChannels() {
	try {
		const res = await Api.notifications.getChannels()
		if (res.data.success) channels.value = res.data.channels
	} catch {
		channels.value = []
	}
}

const TestIcon = "carbon:send-alt"
const testing = ref(false)

async function sendTest() {
	if (!props.editingRoute) return
	testing.value = true
	try {
		const routeId = props.editingRoute.id
		const code = props.customerCode
		const res =
			isInternalScope.value || !code
				? await Api.notifications.testInternalRoute(routeId)
				: await Api.notifications.testRoute(code, routeId)

		// The endpoint reports the delivery outcome rather than throwing on a
		// failed send: "domain not verified" is information, not an error state.
		if (res.data.status === "sent") {
			message.success(`Test sent via ${res.data.channel} in ${res.data.latency_ms ?? "?"}ms`)
		} else {
			message.warning(res.data.error_message || `Test ${res.data.status}`)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as never) || "Failed to send test notification")
	} finally {
		testing.value = false
	}
}

const isWebhook = computed(() => form.channel === "webhook")
const isResend = computed(() => form.channel === "resend")
const isAssigneeMode = computed(() => form.recipient_mode === "assignee")

// n-dynamic-input binds an array of strings; cfg.to is the source of truth.
const toAddresses = computed({
	get: () => cfg.to ?? [],
	set: (v: string[]) => {
		cfg.to = v
	}
})

const recipientModeOptions = [
	{ label: "A fixed list of addresses", value: "static" },
	{ label: "Whoever it's assigned to", value: "assignee" }
]

// Deployment-wide, not per-customer: one API key, one allowance. Fetched only
// when the channel is actually Resend so other routes don't pay for it.
const quota = ref<ResendQuota | null>(null)
const quotaTone = computed(() => {
	if (!quota.value?.configured) return "warning"
	const used = quota.value.sent_this_month / Math.max(quota.value.limit, 1)
	return used >= 0.9 ? "error" : used >= 0.7 ? "warning" : "info"
})

async function loadQuota() {
	if (!isResend.value || quota.value) return
	try {
		const res = await Api.notifications.getResendQuota(props.customerCode)
		if (res.data.success) {
			quota.value = {
				sent_this_month: res.data.sent_this_month,
				limit: res.data.limit,
				customer_sent: res.data.customer_sent,
				configured: res.data.configured
			}
		}
	} catch {
		// Non-fatal: the indicator is informational, and a failure here must not
		// block someone from saving a route.
	}
}

// Mutual exclusivity (webhook only): "include full report" and a custom
// template are two alternative body modes. Ticking the box disables the
// template; writing a template disables the box. Each lane can still get
// the report — the box for the structured payload, the {{report}} token
// for the template.
const templateDisabled = computed(() => isWebhook.value && Boolean(cfg.include_full_report))

// ----- Shared templates (#1038) -----
//
// Precedence at send time is: this route's inline `format_template`, then the
// shared template picked here, then the channel default. The picker filters
// client-side using the same rules the server enforces on save, so an operator
// never picks something that's then refused.
const templates = ref<NotificationTemplate[]>([])
const loadingTemplates = ref(false)

async function loadTemplates() {
	loadingTemplates.value = true
	try {
		// Not filtered by trigger server-side: the trigger can change while the
		// form is open, and re-fetching on every change would be a round trip
		// per keystroke-equivalent. Filtering happens in `templateOptions`.
		const res = await Api.notifications.listTemplates({ customerCode: props.customerCode })
		templates.value = res.data.success ? res.data.templates : []
	} catch {
		// A failed list only costs the picker — the route is still saveable
		// with an inline template or the channel default.
		templates.value = []
	} finally {
		loadingTemplates.value = false
	}
}

const templateOptions = computed(() =>
	templates.value
		.filter(t => {
			// Trigger-agnostic templates work anywhere; a scoped one only on its
			// own trigger, since it's written around that event's variables.
			if (t.trigger && t.trigger !== form.trigger) return false
			// An internal route belongs to no tenant, so a customer-scoped
			// template would leak that customer's branding to the SOC.
			if (t.customer_code && isInternalScope.value) return false
			if (t.customer_code && props.customerCode && t.customer_code !== props.customerCode) return false
			// Only email renders HTML; a chat card would show the markup.
			const formats = activeDescriptor.value?.template_formats
			if (formats?.length && !formats.includes(t.format)) return false
			return true
		})
		.map(t => ({
			label: t.customer_code ? `${t.name} (${t.customer_code})` : t.name,
			value: t.id
		}))
)

// The inline box wins over the picker, so say so rather than letting the
// operator wonder which one is in effect.
const overridesSharedTemplate = computed(() => Boolean(form.template_id) && Boolean(form.format_template?.trim()))
const fullReportDisabled = computed(() => isWebhook.value && Boolean(form.format_template?.trim()))
// Shown literally in the help text. Kept as a constant so the template
// doesn't nest {{ }} inside an interpolation (Vue can't parse that).
const reportToken = "{{report}}"

// Custom headers are edited as an ordered key/value list and converted to
// a Record on submit. Seed from the editing route's stored headers.
const headerPairs = ref<{ key: string; value: string }[]>(
	props.editingRoute?.config?.headers
		? Object.entries(props.editingRoute.config.headers as Record<string, string>).map(([key, value]) => ({
				key,
				value
			}))
		: []
)

// Triggers are filtered by scope rather than shown as one list. A customer
// route with an assignment trigger would be dead config: assignments resolve
// against internal routes, so it could never fire. Offering it would be an
// invitation to create something that silently does nothing.
const CUSTOMER_TRIGGER_OPTIONS = [
	{ label: "An alert is created", value: "alert_created" },
	{ label: "An AI investigation completes", value: "investigation_complete" },
	// Legacy value kept selectable so editing an old route doesn't blank the
	// field; the backend coerces it to investigation_complete on read.
	{ label: "Critical / High severity only (legacy)", value: "severity_critical_or_high" }
]

const INTERNAL_TRIGGER_OPTIONS = [
	{ label: "An alert is assigned", value: "alert_assigned" },
	{ label: "A case is assigned", value: "case_assigned" },
	{ label: "A case task is assigned", value: "case_task_assigned" }
]

const triggerOptions = computed(() => (isInternalScope.value ? INTERNAL_TRIGGER_OPTIONS : CUSTOMER_TRIGGER_OPTIONS))

// Derived from the channel catalog rather than a hardcoded list, so adding a
// channel needs no change here. Providers declare whether they can serve an
// internal route: Shuffle can't, because its org is an FK to a per-customer
// table and an internal route has no tenant.
const channelOptions = computed(() => {
	const available = isInternalScope.value ? channels.value.filter(c => c.supports_internal_scope) : channels.value

	// Before the catalog loads, fall back to whatever the route already uses so
	// the select isn't briefly empty when editing.
	if (!available.length) {
		return [{ label: form.channel, value: form.channel }]
	}
	return available.map(c => ({ label: c.display_name, value: c.key }))
})

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
	if (channel !== "resend" && form.recipient_mode === "assignee") {
		// Only email can resolve a person; leaving the mode set would fail the
		// provider's supports_recipient_modes check on save.
		form.recipient_mode = "static"
	}
	if (channel === "resend") {
		if (!cfg.subject_prefix) cfg.subject_prefix = "[CoPilot]"
		if (cfg.max_per_hour === undefined) cfg.max_per_hour = 20
		loadQuota()
	}
	if (channel === "webhook" && !cfg.method) {
		cfg.method = "POST"
	}
}

async function loadIntegrations() {
	// Shuffle integrations are per-customer, so there is nothing to load for an
	// internal route — and no customerCode to load it with.
	const code = props.customerCode
	if (!code) return

	loadingIntegrations.value = true
	try {
		const res = await Api.notifications.listShuffleIntegrations(code)
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
	const code = props.customerCode
	if (!code) return

	loadingApps.value = true
	appsError.value = null
	try {
		const res = await Api.notifications.listShuffleApps(code, integrationId)
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
	cfg.app_id = null
	cfg.app_name = null
	if (integrationId) {
		await loadApps(integrationId)
	}
}

function onAppChange(appId: string | null) {
	// Cache the app's display name alongside the UUID so the UI list can
	// render "Slack" instead of a UUID without re-fetching the catalog.
	const app = apps.value.find(a => a.id === appId)
	cfg.app_name = app?.name ?? null
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
		const sendTemplate =
			isWebhook.value && Boolean(cfg.include_full_report) ? null : form.format_template?.trim() || null

		const base = {
			name: form.name,
			trigger: form.trigger,
			channel: form.channel,
			min_severity: form.min_severity,
			format_template: sendTemplate,
			// Explicit null rather than omitted, so clearing the picker detaches
			// the template instead of silently leaving the old one attached.
			template_id: form.template_id ?? null,
			enabled: form.enabled,
			scope: props.scope ?? "customer",
			recipient_mode: form.recipient_mode,
			notify_on_self_assign: form.notify_on_self_assign
		}

		// Build config from scratch per channel rather than sending the whole
		// `cfg` object: switching channels leaves the other branch's keys in
		// there, and the backend's config schemas use extra="forbid", so a
		// leftover `url` on a shuffle route is a 400 rather than a no-op.
		const payload: NotificationRoutePayload = isWebhook.value
			? {
					...base,
					destination: null,
					shuffle_integration_id: null,
					config: {
						url: cfg.url?.trim() || null,
						method: cfg.method || "POST",
						headers: buildHeaders(),
						include_full_report: Boolean(cfg.include_full_report)
					}
				}
			: isResend.value
				? {
						...base,
						destination: null,
						shuffle_integration_id: null,
						config: {
							// Assignee mode resolves the address from the event, so an
							// unused `to` list is dropped rather than persisted as a
							// fallback it would never act as.
							to: isAssigneeMode.value ? [] : (cfg.to ?? []).filter(a => a.trim().length > 0),
							cc: (cfg.cc ?? []).filter(a => a.trim().length > 0),
							from_address: cfg.from_address?.trim() || null,
							reply_to: cfg.reply_to?.trim() || null,
							subject_prefix: cfg.subject_prefix ?? "[CoPilot]",
							max_per_hour: cfg.max_per_hour ?? null
						}
					}
				: {
						...base,
						destination: form.destination,
						shuffle_integration_id: form.shuffle_integration_id,
						config: {
							app_id: cfg.app_id ?? null,
							app_name: cfg.app_name ?? null
						}
					}

		let res
		if (isInternalScope.value) {
			res = props.editingRoute
				? await Api.notifications.updateInternalRoute(props.editingRoute.id, payload)
				: await Api.notifications.createInternalRoute(payload)
		} else {
			// customerCode is optional on the props because internal routes have
			// none; on this branch it is always present, and a missing one is a
			// wiring bug worth surfacing rather than sending "" to the API.
			const code = props.customerCode
			if (!code) {
				message.error("No customer selected for this route.")
				return
			}
			res = props.editingRoute
				? await Api.notifications.updateRoute(code, props.editingRoute.id, payload)
				: await Api.notifications.createRoute(code, payload)
		}

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
	loadChannels()
	loadTemplates()
	loadLegacyWorkflowState()
	await loadIntegrations()
	// If editing a Shuffle route, prefetch the apps for its integration
	// so the picker is populated when the form first renders.
	if (props.editingRoute?.shuffle_integration_id) {
		await loadApps(props.editingRoute.shuffle_integration_id)
	}
})
</script>
