<template>
	<n-spin :show="loadingRule">
		<div v-if="rule" class="flex flex-col gap-4">
			<!-- Rule Info -->
			<div class="bg-secondary-color rounded-lg p-4">
				<div class="mb-2 flex items-center gap-2">
					<PlatformBadge :platform="rule.tags?.asset_type || 'unknown'" />
					<SeverityBadge :severity="rule.response?.severity || 'medium'" />
				</div>
				<h3 class="mb-1 font-semibold">{{ rule.name }}</h3>
				<p class="text-sm opacity-70">{{ rule.description }}</p>
			</div>

			<!-- Graylog Query Preview -->
			<CardKV v-if="rule.graylog?.query">
				<template #key>Graylog Query</template>
				<template #value>
					<CodeSource :code="rule.graylog.query" lang="sql" />
				</template>
			</CardKV>

			<!-- No Graylog Query Warning -->
			<n-alert v-else type="warning" title="No Graylog Query">
				This rule does not have a Graylog query defined. Only rules with Graylog queries can be provisioned as
				Graylog alerts.
			</n-alert>

			<!-- Provision Form -->
			<n-form
				v-if="rule.graylog?.query"
				ref="formRef"
				:model="formValue"
				:rules="formRules"
				label-placement="left"
				label-width="auto"
			>
				<!-- Custom Title -->
				<n-form-item label="Alert Title" path="custom_title">
					<n-input v-model:value="formValue.custom_title" :placeholder="defaultTitle" clearable />
					<template #feedback>
						<span class="text-xs opacity-60">
							Leave empty to use the default title: "{{ defaultTitle }}"
						</span>
					</template>
				</n-form-item>

				<!-- Search Within -->
				<n-form-item label="Search Window" path="search_within_seconds">
					<n-input-number
						v-model:value="formValue.search_within_seconds"
						:min="60"
						:max="86400"
						:step="60"
						class="w-full"
					>
						<template #suffix>seconds</template>
					</n-input-number>
					<template #feedback>
						<span class="text-xs opacity-60">
							Time window to search within ({{ formatDuration(formValue.search_within_seconds) }})
						</span>
					</template>
				</n-form-item>

				<!-- Execute Every -->
				<n-form-item label="Execute Every" path="execute_every_seconds">
					<n-input-number
						v-model:value="formValue.execute_every_seconds"
						:min="60"
						:max="86400"
						:step="60"
						class="w-full"
					>
						<template #suffix>seconds</template>
					</n-input-number>
					<template #feedback>
						<span class="text-xs opacity-60">
							How often to run the search ({{ formatDuration(formValue.execute_every_seconds) }})
						</span>
					</template>
				</n-form-item>

				<!-- Priority -->
				<n-form-item label="Priority" path="priority">
					<n-select v-model:value="formValue.priority" :options="priorityOptions" class="w-full" />
				</n-form-item>

				<!-- Event Limit -->
				<n-form-item label="Event Limit" path="event_limit">
					<n-input-number v-model:value="formValue.event_limit" :min="1" :max="10000" class="w-full" />
					<template #feedback>
						<span class="text-xs opacity-60">Maximum number of events to process per execution</span>
					</template>
				</n-form-item>

				<!-- Streams (Optional) -->
				<n-form-item label="Streams" path="streams">
					<n-dynamic-tags v-model:value="formValue.streams" />
					<template #feedback>
						<span class="text-xs opacity-60">Optional: Limit search to specific Graylog stream IDs</span>
					</template>
				</n-form-item>
			</n-form>

			<!-- Actions -->
			<div class="flex justify-end gap-2">
				<n-button @click="emit('close')">Cancel</n-button>
				<n-button
					type="primary"
					:loading="provisioning"
					:disabled="!rule.graylog?.query"
					@click="handleProvision"
				>
					<template #icon>
						<Icon :name="ProvisionIcon" />
					</template>
					Provision Alert
				</n-button>
			</div>
		</div>

		<n-empty v-else-if="!loadingRule" description="Failed to load rule details" />
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ProvisionGraylogAlertRequest, RuleDetail } from "@/types/copilotSearches.d"
import {
	NAlert,
	NButton,
	NDynamicTags,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import SeverityBadge from "./SeverityBadge.vue"

const props = defineProps<{
	ruleId: string
}>()

const emit = defineEmits<{
	(e: "success"): void
	(e: "close"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loadingRule = ref(false)
const provisioning = ref(false)
const rule = ref<RuleDetail | null>(null)

const ProvisionIcon = "carbon:add-alt"

const formValue = ref<{
	custom_title: string | null
	search_within_seconds: number
	execute_every_seconds: number
	priority: 1 | 2 | 3
	event_limit: number
	streams: string[]
}>({
	custom_title: null,
	search_within_seconds: 300,
	execute_every_seconds: 300,
	priority: 2,
	event_limit: 1000,
	streams: []
})

const formRules: FormRules = {
	search_within_seconds: {
		required: true,
		type: "number",
		min: 60,
		max: 86400,
		message: "Must be between 60 and 86400 seconds",
		trigger: ["blur", "change"]
	},
	execute_every_seconds: {
		required: true,
		type: "number",
		min: 60,
		max: 86400,
		message: "Must be between 60 and 86400 seconds",
		trigger: ["blur", "change"]
	},
	event_limit: {
		required: true,
		type: "number",
		min: 1,
		max: 10000,
		message: "Must be between 1 and 10000",
		trigger: ["blur", "change"]
	}
}

const priorityOptions = [
	{ label: "Low (1)", value: 1 },
	{ label: "Normal (2)", value: 2 },
	{ label: "High (3)", value: 3 }
]

const defaultTitle = computed(() => {
	if (!rule.value) return ""
	return rule.value.name.toUpperCase().replace(/ /g, " - ")
})

function formatDuration(seconds: number): string {
	if (seconds < 60) return `${seconds} seconds`
	if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`
	if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`
	return `${Math.floor(seconds / 86400)} days`
}

function getPriorityFromSeverity(severity: string): 1 | 2 | 3 {
	switch (severity.toLowerCase()) {
		case "low":
			return 1
		case "medium":
			return 2
		case "high":
		case "critical":
			return 3
		default:
			return 2
	}
}

async function loadRule() {
	loadingRule.value = true
	try {
		const res = await Api.copilotSearches.getRuleById(props.ruleId)
		if (res.data.success) {
			rule.value = res.data.rule

			// Set default priority based on rule severity
			if (rule.value.response?.severity) {
				formValue.value.priority = getPriorityFromSeverity(rule.value.response.severity)
			}
		} else {
			message.error(res.data?.message || "Failed to load rule details")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load rule details")
	} finally {
		loadingRule.value = false
	}
}

async function handleProvision() {
	if (!formRef.value || !rule.value) return

	try {
		await formRef.value.validate()
	} catch {
		return
	}

	provisioning.value = true

	try {
		const request: ProvisionGraylogAlertRequest = {
			rule_id: props.ruleId,
			search_within_seconds: formValue.value.search_within_seconds,
			execute_every_seconds: formValue.value.execute_every_seconds,
			priority: formValue.value.priority,
			event_limit: formValue.value.event_limit
		}

		if (formValue.value.custom_title) {
			request.custom_title = formValue.value.custom_title
		}

		if (formValue.value.streams.length > 0) {
			request.streams = formValue.value.streams
		}

		const res = await Api.copilotSearches.provisionGraylogAlert(request)

		if (res.data.success) {
			message.success(`Graylog alert "${res.data.alert_title}" created successfully!`)
			emit("success")
		} else {
			message.error(res.data?.message || "Failed to provision alert")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to provision Graylog alert")
	} finally {
		provisioning.value = false
	}
}

onMounted(() => {
	loadRule()
})
</script>
