<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-6">
			<div class="text-sm leading-relaxed">{{ action.description }}</div>

			<!-- Target Agents Selection -->
			<div class="mt-4 flex flex-col gap-1">
				<n-form-item label="Target Agents" required :show-feedback="false">
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
				</n-form-item>
				<p class="px-0.5 text-sm">Select one or more agents to run this action on</p>
			</div>

			<!-- Parameters Form -->
			<CardEntity v-if="action.script_parameters.length > 0" embedded>
				<template #header>Parameters</template>

				<div class="flex flex-col gap-4">
					<n-card
						v-for="param in parameters"
						:key="param.name"
						embedded
						size="small"
						content-class="flex flex-col gap-2"
					>
						<n-form-item :required="param.required" :show-feedback="false">
							<template #label>
								<div class="flex items-center gap-2">
									<span>{{ param.name }}</span>
									<code>{{ param.type }}</code>
								</div>
							</template>
							<component
								:is="getInputComponent(param.type)"
								v-model:value="form.parameters[param.name]"
								:placeholder="getPlaceholder(param)"
								:options="param.enum?.map(e => ({ label: e, value: e }))"
								clearable
							/>
						</n-form-item>
						<p v-if="param.description" class="px-0.5 text-sm">{{ param.description }}</p>
					</n-card>
				</div>
			</CardEntity>

			<!-- Action Buttons -->
			<div class="mt-6 flex justify-end gap-3">
				<n-button size="large" @click="$emit('close')">Cancel</n-button>
				<n-button type="primary" size="large" :loading="loading" :disabled="!isFormValid" @click="handleSubmit">
					<template #icon>
						<Icon :size="18" :name="InvokeIcon" />
					</template>
					{{ loading ? "Invoking..." : "Invoke Action" }}
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ActiveResponseItem, InvokeCopilotActionRequest, ScriptParameter } from "@/types/copilotAction.d"
import _orderBy from "lodash/orderBy"
import { NButton, NCard, NFormItem, NInput, NInputNumber, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"

const { action } = defineProps<{
	action: ActiveResponseItem
}>()

const emit = defineEmits<{
	success: []
	close: []
}>()

const InvokeIcon = "solar:playback-speed-outline"
const message = useMessage()
const loading = ref(false)
const loadingAgents = ref(false)

const agentOptions = ref<{ label: string; value: string }[]>([])

const form = ref<{
	agent_names: string[]
	parameters: Record<string, string | number | boolean>
}>({
	agent_names: [],
	parameters: {}
})

// Separate required and optional parameters
const requiredParameters = computed(() => action.script_parameters.filter(p => p.required))
const parameters = computed(() => _orderBy(action.script_parameters, ["required"], ["asc"]))

const isFormValid = computed(() => {
	if (form.value.agent_names.length === 0) return false

	// Check all required parameters are filled
	for (const param of requiredParameters.value) {
		const value = form.value.parameters[param.name]
		if (value === null || value === undefined || value === "") {
			return false
		}
	}

	return true
})

function getInputComponent(type: string) {
	switch (type.toLowerCase()) {
		case "int":
		case "integer":
		case "float":
		case "number":
			return NInputNumber
		case "bool":
		case "boolean":
			return NSwitch
		case "enum":
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
			message.error("Failed to load agents")
		}
	} catch {
		message.error("Error loading agents")
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
				ScriptURL: action.repo_url,
				...form.value.parameters
			}
		}

		const response = await Api.copilotAction.invokeAction(payload)

		if (response.data.success) {
			message.success(
				`Action invoked successfully on ${form.value.agent_names.length} agent(s). Check the appropriate Grafana dashboard for results.`
			)
			emit("success")
		} else {
			message.error(response.data.message || "Failed to invoke action")
		}
	} catch (error: any) {
		// TODO: remove any
		message.error(error.response?.data?.message || "Error invoking action")
	} finally {
		loading.value = false
	}
}

// Initialize form with default values
function initializeForm() {
	const parameters: Record<string, string | number | boolean> = {}

	action.script_parameters.forEach(param => {
		if (param.default !== null && param.default !== undefined) {
			parameters[param.name] = param.default
		}
	})

	form.value.parameters = parameters
}

onBeforeMount(() => {
	loadAgents()
	initializeForm()
})
</script>

<style scoped>
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
</style>
