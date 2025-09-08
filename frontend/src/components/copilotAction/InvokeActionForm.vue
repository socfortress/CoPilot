<template>
	<div class="invoke-action-form">
		<n-spin :show="loading">
			<div class="flex flex-col gap-6">
				<!-- Action Information -->
				<div class="action-header p-4 rounded-lg border">
					<div class="flex items-start justify-between mb-3">
						<div class="flex-1">
							<h4 class="text-lg font-semibold mb-1">{{ action.copilot_action_name }}</h4>
							<p class="text-sm opacity-75">{{ action.description }}</p>
						</div>
						<Badge :color="getTechnologyColor(action.technology)" class="ml-3">
							<template #iconLeft><Icon :name="getTechnologyIcon(action.technology)" :size="14" /></template>
							<template #value>{{ action.technology }}</template>
						</Badge>
					</div>
				</div>

				<!-- Target Agents Selection -->
				<div class="form-section">
					<div class="section-header mb-3">
						<h5 class="font-semibold text-base">Target Agents</h5>
						<span class="required-indicator">*</span>
					</div>
					<n-select
						v-model:value="form.agent_names"
						:options="agentOptions"
						multiple
						filterable
						placeholder="Select target agents..."
						:loading="loadingAgents"
						clearable
						size="large"
						class="mb-2"
					/>
					<p class="helper-text">Select one or more agents to run this action on</p>
				</div>

				<!-- Parameters Form -->
				<div v-if="action.script_parameters.length > 0" class="form-section">
					<div class="section-header mb-4">
						<h5 class="font-semibold text-base">Parameters</h5>
					</div>

					<!-- Required Parameters -->
					<div v-if="requiredParameters.length > 0" class="parameter-group mb-6">
						<div class="parameter-group-header mb-4">
							<h6 class="text-sm font-medium opacity-90">Required Parameters</h6>
							<div class="parameter-group-line"></div>
						</div>
						<div class="grid grid-cols-1 gap-4">
							<div v-for="param in requiredParameters" :key="param.name" class="parameter-field">
								<div class="parameter-label mb-2">
									<label class="font-medium text-sm">
										{{ param.name }}
										<span class="required-indicator">*</span>
									</label>
									<Badge v-if="param.type" color="primary" size="small" class="ml-2">
										<template #value>{{ param.type }}</template>
									</Badge>
								</div>
								<component
									:is="getInputComponent(param.type)"
									v-model:value="form.parameters[param.name]"
									:placeholder="getPlaceholder(param)"
									:options="param.enum?.map(e => ({ label: e, value: e }))"
									clearable
									size="large"
									class="mb-1"
								/>
								<p v-if="param.description" class="helper-text">{{ param.description }}</p>
							</div>
						</div>
					</div>

					<!-- Optional Parameters -->
					<div v-if="optionalParameters.length > 0" class="parameter-group">
						<div class="parameter-group-header mb-4">
							<h6 class="text-sm font-medium opacity-90">Optional Parameters</h6>
							<div class="parameter-group-line"></div>
						</div>
						<div class="grid grid-cols-1 gap-4">
							<div v-for="param in optionalParameters" :key="param.name" class="parameter-field">
								<div class="parameter-label mb-2">
									<label class="font-medium text-sm">{{ param.name }}</label>
									<Badge v-if="param.type" color="primary" size="small" class="ml-2">
										<template #value>{{ param.type }}</template>
									</Badge>
								</div>
								<component
									:is="getInputComponent(param.type)"
									v-model:value="form.parameters[param.name]"
									:placeholder="getPlaceholder(param)"
									:options="param.enum?.map(e => ({ label: e, value: e }))"
									clearable
									size="large"
									class="mb-1"
								/>
								<p v-if="param.description" class="helper-text">{{ param.description }}</p>
							</div>
						</div>
					</div>
				</div>				<!-- Action Buttons -->
				<div class="action-buttons flex justify-end gap-3 pt-6 mt-6 border-t border-opacity-20">
					<n-button size="large" class="px-6" @click="$emit('close')">
						Cancel
					</n-button>
					<n-button
						type="primary"
						size="large"
						class="px-8"
						:loading="loading"
						:disabled="!isFormValid"
						@click="handleSubmit"
					>
						<template v-if="!loading" #icon>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</template>
						{{ loading ? 'Invoking...' : 'Invoke Action' }}
					</n-button>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem, InvokeCopilotActionRequest, ScriptParameter } from "@/types/copilotAction.d"
