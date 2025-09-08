<template>
	<div class="invoke-action-form">
		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<!-- Action Information -->
				<div class="bg-gray-50 p-4 rounded-lg">
					<h4 class="font-semibold mb-2">Action: {{ action.copilot_action_name }}</h4>
					<p class="text-sm text-gray-600 mb-2">{{ action.description }}</p>
					<Badge :color="getTechnologyColor(action.technology)">
						<template #iconLeft><Icon :name="getTechnologyIcon(action.technology)" :size="14" /></template>
						<template #value>{{ action.technology }}</template>
					</Badge>
				</div>

				<!-- Target Agents Selection -->
				<div class="flex flex-col gap-2">
					<label class="font-semibold">Target Agents *</label>
					<n-select
						v-model:value="form.hostnames"
						:options="agentOptions"
						multiple
						filterable
						placeholder="Select target agents..."
						:loading="loadingAgents"
						clearable
					/>
					<p class="text-xs text-gray-500">Select one or more agents to run this action on</p>
				</div>

				<!-- Parameters Form -->
				<div v-if="action.script_parameters.length > 0" class="flex flex-col gap-4">
					<h4 class="font-semibold">Parameters</h4>

					<!-- Required Parameters -->
					<div v-for="param in requiredParameters" :key="param.name" class="flex flex-col gap-2">
						<label class="font-medium">
							{{ param.name }} *
							<span v-if="param.description" class="text-sm font-normal text-gray-500">
								- {{ param.description }}
							</span>
						</label>
						<component
							:is="getInputComponent(param.type)"
							v-model:value="form.parameters[param.name]"
							:placeholder="getPlaceholder(param)"
							:options="param.enum?.map(e => ({ label: e, value: e }))"
							clearable
						/>
					</div>

					<!-- Optional Parameters -->
					<div v-if="optionalParameters.length > 0">
						<n-divider>Optional Parameters</n-divider>
						<div v-for="param in optionalParameters" :key="param.name" class="flex flex-col gap-2">
							<label class="font-medium">
								{{ param.name }}
								<span v-if="param.description" class="text-sm font-normal text-gray-500">
									- {{ param.description }}
								</span>
							</label>
							<component
								:is="getInputComponent(param.type)"
								v-model:value="form.parameters[param.name]"
								:placeholder="getPlaceholder(param)"
								:options="param.enum?.map(e => ({ label: e, value: e }))"
								clearable
							/>
						</div>
					</div>
				</div>

				<!-- Action Buttons -->
				<div class="flex justify-end gap-2 pt-4 border-t">
					<n-button @click="$emit('close')">Cancel</n-button>
					<n-button
						type="primary"
						:loading="loading"
						:disabled="!isFormValid"
						@click="handleSubmit"
					>
						<template #icon>
							<Icon :name="PlayIcon"></Icon>
						</template>
						Invoke Action
					</n-button>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ActiveResponseItem, InvokeCopilotActionRequest, ScriptParameter } from "@/types/copilotAction.d"
import { NButton, NDivider, NInput, NInputNumber, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
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
const PlayIcon = "carbon:play"

const agentOptions = ref<{ label: string; value: string }[]>([])

const form = ref<{
	hostnames: string[]
	parameters: Record<string, any>
}>({
	hostnames: [],
	parameters: {}
})

// Separate required and optional parameters
const requiredParameters = computed(() => action.script_parameters.filter(p => p.required))
const optionalParameters = computed(() => action.script_parameters.filter(p => !p.required))

const isFormValid = computed(() => {
	if (form.value.hostnames.length === 0) return false

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
			hostnames: form.value.hostnames,
			parameters: {
				RepoURL: action.repo_url,
				ScriptName: action.script_name || action.copilot_action_name,
				...form.value.parameters
			}
		}

		const response = await Api.copilotAction.invokeAction(payload)

		if (response.data.success) {
			message.success(`Action invoked successfully on ${form.value.hostnames.length} agent(s)`)
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
</style>
