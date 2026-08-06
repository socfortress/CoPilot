<template>
	<n-form ref="formRef" :model="form" :rules class="flex flex-col gap-1">
		<div class="flex flex-wrap gap-4">
			<n-form-item label="Name" path="name" class="grow" :show-feedback="!!fieldErrors.name">
				<n-input v-model:value="form.name" placeholder="e.g. Alert — concise" />
			</n-form-item>

			<n-form-item label="Format" path="format" :show-feedback="false" class="min-w-40">
				<n-select v-model:value="form.format" :options="formatOptions" />
			</n-form-item>
		</div>

		<div class="text-secondary mb-3 text-xs">
			<template v-if="isTempPassword && form.format === 'json'">
				A JSON template cannot be sent as an email — pick HTML or plain text, or this template won't be
				offered when sending.
			</template>
			<template v-else-if="isTempPassword && form.format === 'html'">
				Sent as HTML with a plain-text part generated from it automatically, so a text-only client still shows
				the password. Values are escaped automatically.
			</template>
			<template v-else-if="form.format === 'html'">
				Only
				<strong>email</strong>
				renders HTML — a chat card would show the markup — so this template can only be attached to email
				routes. Values are escaped automatically.
			</template>
			<template v-else-if="form.format === 'json'">
				Sent as a raw JSON body. Use the
				<code>| tojson</code>
				filter on any value you interpolate, or the result won't parse.
			</template>
			<template v-else>Plain text with light markdown. Renders as-is in chat, email and a Teams card.</template>
		</div>

		<n-form-item label="Description (optional)" :show-feedback="false">
			<n-input v-model:value="form.description" placeholder="What this template is for" />
		</n-form-item>

		<div class="mt-4 flex flex-wrap gap-4">
			<n-form-item label="Trigger" :show-feedback="false" class="grow">
				<n-select v-model:value="form.trigger" :options="triggerOptions" clearable />
			</n-form-item>

			<n-form-item label="Customer" :show-feedback="false" class="grow">
				<n-select
					v-model:value="form.customer_code"
					:options="customerOptions"
					:loading="loadingCustomers"
					clearable
					filterable
					placeholder="Shared with all customers"
				/>
			</n-form-item>
		</div>

		<!--
			The temp-password trigger is not a route trigger — nothing dispatches
			it — so the generic "attached to a route" explanation is wrong for it
			and would leave an operator waiting for an email that only ever goes
			out when an admin presses Send.
		-->
		<div v-if="isTempPassword" class="text-secondary mb-4 text-xs">
			This is the email an admin sends from
			<strong>Customers → Security → Email temp password</strong>
			. It is not a notification route and fires only on that action. Set
			<strong>Customer</strong>
			to give one customer their own wording or language; leave it empty for the shared default. The most
			specific one wins, and the admin can still override it for a single send.
		</div>
		<div v-else class="text-secondary mb-4 text-xs">
			Leaving
			<strong>Trigger</strong>
			empty makes this usable anywhere. Setting it stops the template being attached to a route whose event never
			carries the variables it references. Leaving
			<strong>Customer</strong>
			empty shares it with every customer.
		</div>

		<n-form-item label="Subject (optional)" :show-feedback="false">
			<n-input v-model:value="form.subject_template" :placeholder="subjectPlaceholder" />
		</n-form-item>
		<div class="text-secondary mb-4 text-xs">
			Used as the email subject and the Teams card title. Channels without a subject ignore it.
		</div>

		<n-form-item label="Body" path="body_template" :show-feedback="!!fieldErrors.body_template">
			<n-input
				v-model:value="form.body_template"
				type="textarea"
				:autosize="{ minRows: 10, maxRows: 26 }"
				placeholder="Write the message. Jinja syntax — see the variables below."
				class="font-mono text-xs!"
			/>
		</n-form-item>

		<!--
			Snippets insert at the end rather than at the cursor: a textarea
			caret position is unreliable once the field has been re-rendered,
			and appending is predictable.
		-->
		<div class="mb-4 flex flex-wrap items-center gap-2">
			<span class="text-secondary text-xs">Insert:</span>
			<n-button
				v-for="snippet of snippets"
				:key="snippet.label"
				size="tiny"
				secondary
				@click="append(snippet.source)"
			>
				{{ snippet.label }}
			</n-button>
		</div>

		<n-collapse class="mb-4">
			<n-collapse-item title="Available variables" name="vars">
				<div class="text-secondary mb-2 text-xs">
					For
					<strong>{{ form.trigger ? triggerLabel(form.trigger) : "any trigger" }}</strong>
					. Wrap in
					<code>{{ mustache }}</code>
					to output a value.
				</div>
				<n-table size="small" :bordered="false" :single-line="false">
					<tbody>
						<tr v-for="variable of variables" :key="variable.name">
							<td class="w-48 align-top">
								<code class="text-xs">{{ variable.name }}</code>
							</td>
							<td class="text-secondary align-top text-xs">
								{{ variable.description }}
								<template v-if="variable.example">
									<br />
									<span class="opacity-70">e.g. {{ variable.example }}</span>
								</template>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-collapse-item>
		</n-collapse>

		<div class="mb-2 flex items-center justify-between gap-4">
			<h4 class="m-0">Preview</h4>
			<n-button size="small" secondary :loading="previewing" :disabled="!form.body_template" @click="loadPreview">
				<template #icon>
					<Icon :name="RefreshIcon" :size="14" />
				</template>
				Refresh
			</n-button>
		</div>

		<!--
			Rendered against a sample event, not this customer's real data — the
			editor must work before any matching alert exists.
		-->
		<n-alert v-if="preview?.error" type="warning" :bordered="false" class="mb-4">
			{{ preview.error }}
		</n-alert>
		<div v-else-if="preview" class="mb-4 flex flex-col gap-2">
			<div v-if="preview.subject" class="text-xs">
				<span class="text-secondary uppercase">Subject</span>
				<div class="font-mono">{{ preview.subject }}</div>
			</div>
			<!--
				A sandboxed iframe, not v-html. The body is operator-authored and
				renders in an admin's browser, so v-html would let a template
				author run script in the previewer's session. `sandbox` with no
				allow-* tokens blocks scripts, forms and navigation while still
				showing the real layout — which is also a truer preview, since
				an email client won't run scripts either.
			-->
			<iframe
				v-if="form.format === 'html'"
				:srcdoc="preview.body"
				sandbox=""
				title="HTML preview"
				class="h-80 w-full rounded border bg-white"
			/>
			<n-input
				v-else
				:value="preview.body"
				type="textarea"
				readonly
				:autosize="{ minRows: 4, maxRows: 20 }"
				class="font-mono text-xs!"
			/>
		</div>
		<div v-else class="text-secondary mb-4 text-xs">
			Renders against a sample event, so you can write a template before any matching alert exists.
		</div>

		<n-alert v-if="submitError" type="error" :bordered="false" class="mb-2">{{ submitError }}</n-alert>

		<div class="flex flex-wrap items-center justify-end gap-2">
			<n-button @click="$emit('close')">Cancel</n-button>
			<n-button type="primary" :loading="submitting" @click="submit">
				{{ editing ? "Save changes" : "Create template" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type {
	NotificationTemplate,
	NotificationTemplateFormat,
	NotificationTemplatePayload,
	NotificationTrigger,
	TemplatePreviewResult
} from "@/types/notifications"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NTable,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, reactive, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { snippetsForTrigger, variablesForTrigger } from "./templateVariables"

// The editor for a named, reusable template.
//
// The preview is the load-bearing part: it renders the UNSAVED source against a
// sample event, which is what stops "it looked right in the editor" from
// diverging from what actually goes out. It also renders errors inline rather
// than as a failed request, because a half-written template is expected to be
// broken and clearing the form on every keystroke-in-progress would be hostile.

const props = defineProps<{
	editingTemplate?: NotificationTemplate | null
}>()

const emit = defineEmits<{
	(e: "submitted", template: NotificationTemplate): void
	(e: "close"): void
}>()

const RefreshIcon = "carbon:renew"
// Shown literally in the help text. A constant because Vue can't parse nested
// {{ }} inside an interpolation — same reason the route form holds `reportToken`.
const mustache = "{{ }}"

const message = useMessage()
const formRef = ref<FormInst | null>(null)

// Keyed on the id, not the object: a Duplicate arrives as a populated template
// with id 0, and must CREATE. Branching on the object being present would make
// it overwrite template 0.
const editing = computed(() => !!props.editingTemplate?.id)

const form = reactive<NotificationTemplatePayload>({
	name: props.editingTemplate?.name ?? "",
	description: props.editingTemplate?.description ?? "",
	trigger: props.editingTemplate?.trigger ?? null,
	format: props.editingTemplate?.format ?? ("text" as NotificationTemplateFormat),
	subject_template: props.editingTemplate?.subject_template ?? "",
	body_template: props.editingTemplate?.body_template ?? "",
	customer_code: props.editingTemplate?.customer_code ?? null
})

const fieldErrors = reactive<Partial<Record<"name" | "body_template", string>>>({})
const submitError = ref<string | null>(null)
const submitting = ref(false)
const previewing = ref(false)
const preview = ref<TemplatePreviewResult | null>(null)

const customers = ref<{ customer_code: string; customer_name: string }[]>([])
const loadingCustomers = ref(false)

const formatOptions = [
	{ label: "Plain text", value: "text" },
	{ label: "Markdown", value: "markdown" },
	{ label: "HTML (email only)", value: "html" },
	{ label: "JSON", value: "json" }
]

const TRIGGER_LABELS: Record<NotificationTrigger, string> = {
	alert_created: "Alert created",
	investigation_complete: "AI investigation complete",
	ai_report_reviewed: "AI report reviewed",
	alert_assigned: "Alert assigned",
	case_assigned: "Case assigned",
	case_task_assigned: "Case task assigned",
	temp_password_issued: "Temporary password email"
}

function triggerLabel(trigger: NotificationTrigger): string {
	return TRIGGER_LABELS[trigger] ?? trigger
}

const triggerOptions = Object.entries(TRIGGER_LABELS).map(([value, label]) => ({ label, value }))

const customerOptions = computed(() =>
	customers.value.map(c => ({ label: `${c.customer_name} (${c.customer_code})`, value: c.customer_code }))
)

const variables = computed(() => variablesForTrigger(form.trigger ?? null))
const snippets = computed(() => snippetsForTrigger(form.trigger ?? null))
const isTempPassword = computed(() => form.trigger === "temp_password_issued")

// A placeholder showing alert variables is worse than none on a password email
// — it reads as the suggested shape. Bound rather than inlined in the template
// because the mustaches would otherwise be parsed as interpolations there.
const subjectPlaceholder = computed(() =>
	isTempPassword.value
		? "Your temporary {{ customer_name or 'CoPilot' }} password"
		: "{{ severity }} alert on {{ customer_code }}"
)

const rules: FormRules = {
	name: { required: true, message: "A template needs a name", trigger: ["blur", "input"] },
	body_template: { required: true, message: "A template needs a body", trigger: ["blur", "input"] }
}

function append(source: string) {
	form.body_template = form.body_template ? `${form.body_template}\n${source}` : source
}

async function loadCustomers() {
	loadingCustomers.value = true
	try {
		const res = await Api.customers.getCustomers()
		customers.value = res.data.customers ?? []
	} catch {
		// A failed customer list only costs the scoping dropdown; the template
		// is still writable and shared-with-all is the default anyway.
		customers.value = []
	} finally {
		loadingCustomers.value = false
	}
}

async function loadPreview() {
	if (!form.body_template) return
	previewing.value = true
	try {
		const res = await Api.notifications.previewTemplate({
			body_template: form.body_template,
			subject_template: form.subject_template || null,
			format: form.format,
			trigger: form.trigger ?? undefined,
			customer_code: form.customer_code
		})
		preview.value = { body: res.data.body, subject: res.data.subject, error: res.data.error }
	} catch (err) {
		preview.value = {
			body: "",
			subject: null,
			error: getApiErrorMessage(err as ApiError) || "Could not render a preview."
		}
	} finally {
		previewing.value = false
	}
}

// Debounced rather than on every keystroke: each preview is a round trip, and a
// template mid-edit is usually invalid anyway.
let previewTimer: ReturnType<typeof setTimeout> | undefined
watch(
	() => [form.body_template, form.subject_template, form.format, form.trigger, form.customer_code],
	() => {
		clearTimeout(previewTimer)
		previewTimer = setTimeout(loadPreview, 600)
	}
)

async function submit() {
	submitError.value = null
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	submitting.value = true
	try {
		const payload: NotificationTemplatePayload = {
			name: form.name,
			description: form.description || null,
			trigger: form.trigger ?? null,
			format: form.format,
			subject_template: form.subject_template || null,
			body_template: form.body_template,
			customer_code: form.customer_code ?? null
		}

		const existingId = props.editingTemplate?.id
		const res = existingId
			? await Api.notifications.updateTemplate(existingId, payload)
			: await Api.notifications.createTemplate(payload)

		message.success(editing.value ? "Template updated" : "Template created")
		emit("submitted", res.data.template)
	} catch (err) {
		// Includes the "this change would break N routes" refusal, which names
		// the routes — worth showing in full rather than as a toast that fades.
		submitError.value = getApiErrorMessage(err as ApiError) || "Could not save the template."
	} finally {
		submitting.value = false
	}
}

onBeforeMount(() => {
	loadCustomers()
	if (form.body_template) loadPreview()
})
</script>