import { NButton, NInput, NInputNumber, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { Technology } from "@/types/copilotAction.d"

const { action } = defineProps<{
	action: ActiveResponseItem
}>()

const emit = defineEmits<{
	success: []
	close: []
}>()

const message = useMessage()
const loading = ref(false)
const loadingAgents = ref(false)

const agentOptions = ref<{ label: string; value: string }[]>([])

const form = ref<{
	agent_names: string[]
	parameters: Record<string, any>
}>({
	agent_names: [],
	parameters: {}
})

// Separate required and optional parameters
const requiredParameters = computed(() => action.script_parameters.filter(p => p.required))
const optionalParameters = computed(() => action.script_parameters.filter(p => !p.required))

const isFormValid = computed(() => {
	if (form.value.agent_names.length === 0) return false

	// Check all required parameters are filled
	for (const param of requiredParameters.value) {
		const value = form.value.parameters[param.name]
		if (value === null || value === undefined || value === '') {
			return false
		}
	}

	return true
})

function getInputComponent(type: string) {
	switch (type.toLowerCase()) {
		case 'int':
		case 'integer':
		case 'float':
		case 'number':
			return NInputNumber
		case 'bool':
		case 'boolean':
			return NSwitch
		case 'enum':
			return NSelect
		default:
			return NInput
	}
}

function getPlaceholder(param: ScriptParameter): string {
	if (param.default !== null && param.default !== undefined) {
		return `Default: ${param.default}`
	}
	return `Enter ${param.name}...`
}

function getTechnologyIcon(technology: string): string {
	const iconMap: Record<string, string> = {
		[Technology.WINDOWS]: "carbon:logo-windows",
		[Technology.LINUX]: "carbon:logo-linux",
		[Technology.MACOS]: "carbon:logo-apple",
		[Technology.WAZUH]: "carbon:security",
		[Technology.VELOCIRAPTOR]: "carbon:eagle",
		[Technology.NETWORK]: "carbon:network-3",
		[Technology.CLOUD]: "carbon:cloud"
	}
	return iconMap[technology] || "carbon:application"
}

function getTechnologyColor(technology: string): "primary" | "warning" | "success" | "danger" | undefined {
	const colorMap: Record<string, "primary" | "warning" | "success" | "danger"> = {
		[Technology.WINDOWS]: "primary",
		[Technology.LINUX]: "warning",
		[Technology.MACOS]: "success",
		[Technology.WAZUH]: "success",
		[Technology.VELOCIRAPTOR]: "primary",
		[Technology.NETWORK]: "primary",
		[Technology.CLOUD]: "success"
	}
	return colorMap[technology]
}

async function loadAgents() {
	loadingAgents.value = true
	try {
		const response = await Api.agents.getAgents()
		if (response.data.success) {
			agentOptions.value = response.data.agents.map(agent => ({
				label: `${agent.hostname} (${agent.ip_address})`,
				value: agent.hostname
			}))
		} else {
			message.error('Failed to load agents')
		}
	} catch {
		message.error('Error loading agents')
	} finally {
		loadingAgents.value = false
	}
}

async function handleSubmit() {
	if (!isFormValid.value) return

	loading.value = true
	try {
		// Prepare the payload
		const payload: InvokeCopilotActionRequest = {
			copilot_action_name: action.copilot_action_name,
			agent_names: form.value.agent_names,
			parameters: {
				RepoURL: action.repo_url,
				ScriptName: action.script_name || action.copilot_action_name,
				...form.value.parameters
			}
		}

		const response = await Api.copilotAction.invokeAction(payload)

		if (response.data.success) {
			message.success(`Action invoked successfully on ${form.value.agent_names.length} agent(s)`)
			emit('success')
		} else {
			message.error(response.data.message || 'Failed to invoke action')
		}
	} catch (error: any) {
		message.error(error.response?.data?.message || 'Error invoking action')
	} finally {
		loading.value = false
	}
}

// Initialize form with default values
function initializeForm() {
	const parameters: Record<string, any> = {}

	action.script_parameters.forEach(param => {
		if (param.default !== null && param.default !== undefined) {
			parameters[param.name] = param.default
		}
	})

	form.value.parameters = parameters
}

onMounted(() => {
	loadAgents()
	initializeForm()
})
</script>

<style scoped>
.invoke-action-form {
	max-height: 70vh;
	overflow-y: auto;
}

/* Form section styling */
.form-section {
	padding: 1rem;
	border: 1px solid var(--border-color);
	border-radius: 8px;
}

.section-header {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.required-indicator {
	color: #f56565;
	font-weight: 600;
}

/* Parameter groups */
.parameter-group-header {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.parameter-group-line {
	flex: 1;
	height: 1px;
	background: linear-gradient(to right, var(--border-color) 0%, transparent 100%);
}

.parameter-field {
	position: relative;
}

.parameter-label {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.helper-text {
	font-size: 0.875rem;
	opacity: 0.7;
	margin-top: 0.25rem;
}

/* Action header styling */
.action-header {
	border-color: var(--border-color);
}

/* Action buttons styling */
.action-buttons {
	border-color: var(--border-color);
}

/* CSS Variables for theme support */
.light-theme {
	--border-color: rgba(0, 0, 0, 0.1);
}

.dark-theme {
	--border-color: rgba(255, 255, 255, 0.1);
}

/* Default fallback */
:not(.light-theme):not(.dark-theme) {
	--border-color: rgba(0, 0, 0, 0.1);
}
</style>
