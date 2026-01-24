<template>
	<n-form ref="formRef" :model="formValue" :rules="rules" label-placement="left" label-width="auto">
		<!-- Technology Info Alert -->
		<n-alert v-if="action?.technology" type="info" class="mb-4" size="small">
			<template #header>
				<div class="flex items-center gap-2">
					<TechnologyIcon :technology="action.technology" :size="16" />
					<span>{{ action.technology }} Action</span>
				</div>
			</template>
			Only showing agents compatible with {{ action.technology }} technology
			<template v-if="incompatibleAgentCount > 0">
				({{ incompatibleAgentCount }} incompatible agent{{ incompatibleAgentCount !== 1 ? 's' : '' }} hidden)
			</template>
		</n-alert>

		<n-form-item label="Target Agents" path="agent_names" required>
			<div class="flex flex-col gap-2 w-full">
				<n-select
					v-model:value="formValue.agent_names"
					:options="filteredAgentOptions"
					:loading="loadingAgents"
					multiple
					filterable
					placeholder="Select target agents"
					:max-tag-count="3"
				>
					<template #empty>
						<n-empty description="No compatible agents found" />
					</template>
				</n-select>
				<div class="flex gap-2 justify-end">
					<n-button
						secondary
						type="primary"
						size="small"
						:disabled="loadingAgents || filteredAgentOptions.length === 0"
						@click="selectAllAgents"
					>
						<template #icon>
							<Icon name="carbon:checkbox-checked-filled" />
						</template>
						Select All
					</n-button>
					<n-button
						v-if="formValue.agent_names.length > 0"
						secondary
						size="small"
						@click="clearAllAgents"
					>
						<template #icon>
							<Icon name="carbon:close" />
						</template>
						Clear
					</n-button>
				</div>
			</div>
		</n-form-item>

		<!-- Parameters Section -->
		<div v-if="action?.script_parameters?.length" class="mb-4">
			<n-divider>Parameters</n-divider>
			<div v-for="param in action.script_parameters" :key="param.name" class="mb-3">
				<n-form-item
					:label="param.name"
					:path="`parameters.${param.name}`"
					:required="param.required"
				>
					<template #label>
						<div class="flex items-center gap-2">
							<span>{{ param.name }}</span>
							<n-tag v-if="param.type" size="tiny" :bordered="false">
								{{ param.type }}
							</n-tag>
						</div>
					</template>

					<!-- Boolean Parameter -->
					<n-switch
						v-if="param.type === 'boolean'"
						v-model:value="formValue.parameters[param.name]"
					/>

					<!-- Integer Parameter -->
					<n-input-number
						v-else-if="param.type === 'integer'"
						v-model:value="formValue.parameters[param.name]"
						:placeholder="param.default?.toString() || 'Enter value...'"
						class="w-full"
					/>

					<!-- String with Enum (Select) -->
					<n-select
						v-else-if="param.enum?.length"
						v-model:value="formValue.parameters[param.name]"
						:options="param.enum.map(v => ({ label: v, value: v }))"
						:placeholder="param.default?.toString() || 'Select value...'"
					/>

					<!-- String Parameter -->
					<n-input
						v-else
						v-model:value="formValue.parameters[param.name]"
						:placeholder="param.default?.toString() || 'Enter value...'"
						clearable
					/>

					<template v-if="param.description" #feedback>
						<span class="text-xs text-gray-500">{{ param.description }}</span>
					</template>
				</n-form-item>
			</div>
		</div>

		<div class="flex justify-end gap-2">
			<n-button @click="emit('close')">Cancel</n-button>
			<n-button
				type="primary"
				:loading="loading"
				:disabled="!isFormValid"
				@click="handleInvoke"
			>
				<template #icon>
					<Icon :name="PlayIcon" />
				</template>
				Invoke Action
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { Agent } from "@/types/agents.d"
import type { CopilotAction } from "@/types/copilotAction.d"
import {
    NAlert,
    NButton,
    NDivider,
    NEmpty,
    NForm,
    NFormItem,
    NInput,
    NInputNumber,
    NSelect,
    NSwitch,
    NTag,
    useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import TechnologyIcon from "./TechnologyIcon.vue"

const { action } = defineProps<{
    action: CopilotAction
}>()

const emit = defineEmits<{
    (e: "success"): void
    (e: "close"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const loadingAgents = ref(false)
const agents = ref<Agent[]>([])
const PlayIcon = "carbon:play"

const formValue = ref<{
    agent_names: string[]
    parameters: Record<string, string | number | boolean>
}>({
    agent_names: [],
    parameters: {}
})

// Initialize default parameter values
onBeforeMount(() => {
    if (action?.script_parameters?.length) {
        action.script_parameters.forEach(param => {
            if (param.default !== undefined && param.default !== null) {
                formValue.value.parameters[param.name] = param.default
            }
        })
    }
    getAgents()
})

// Helper function to determine if agent OS is compatible with technology
function isAgentCompatible(agent: Agent, technology: string): boolean {
    const agentOS = agent.os?.toLowerCase() || ''
    const tech = technology.toLowerCase()

    switch (tech) {
        case 'linux':
            return agentOS.includes('linux') ||
                   agentOS.includes('ubuntu') ||
                   agentOS.includes('debian') ||
                   agentOS.includes('centos') ||
                   agentOS.includes('red hat') ||
                   agentOS.includes('fedora') ||
                   agentOS.includes('suse')

        case 'windows':
            return agentOS.includes('windows')

        case 'macos':
        case 'darwin':
            return agentOS.includes('darwin') || agentOS.includes('macos')

        // For other technologies or if no specific filtering is needed
        default:
            return true
    }
}

// Filtered agent options based on technology
const filteredAgentOptions = computed(() => {
    if (!action?.technology) {
        return agents.value.map(a => ({
            label: `${a.hostname} (${a.os})`,
            value: a.hostname
        }))
    }

    return agents.value
        .filter(agent => isAgentCompatible(agent, action.technology))
        .map(a => ({
            label: `${a.hostname} (${a.os})`,
            value: a.hostname
        }))
})

// Count of incompatible agents (for display purposes)
const incompatibleAgentCount = computed(() => {
    if (!action?.technology) return 0

    return agents.value.filter(agent => !isAgentCompatible(agent, action.technology)).length
})

// Select all filtered agents
function selectAllAgents() {
    formValue.value.agent_names = filteredAgentOptions.value.map(option => option.value)
    message.success(`Selected ${formValue.value.agent_names.length} agent${formValue.value.agent_names.length !== 1 ? 's' : ''}`)
}

// Clear all selected agents
function clearAllAgents() {
    formValue.value.agent_names = []
    message.info('Cleared all agents')
}

const rules: FormRules = {
    agent_names: {
        type: 'array',
        required: true,
        message: 'Please select at least one agent',
        trigger: ['blur', 'change']
    }
}

// Add dynamic rules for required parameters
if (action?.script_parameters?.length) {
    action.script_parameters.forEach(param => {
        if (param.required) {
            rules[`parameters.${param.name}`] = {
                required: true,
                message: `${param.name} is required`,
                trigger: ['blur', 'change']
            }
        }
    })
}

const isFormValid = computed(() => {
    if (!formValue.value.agent_names.length) return false

    // Check required parameters
    if (action?.script_parameters?.length) {
        for (const param of action.script_parameters) {
            if (param.required) {
                const value = formValue.value.parameters[param.name]
                if (value === undefined || value === null || value === '') {
                    return false
                }
            }
        }
    }

    return true
})

async function getAgents() {
    loadingAgents.value = true
    try {
        const res = await Api.agents.getAgents()
        if (res.data.success) {
            agents.value = res.data.agents || []
        } else {
            message.error(res.data?.message || "Failed to load agents")
        }
    } catch (err: any) {
        message.error(err.response?.data?.message || "Failed to load agents")
    } finally {
        loadingAgents.value = false
    }
}

async function handleInvoke() {
    if (!formRef.value) return

    try {
        await formRef.value.validate()
    } catch {
        return
    }

    loading.value = true

    // Filter out undefined/null parameters
    const cleanedParameters: Record<string, string | number> = {}
    Object.entries(formValue.value.parameters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            cleanedParameters[key] = typeof value === 'boolean' ? (value ? 'true' : 'false') : value
        }
    })

    try {
        const res = await Api.copilotAction.invokeAction({
            copilot_action_name: action.copilot_action_name,
            agent_names: formValue.value.agent_names,
            parameters: cleanedParameters
        })

        if (res.data.success) {
            message.success(res.data?.message || "Action invoked successfully")
            emit('success')
        } else {
            message.warning(res.data?.message || "Failed to invoke action")
        }
    } catch (err: any) {
        message.error(err.response?.data?.message || "Failed to invoke action")
    } finally {
        loading.value = false
    }
}
</script>
