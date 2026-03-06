<template>
	<div class="flex flex-col gap-4">
		<!-- Search Filters -->
		<div class="flex items-center gap-2">
			<n-input v-model:value="searchQuery" size="small" placeholder="Search rules..." class="grow" clearable>
				<template #prefix>
					<Icon :name="SearchIcon" />
				</template>
			</n-input>

			<n-select
				v-model:value="selectedPlatform"
				:options="platformOptions"
				size="small"
				placeholder="All Platforms"
				class="max-w-35"
				clearable
				:consistent-menu-width="false"
			/>
		</div>

		<n-card content-class="p-0!">
			<!-- Rules List -->
			<n-spin :show="loadingRules" class="min-h-50">
				<n-scrollbar
					v-if="filteredRules.length"
					class="max-h-90 p-3!"
					trigger="none"
					:theme-overrides="{
						railInsetVerticalRight: `4px 4px 4px auto`
					}"
				>
					<div class="flex flex-col gap-3">
						<CardEntity
							v-for="rule in filteredRules"
							:key="rule.id"
							size="small"
							hoverable
							embedded
							clickable
							:highlighted="selectedRule?.id === rule.id"
							@click="selectRule(rule)"
						>
							<template #headerMain>
								<PlatformBadge :platform="rule.platform" class="text-default" />
							</template>
							<template #headerExtra>
								<SeverityBadge :severity="rule.severity" />
							</template>
							<template #mainExtra>
								<div class="flex flex-col gap-1">
									<span class="font-medium">{{ rule.name }}</span>
									<span class="line-clamp-2 text-sm opacity-70">{{ rule.description }}</span>
								</div>
							</template>
						</CardEntity>
					</div>
				</n-scrollbar>

				<n-empty v-else-if="!loadingRules" description="No rules found" class="py-20" />
			</n-spin>
		</n-card>

		<n-modal
			:show="!!selectedRule"
			:mask-closable="false"
			:title="selectedRule?.name"
			segmented
			preset="card"
			:style="{ maxWidth: 'min(550px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			@close="selectedRule = null"
		>
			<ExecuteSearchForm v-if="selectedRule" :rule-summary="selectedRule" :asset />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { PlatformFilter, RuleSummary } from "@/types/copilotSearches.d"
import type { AlertAsset } from "@/types/incidentManagement/alerts.d"
import { NCard, NEmpty, NInput, NModal, NScrollbar, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import PlatformBadge from "@/components/common/PlatformBadge.vue"
import ExecuteSearchForm from "./ExecuteSearchForm.vue"
import SeverityBadge from "./SeverityBadge.vue"

const { asset } = defineProps<{
	asset: AlertAsset
}>()

const message = useMessage()
const SearchIcon = "carbon:search"

// State
const loadingRules = ref(false)
const rules = ref<RuleSummary[]>([])
const selectedRule = ref<RuleSummary | null>(null)

// Filters
const selectedPlatform = ref<PlatformFilter | null>(null)
const searchQuery = ref<string | null>(null)

const platformOptions = [
	{ label: "Linux", value: "linux" },
	{ label: "Windows", value: "windows" }
]

// Computed
const filteredRules = computed(() => {
	let result = rules.value

	if (selectedPlatform.value) {
		result = result.filter(r => r.platform === selectedPlatform.value)
	}

	if (searchQuery.value) {
		const query = searchQuery.value.toLowerCase()
		result = result.filter(r => r.name.toLowerCase().includes(query) || r.description.toLowerCase().includes(query))
	}

	return result
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

function selectRule(rule: RuleSummary) {
	selectedRule.value = rule
}

// Lifecycle
onBeforeMount(() => {
	loadRules()
})

// Watch for platform changes to reload
watch(selectedPlatform, () => {
	selectedRule.value = null
})
</script>
