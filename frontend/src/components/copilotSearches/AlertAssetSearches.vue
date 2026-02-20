<template>
    <div class="flex flex-col gap-4">
        <!-- Search Filters -->
        <div class="flex flex-wrap items-center gap-2">
            <n-select
                v-model:value="selectedPlatform"
                :options="platformOptions"
                size="small"
                placeholder="Platform"
                class="max-w-30"
                :consistent-menu-width="false"
            />

            <n-input
                v-model:value="searchQuery"
                size="small"
                placeholder="Search rules..."
                class="max-w-60"
                clearable
            >
                <template #prefix>
                    <Icon :name="SearchIcon" />
                </template>
            </n-input>

            <n-button size="small" :loading="loadingRules" @click="loadRules">
                <template #icon>
                    <Icon :name="RefreshIcon" />
                </template>
            </n-button>
        </div>

        <!-- Rules List -->
        <n-spin :show="loadingRules">
            <div v-if="filteredRules.length" class="flex max-h-60 flex-col gap-2 overflow-y-auto">
                <n-card
                    v-for="rule in filteredRules"
                    :key="rule.id"
                    size="small"
                    hoverable
                    class="cursor-pointer"
                    :class="{ 'border-primary': selectedRule?.id === rule.id }"
                    @click="selectRule(rule)"
                >
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex flex-col gap-1">
                            <span class="font-medium">{{ rule.name }}</span>
                            <span class="line-clamp-2 text-xs opacity-70">{{ rule.description }}</span>
                        </div>
                        <div class="flex shrink-0 items-center gap-2">
                            <PlatformBadge :platform="rule.platform" />
                            <SeverityBadge :severity="rule.severity" />
                        </div>
                    </div>
                </n-card>
            </div>

            <n-empty v-else-if="!loadingRules" description="No rules found" class="h-32" />
        </n-spin>

        <!-- Selected Rule Execution -->
        <template v-if="selectedRule">
            <n-divider class="my-2!" />

            <div class="rounded-lg border border-dashed p-4">
                <div class="mb-4 flex items-center justify-between">
                    <div class="flex flex-col gap-1">
                        <span class="font-semibold">{{ selectedRule.name }}</span>
                        <div class="flex flex-wrap gap-2">
                            <Badge v-for="mitre of selectedRule.mitre_attack_id?.slice(0, 3)" :key="mitre" size="small">
                                <template #value>{{ mitre }}</template>
                            </Badge>
                        </div>
                    </div>
                    <n-button size="small" quaternary @click="selectedRule = null">
                        <template #icon>
                            <Icon :name="CloseIcon" />
                        </template>
                    </n-button>
                </div>

                <n-form ref="formRef" :model="formValue" size="small" label-placement="left" label-width="auto">
                    <!-- Index Pattern (pre-filled) -->
                    <n-form-item label="Index Pattern" required>
                        <n-input v-model:value="formValue.index_pattern" placeholder="e.g., wazuh-alerts-*" />
                    </n-form-item>

                    <!-- Result Size -->
                    <n-form-item label="Size">
                        <n-input-number v-model:value="formValue.size" :min="1" :max="1000" class="w-full" />
                    </n-form-item>

                    <!-- Dynamic Parameters (pre-filled from asset context) -->
                    <n-form-item v-if="ruleDetail" v-for="param in ruleDetail.parameters" :key="param.name" :label="param.name">
                        <template #label>
                            <div class="flex items-center gap-1">
                                <span>{{ param.name }}</span>
                                <n-tag v-if="param.required" size="tiny" type="error" :bordered="false">required</n-tag>
                            </div>
                        </template>
                        <n-input
                            v-if="param.type !== 'integer'"
                            v-model:value="formValue.parameters[param.name] as string"
                            :placeholder="param.example?.toString() || param.default?.toString()"
                        />
                        <n-input-number
                            v-else
                            v-model:value="formValue.parameters[param.name] as number"
                            class="w-full"
                        />
                    </n-form-item>
                </n-form>

                <div class="flex justify-end">
                    <n-button type="primary" :loading="executing" :disabled="!canExecute" @click="executeSearch">
                        <template #icon>
                            <Icon :name="PlayIcon" />
                        </template>
                        Execute Search
                    </n-button>
                </div>
            </div>
        </template>

        <!-- Search Results -->
        <template v-if="searchResults">
            <n-divider class="my-2!" />

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

            <n-collapse v-if="searchResults.hits.length" :default-expanded-names="['results']">
                <n-collapse-item title="Results" name="results">
                    <div class="flex max-h-64 flex-col gap-2 overflow-y-auto">
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

            <n-empty v-else description="No results found" class="py-4" />
        </template>
    </div>
