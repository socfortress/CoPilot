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

		<n-form-item label="Channel" path="channel">
			<n-select v-model:value="form.channel" :options="channelOptions" />
		</n-form-item>

		<n-form-item :label="destinationLabel" path="destination">
			<n-input
				v-model:value="form.destination"
				:placeholder="destinationPlaceholder"
				type="text"
			/>
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
	NotificationChannel,
	NotificationRoute,
	NotificationRoutePayload,
	NotificationSeverity,
	NotificationTrigger
} from "@/types/notifications.d"
import type { FormInst, FormRules } from "naive-ui"
import { NButton, NCheckbox, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, reactive, ref } from "vue"
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

// Reactive form seeded from the editing route if present, else from
// reasonable defaults. Channel and trigger default to the values most
// admins want first ("every investigation" / Slack) so empty form is
// closer to "ready to type the destination" than "where do I start".
const editing = computed(() => props.editingRoute !== null)

const form = reactive<NotificationRoutePayload>({
	name: props.editingRoute?.name ?? "",
	trigger: props.editingRoute?.trigger ?? ("investigation_complete" as NotificationTrigger),
	channel: props.editingRoute?.channel ?? ("slack_webhook" as NotificationChannel),
	destination: props.editingRoute?.destination ?? "",
	min_severity: props.editingRoute?.min_severity ?? ("Medium" as NotificationSeverity),
	format_template: props.editingRoute?.format_template ?? "",
	enabled: props.editingRoute?.enabled ?? true
})

const triggerOptions = [
	{ label: "Every investigation completes", value: "investigation_complete" },
	{ label: "Critical / High severity only", value: "severity_critical_or_high" }
]

const channelOptions = [
	{ label: "Slack incoming webhook", value: "slack_webhook" },
	{ label: "Email (SMTP)", value: "smtp_email" }
]

const severityOptions = [
	{ label: "Critical (only)", value: "Critical" },
	{ label: "High and above", value: "High" },
	{ label: "Medium and above", value: "Medium" },
	{ label: "Low and above", value: "Low" },
	{ label: "Informational and above (everything)", value: "Informational" }
]

const destinationLabel = computed(() =>
	form.channel === "slack_webhook" ? "Slack webhook URL" : "Recipient email(s)"
)

const destinationPlaceholder = computed(() =>
	form.channel === "slack_webhook"
		? "https://hooks.slack.com/services/T.../B.../..."
		: "soc@example.com, ir@example.com"
)

// Light-touch validation. Backend re-validates everything; the form
// rules just keep obvious typos out of the round trip.
const rules: FormRules = {
	name: { required: true, message: "Name is required", trigger: ["input", "blur"] },
	trigger: { required: true, message: "Pick a trigger", trigger: ["change", "blur"] },
	channel: { required: true, message: "Pick a channel", trigger: ["change", "blur"] },
	min_severity: { required: true, message: "Pick a severity threshold", trigger: ["change", "blur"] },
	destination: {
		required: true,
		validator: (_rule, value: string) => {
			if (!value || !value.trim()) {
				return new Error("Destination is required")
			}
			if (form.channel === "slack_webhook") {
				if (!value.startsWith("https://hooks.slack.com/")) {
					return new Error("Must be a Slack incoming webhook URL")
				}
			} else if (form.channel === "smtp_email") {
				const recipients = value.split(",").map(s => s.trim()).filter(Boolean)
				if (!recipients.length) return new Error("At least one email required")
				const bad = recipients.find(r => !r.includes("@"))
				if (bad) return new Error(`Invalid email: ${bad}`)
			}
			return true
		},
		trigger: ["input", "blur"]
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
</script>
