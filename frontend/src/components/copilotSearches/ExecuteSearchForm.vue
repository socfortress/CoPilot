<template>
	<n-spin :show="loadingRule">
		<div v-if="rule" class="flex flex-col gap-8">
			<RuleHeader v-if="showHeader" :rule-detail="rule" />

			<n-form
				ref="formRef"
				:model="formValue"
				:rules
				label-placement="left"
				label-width="auto"
				:disabled="executing"
			>
				<!-- Index Pattern -->
				<n-form-item label="Index Pattern" path="index_pattern" required>
					<n-input
						v-model:value="formValue.index_pattern"
						placeholder="e.g., wazuh-alerts-*"
						clearable
						:disabled="executing"
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
						clearable
						:disabled="executing"
					/>
				</n-form-item>

				<!-- Parameters Section -->
				<div v-if="rule.parameters?.length">
					<n-divider>Search Parameters</n-divider>

					<n-form-item
						v-for="param in rule.parameters"
						:key="param.name"
						:label="param.name"
						:required="param.required"
					>
						<div class="flex w-full flex-col gap-2">
							<n-input-number
								v-if="['integer', 'int', 'long', 'number', 'numeric'].includes(param.type)"
								v-model:value="formValue.parameters[param.name] as number"
								class="w-full"
								:placeholder="param.default?.toString()"
								clearable
							/>
							<n-switch
								v-if="['boolean', 'bool'].includes(param.type)"
								v-model:value="formValue.parameters[param.name] as boolean"
							/>
							<n-input
								v-else
								v-model:value="formValue.parameters[param.name] as string"
								:placeholder="param.example?.toString() || param.default?.toString()"
								clearable
							/>
							<div v-if="param.description" class="text-secondary text-xs">
								{{ param.description }}
							</div>
						</div>
					</n-form-item>
				</div>

				<div class="flex items-center justify-between">
					<div class="flex flex-wrap gap-2">
						<Badge v-for="mitre of ruleSummary?.mitre_attack_id?.slice(0, 3)" :key="mitre" size="small">
							<template #value>{{ mitre }}</template>
						</Badge>
					</div>
					<n-button type="primary" :loading="executing" :disabled="!isFormValid" @click="executeSearch">
						<template #icon>
							<Icon :name="PlayIcon" />
						</template>
						Execute Search
					</n-button>
				</div>
			</n-form>

			<!-- Search Results -->
			<n-collapse-transition :show="!!searchResults">
				<n-card v-if="searchResults" title="Search Results" size="small" content-class="flex flex-col gap-6">
					<div class="flex flex-wrap items-center gap-3">
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

					<n-collapse v-if="searchResults.hits.length">
						<n-collapse-item title="Results" name="results">
							<n-scrollbar
								class="max-h-64"
								trigger="none"
								:theme-overrides="{
									railInsetVerticalRight: `0px 0px 0px auto`
								}"
							>
								<div class="flex flex-col gap-2">
									<div
										v-for="hit in searchResults.hits"
										:key="hit.id"
										class="bg-secondary-color rounded-lg p-3"
									>
										<div class="mb-2 flex flex-wrap gap-2">
											<Badge type="splitted" size="small">
												<template #label>Index</template>
												<template #value>{{ hit.index }}</template>
											</Badge>
											<Badge type="splitted" size="small">
												<template #label>ID</template>
												<template #value>{{ hit.id }}</template>
											</Badge>
										</div>
										<CodeSource :code="hit.source" lang="json" />
									</div>
								</div>
							</n-scrollbar>
						</n-collapse-item>

						<n-collapse-item title="Query Executed" name="query">
							<CodeSource :code="searchResults.query_executed" lang="json" />
						</n-collapse-item>
					</n-collapse>
				</n-card>
				<n-empty v-else description="No results found" class="py-4" />
			</n-collapse-transition>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ExecuteSearchResponse, RuleDetail, RuleSummary } from "@/types/copilotSearches.d"
import type { AlertAsset } from "@/types/incidentManagement/alerts"
import {
	NButton,
	NCard,
	NCollapse,
	NCollapseItem,
	NCollapseTransition,
	NDivider,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NScrollbar,
	NSpin,
	NSwitch,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import RuleHeader from "./RuleHeader.vue"

const props = defineProps<{
	ruleId?: string
	ruleSummary?: RuleSummary
	ruleDetail?: RuleDetail
	asset?: AlertAsset
	showHeader?: boolean
}>()

const PlayIcon = "carbon:play"

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loadingRule = ref(false)
const executing = ref(false)
const rule = ref<RuleDetail | null>(null)
const searchResults = ref<ExecuteSearchResponse | null>(null)

const formValue = ref<{
	index_pattern: string
	size: number
	parameters: Record<string, string | number | boolean>
}>({
	index_pattern: props.asset?.index_name || "wazuh-alerts-*",
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
	if (!rule.value) return false

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

function prefillParameters() {
	// Initialize parameters with defaults
	if (rule.value?.parameters?.length) {
		rule.value.parameters.forEach(param => {
			if (param.default !== undefined && param.default !== null) {
				formValue.value.parameters[param.name] = param.default
			}
		})
	}

	// Set default size from rule if available
	if (rule.value?.search?.size) {
		formValue.value.size = rule.value.search.size as number
	}
}

async function loadRule(ruleId: string) {
	loadingRule.value = true

	try {
		const res = await Api.copilotSearches.getRuleById(ruleId)
		if (res.data.success) {
			rule.value = res.data.rule

			prefillParameters()
		} else {
			message.error(res.data?.message || "Failed to load rule details")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load rule details")
	} finally {
		loadingRule.value = false
	}
}

async function executeSearch() {
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
			rule_id: rule.value.id,
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

onBeforeMount(() => {
	if (props.ruleDetail) {
		rule.value = props.ruleDetail
		prefillParameters()
	} else if (props.ruleSummary) {
		loadRule(props.ruleSummary?.id)
	} else if (props.ruleId) {
		loadRule(props.ruleId)
	} else {
		message.error("No rule data or rule ID provided")
	}
})
</script>
