<template>
	<div class="flex flex-col gap-4">
		<div>
			<n-form :model="formValue" size="small" label-placement="left" label-width="auto">
				<!-- Index Pattern (pre-filled) -->
				<n-form-item label="Index Pattern" required>
					<n-input
						v-model:value="formValue.index_pattern"
						placeholder="e.g., wazuh-alerts-*"
						clearable
						:disabled="executing"
					/>
				</n-form-item>

				<!-- Result Size -->
				<n-form-item label="Size">
					<n-input-number
						v-model:value="formValue.size"
						:min="1"
						:max="1000"
						class="w-full"
						clearable
						:disabled="executing"
					/>
				</n-form-item>

				<!-- Dynamic Parameters (pre-filled from asset context) -->
				<template v-if="ruleDetail">
					<n-form-item
						v-for="param in ruleDetail.parameters"
						:key="param.name"
						:label="param.name"
						:required="param.required"
					>
						<n-input-number
							v-if="['integer', 'int', 'long', 'number', 'numeric'].includes(param.type)"
							v-model:value="formValue.parameters[param.name] as number"
							class="w-full"
							:placeholder="param.default?.toString()"
							clearable
							:disabled="executing"
						/>
						<n-switch
							v-if="['boolean', 'bool'].includes(param.type)"
							v-model:value="formValue.parameters[param.name] as boolean"
							:disabled="executing"
						/>
						<n-input
							v-else
							v-model:value="formValue.parameters[param.name] as string"
							:placeholder="param.example?.toString() || param.default?.toString()"
							clearable
							:disabled="executing"
						/>
					</n-form-item>
				</template>
			</n-form>

			<div class="flex items-center justify-between">
				<div class="flex flex-wrap gap-2">
					<Badge v-for="mitre of selectedRule.mitre_attack_id?.slice(0, 3)" :key="mitre" size="small">
						<template #value>{{ mitre }}</template>
					</Badge>
				</div>
				<n-button type="primary" :loading="executing" :disabled="!canExecute" @click="executeSearch">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Execute Search
				</n-button>
			</div>
		</div>

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
</template>

<script setup lang="ts">
import type { ExecuteSearchResponse, RuleDetail, RuleSummary } from "@/types/copilotSearches.d"
import type { AlertAsset } from "@/types/incidentManagement/alerts.d"
import {
	NButton,
	NCard,
	NCollapse,
	NCollapseItem,
	NCollapseTransition,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NScrollbar,
	NSwitch,
	useMessage
} from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	selectedRule: RuleSummary
	asset?: AlertAsset
}>()

const message = useMessage()
const PlayIcon = "carbon:play"

const loadingRuleDetail = ref(false)
const executing = ref(false)
const ruleDetail = ref<RuleDetail | null>(null)
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

const canExecute = computed(() => {
	if (!formValue.value.index_pattern) return false
	if (!ruleDetail.value) return false

	for (const param of ruleDetail.value.parameters || []) {
		if (param.required) {
			const value = formValue.value.parameters[param.name]
			if (value === undefined || value === null || value === "") {
				return false
			}
		}
	}

	return true
})

watch(
	() => props.selectedRule,
	async rule => {
		if (!rule) {
			ruleDetail.value = null
			searchResults.value = null
			return
		}

		searchResults.value = null
		loadingRuleDetail.value = true
		try {
			const res = await Api.copilotSearches.getRuleById(rule.id)
			if (res.data.success) {
				ruleDetail.value = res.data.rule
				prefillParameters()
			}
		} catch (err: any) {
			message.error(err.response?.data?.message || "Failed to load rule details")
		} finally {
			loadingRuleDetail.value = false
		}
	},
	{ immediate: true }
)

function prefillParameters() {
	if (!ruleDetail.value) return

	formValue.value.parameters = {}

	for (const param of ruleDetail.value.parameters || []) {
		const paramNameLower = param.name.toLowerCase()

		if (paramNameLower.includes("agent") && paramNameLower.includes("name")) {
			formValue.value.parameters[param.name] = props.asset?.asset_name || ""
		} else if (paramNameLower.includes("agent") && paramNameLower.includes("id")) {
			formValue.value.parameters[param.name] = props.asset?.agent_id || ""
		} else if (paramNameLower.includes("customer") || paramNameLower.includes("label")) {
			formValue.value.parameters[param.name] = param.default?.toString() || ""
		} else if (param.default !== undefined && param.default !== null) {
			formValue.value.parameters[param.name] = param.default
		} else {
			formValue.value.parameters[param.name] = ""
		}
	}

	if (props.asset?.index_name) {
		formValue.value.index_pattern = props.asset.index_name
	}
}

async function executeSearch() {
	if (!props.selectedRule || !ruleDetail.value) return

	executing.value = true
	searchResults.value = null

	try {
		const res = await Api.copilotSearches.executeSearch({
			rule_id: props.selectedRule.id,
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
</script>
