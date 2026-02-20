<template>
	<n-spin :show="loadingRule">
		<n-form v-if="rule" ref="formRef" :model="formValue" :rules="rules" label-placement="left" label-width="auto">
			<!-- Index Pattern -->
			<n-form-item label="Index Pattern" path="index_pattern" required>
				<n-input
					v-model:value="formValue.index_pattern"
					placeholder="e.g., wazuh-alerts-*"
					clearable
				/>
			</n-form-item>

			<!-- Result Size -->
			<n-form-item label="Result Size" path="size">
				<n-input-number
					v-model:value="formValue.size"
					:min="1"
					:max="10000"
					placeholder="Number of results"
					class="w-full"
				/>
			</n-form-item>

			<!-- Parameters Section -->
			<div v-if="rule.parameters?.length" class="mb-4">
				<n-divider>Search Parameters</n-divider>
				<div v-for="param in rule.parameters" :key="param.name" class="mb-3">
					<n-form-item :label="param.name" :path="`parameters.${param.name}`" :required="param.required">
						<template #label>
							<div class="flex items-center gap-2">
								<span>{{ param.name }}</span>
								<n-tag v-if="param.type" size="tiny" :bordered="false">
									{{ param.type }}
								</n-tag>
							</div>
						</template>

						<!-- DateTime Parameter -->
						<n-input
							v-if="param.type === 'datetime'"
							v-model:value="formValue.parameters[param.name] as string"
							:placeholder="param.example?.toString() || param.default?.toString() || 'e.g., now-24h'"
							clearable
						/>

						<!-- Integer Parameter -->
						<n-input-number
							v-else-if="param.type === 'integer'"
							v-model:value="formValue.parameters[param.name] as number"
							:placeholder="param.default?.toString() || 'Enter value...'"
							class="w-full"
						/>

						<!-- String Parameter -->
						<n-input
							v-else
							v-model:value="formValue.parameters[param.name] as string"
							:placeholder="param.example?.toString() || param.default?.toString() || 'Enter value...'"
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
				<n-button type="primary" :loading="executing" :disabled="!isFormValid" @click="handleExecute">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Execute Search
				</n-button>
			</div>
		</n-form>

		<!-- Search Results -->
		<div v-if="searchResults" class="mt-4">
			<n-divider>Search Results</n-divider>

			<div class="mb-4 flex flex-wrap items-center gap-4">
				<Badge color="primary" type="splitted">
					<template #label>Total Hits</template>
					<template #value>{{ searchResults.total_hits }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Returned</template>
					<template #value>{{ searchResults.returned_hits }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Time</template>
					<template #value>{{ searchResults.took_ms }}ms</template>
				</Badge>
			</div>

			<n-collapse v-if="searchResults.hits.length" :default-expanded-names="['results']">
				<n-collapse-item title="Results" name="results">
					<div class="flex max-h-96 flex-col gap-2 overflow-y-auto">
						<div
							v-for="hit in searchResults.hits"
							:key="hit.id"
							class="bg-secondary-color rounded-lg p-3"
						>
							<div class="mb-2 flex items-center gap-2 text-xs opacity-60">
								<span>Index: {{ hit.index }}</span>
								<span>|</span>
								<span>ID: {{ hit.id }}</span>
							</div>
							<n-code :code="JSON.stringify(hit.source, null, 2)" language="json" />
						</div>
					</div>
				</n-collapse-item>

				<n-collapse-item title="Query Executed" name="query">
					<n-code :code="JSON.stringify(searchResults.query_executed, null, 2)" language="json" />
				</n-collapse-item>
			</n-collapse>

			<n-empty v-else description="No results found" class="py-8" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ExecuteSearchResponse, RuleDetail } from "@/types/copilotSearches.d"
import {
	NButton,
	NCode,
	NCollapse,
	NCollapseItem,
	NDivider,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const { ruleId } = defineProps<{
	ruleId: string
}>()

const emit = defineEmits<{
	(e: "success"): void
	(e: "close"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loadingRule = ref(false)
const executing = ref(false)
const rule = ref<RuleDetail | null>(null)
const searchResults = ref<ExecuteSearchResponse | null>(null)
const PlayIcon = "carbon:play"

const formValue = ref<{
	index_pattern: string
	size: number
	parameters: Record<string, string | number | boolean>
}>({
	index_pattern: "wazuh-alerts-*",
	size: 20,
	parameters: {}
})

const rules: FormRules = {
	index_pattern: {
		required: true,
		message: "Index pattern is required",
		trigger: ["blur", "change"]
	}
}

const isFormValid = computed(() => {
	if (!formValue.value.index_pattern) return false

	// Check required parameters
	if (rule.value?.parameters?.length) {
		for (const param of rule.value.parameters) {
			if (param.required) {
				const value = formValue.value.parameters[param.name]
				if (value === undefined || value === null || value === "") {
					return false
				}
			}
		}
	}

	return true
})

async function loadRule() {
	loadingRule.value = true
	try {
		const res = await Api.copilotSearches.getRuleById(ruleId)
		if (res.data.success) {
			rule.value = res.data.rule

			// Initialize parameters with defaults
			if (rule.value.parameters?.length) {
				rule.value.parameters.forEach(param => {
					if (param.default !== undefined && param.default !== null) {
						formValue.value.parameters[param.name] = param.default
					}
				})
			}

			// Set default size from rule if available
			if (rule.value.search?.size) {
				formValue.value.size = rule.value.search.size as number
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

async function handleExecute() {
	if (!formRef.value || !rule.value) return

	try {
		await formRef.value.validate()
	} catch {
		return
	}

	executing.value = true
	searchResults.value = null

	try {
		const res = await Api.copilotSearches.executeSearch({
			rule_id: ruleId,
			index_pattern: formValue.value.index_pattern,
			parameters: formValue.value.parameters,
			size: formValue.value.size
		})

		if (res.data.success) {
			searchResults.value = res.data
			message.success(`Search completed: ${res.data.total_hits} hits found`)
		} else {
			message.warning(res.data?.message || "Search failed")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Search execution failed")
	} finally {
		executing.value = false
	}
}

onMounted(() => {
	loadRule()
})
</script>
