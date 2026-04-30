<template>
	<n-form
		ref="formRef"
		:model="form"
		:rules="rules"
		label-placement="top"
		class="px-7 py-4"
	>
		<div class="mb-3 flex items-center justify-between">
			<h3 class="text-lg font-medium">{{ editing ? "Edit route" : "Add route" }}</h3>
			<n-button size="small" quaternary @click="$emit('close')">
				<template #icon>
					<Icon :name="CloseIcon" :size="14" />
				</template>
				Cancel
			</n-button>
		</div>

		<n-form-item label="Name" path="name">
			<n-input
				v-model:value="form.name"
				placeholder="e.g. SOC team Slack #alerts"
				:maxlength="128"
				show-count
			/>
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
			Channel is now Shuffle-only — the SMTP path was removed when we
			consolidated email delivery into Shuffle's catalog (Outlook,
			Gmail, SendGrid, SMTP-via-Shuffle, etc. all live there). Field
			stays in the form for clarity but is fixed to a single value.
		-->
		<n-form-item label="Channel">
			<n-select v-model:value="form.channel" :options="channelOptions" disabled />
			<template #feedback>
				<span class="text-tertiary text-xs">
					All notifications dispatch through Shuffle's authenticated apps —
					Slack, Teams, Outlook, Gmail, ServiceNow, PagerDuty, and 3,000+ more.
				</span>
			</template>
		</n-form-item>

		<n-form-item label="Shuffle integration" path="shuffle_integration_id">
			<div class="flex w-full flex-col gap-1">
				<n-select
					v-model:value="form.shuffle_integration_id"
					:options="integrationOptions"
					placeholder="Pick a Shuffle org for this customer"
					:loading="loadingIntegrations"
					@update:value="onIntegrationChange"
				/>
				<div v-if="!integrationOptions.length && !loadingIntegrations" class="text-tertiary text-xs">
					No Shuffle integrations configured for this customer yet — go to the
					<strong>Shuffle integrations</strong> tab to add one first.
				</div>
			</div>
		</n-form-item>

		<n-form-item label="Shuffle app" path="shuffle_app_id">
			<div class="flex w-full flex-col gap-1">
				<n-select
					v-model:value="form.shuffle_app_id"
					:options="appOptions"
					placeholder="Pick an authenticated app"
					:loading="loadingApps"
					:disabled="!form.shuffle_integration_id || loadingApps"
					filterable
					@update:value="onAppChange"
				/>
				<div
					v-if="form.shuffle_integration_id && !appOptions.length && !loadingApps && appsError"
					class="text-error text-xs"
				>
					Couldn't fetch apps from Shuffle: {{ appsError }}
				</div>
			</div>
		</n-form-item>

		<n-form-item label="Destination hint" path="destination">
			<n-input
				v-model:value="form.destination"
				placeholder="e.g. #soc-alerts, soc@example.com, @user-id"
				type="text"
			/>
			<template #feedback>
				<span class="text-tertiary text-xs">
					Free-form — gets prepended to the outgoing message as a
					<code>Send to &lt;destination&gt;: …</code> hint so the Shuffle app
					agent knows where to deliver. Channel name for Slack, email for
					Outlook / Gmail, handle for chat apps, etc.
				</span>
			</template>
		</n-form-item>

		<n-form-item label="Custom message template (optional)" path="format_template">
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
import type {
	NotificationRoute,
	NotificationRoutePayload,
	NotificationSeverity,
	NotificationTrigger,
	ShuffleApp,
	ShuffleIntegration
} from "@/types/notifications.d"
import type { FormInst, FormRules } from "naive-ui"
import { NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCode: string
	editingRoute: NotificationRoute | null
}>()

const emit = defineEmits<{
	(e: "submitted"): void
	(e: "close"): void
}>()

const CloseIcon = "carbon:close"

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const editing = computed(() => props.editingRoute !== null)

// Channel is hard-coded to "shuffle" — the SMTP path was removed.
// Existing routes loaded via the editing path may have legacy values
// in the DB; we still use the route's channel as-is on edit (fall
// back to "shuffle" for new routes).
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
	shuffle_app_name: props.editingRoute?.shuffle_app_name ?? null
})

const triggerOptions = [
	{ label: "Every investigation completes", value: "investigation_complete" },
	{ label: "Critical / High severity only", value: "severity_critical_or_high" }
]

// Single-option list — keeps the n-select rendering consistent with
// the rest of the form even though there's nothing to pick. If we
// ever add a second channel back (e.g. raw webhook), this is the line
// to extend.
const channelOptions = [{ label: "Shuffle (Slack / Teams / Outlook / 3,000+ apps)", value: "shuffle" }]

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
	trigger: { required: true, message: "Pick a trigger", trigger: ["change", "blur"] },
	min_severity: { required: true, message: "Pick a severity threshold", trigger: ["change", "blur"] },
	destination: {
		required: true,
		message: "Destination hint is required",
		trigger: ["input", "blur"]
	},
	shuffle_integration_id: {
		required: true,
		validator: (_rule, value: number | null) => {
			if (!value) return new Error("Pick a Shuffle integration")
			return true
		},
		trigger: ["change", "blur"]
	},
	shuffle_app_id: {
		required: true,
		validator: (_rule, value: string | null) => {
			if (!value) return new Error("Pick a Shuffle app")
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