</template>

<script setup lang="ts">
import type { AlertAsset } from "@/types/incidentManagement/alerts.d"
import type {
    ExecuteSearchResponse,
    PlatformFilter,
    RuleDetail,
    RuleSummary
} from "@/types/copilotSearches.d"
import { watchDebounced } from "@vueuse/core"
import {
    NButton,
    NCard,
    NCode,
    NCollapse,
    NCollapseItem,
    NDivider,
    NEmpty,
    NForm,
    NFormItem,
    NInput,
    NInputNumber,
    NSelect,
    NSpin,
    NTag,
    useMessage
} from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import PlatformBadge from "./PlatformBadge.vue"
import SeverityBadge from "./SeverityBadge.vue"

const { asset } = defineProps<{
    asset: AlertAsset
}>()

const message = useMessage()
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:refresh"
const PlayIcon = "carbon:play"
const CloseIcon = "carbon:close"

// State
const loadingRules = ref(false)
const loadingRuleDetail = ref(false)
const executing = ref(false)
const rules = ref<RuleSummary[]>([])
const selectedRule = ref<RuleSummary | null>(null)
const ruleDetail = ref<RuleDetail | null>(null)
const searchResults = ref<ExecuteSearchResponse | null>(null)

// Filters
const selectedPlatform = ref<PlatformFilter>("all")
const searchQuery = ref<string | null>(null)

const platformOptions = [
    { label: "All", value: "all" },
    { label: "Linux", value: "linux" },
    { label: "Windows", value: "windows" }
]

// Form
const formRef = ref()
const formValue = ref<{
    index_pattern: string
    size: number
    parameters: Record<string, string | number | boolean>
}>({
    index_pattern: asset.index_name || "wazuh-alerts-*",
    size: 20,
    parameters: {}
})

// Computed
const filteredRules = computed(() => {
    let result = rules.value

    if (selectedPlatform.value !== "all") {
        result = result.filter(r => r.platform === selectedPlatform.value)
    }

    if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        result = result.filter(
            r =>
                r.name.toLowerCase().includes(query) ||
                r.description.toLowerCase().includes(query)
        )
    }

    return result
})

const canExecute = computed(() => {
    if (!formValue.value.index_pattern) return false
    if (!ruleDetail.value) return false

    // Check required parameters
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

// Methods
async function loadRules() {
    loadingRules.value = true
    try {
        const res = await Api.copilotSearches.getRules({ limit: 100 })
        if (res.data.success) {
            rules.value = res.data.rules
        }
    } catch (err: any) {
        message.error(err.response?.data?.message || "Failed to load rules")
    } finally {
        loadingRules.value = false
    }
}

async function selectRule(rule: RuleSummary) {
    selectedRule.value = rule
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
}

function prefillParameters() {
    if (!ruleDetail.value) return

    // Reset parameters
    formValue.value.parameters = {}

    // Pre-fill with defaults and asset context
    for (const param of ruleDetail.value.parameters || []) {
        // Check for common parameter names and pre-fill from asset
        const paramNameLower = param.name.toLowerCase()

        if (paramNameLower.includes("agent") && paramNameLower.includes("name")) {
            formValue.value.parameters[param.name] = asset.asset_name || ""
        } else if (paramNameLower.includes("agent") && paramNameLower.includes("id")) {
            formValue.value.parameters[param.name] = asset.agent_id || ""
        } else if (paramNameLower.includes("customer") || paramNameLower.includes("label")) {
            // Try to extract customer code if available
            formValue.value.parameters[param.name] = param.default?.toString() || ""
        } else if (param.default !== undefined && param.default !== null) {
            formValue.value.parameters[param.name] = param.default
        } else {
            formValue.value.parameters[param.name] = ""
        }
    }

    // Pre-fill index pattern from asset
    if (asset.index_name) {
        formValue.value.index_pattern = asset.index_name
    }
}

async function executeSearch() {
    if (!selectedRule.value || !ruleDetail.value) return

    executing.value = true
    searchResults.value = null

    try {
        const res = await Api.copilotSearches.executeSearch({
            rule_id: selectedRule.value.id,
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

// Lifecycle
onMounted(() => {
    loadRules()
})

// Watch for platform changes to reload
watch(selectedPlatform, () => {
    selectedRule.value = null
    ruleDetail.value = null
    searchResults.value = null
})
</script>
