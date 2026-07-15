<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 flex-wrap items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeCopilotSearchRule())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ rule?.name || ruleId }}</span>
				<span v-if="rule?.version" class="text-secondary font-mono text-sm">v{{ rule.version }}</span>
			</div>

			<div v-if="rule" class="ml-auto flex shrink-0 items-center gap-2">
				<n-button v-if="rule.graylog?.query" secondary @click="showProvisionModal = true">
					<template #icon>
						<Icon :name="ProvisionIcon" />
					</template>
					Provision
				</n-button>
				<n-button type="primary" @click="showExecuteModal = true">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Execute
				</n-button>
			</div>
		</div>

		<n-spin v-if="ruleId" :show="loading" class="min-h-40">
			<RuleCardContent v-if="rule" :rule-data="rule" />
			<n-empty v-else-if="!loading" description="Rule not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid rule" class="h-48 justify-center" />

		<n-modal
			v-if="rule"
			v-model:show="showExecuteModal"
			preset="card"
			:style="{ maxWidth: 'min(550px, 90vw)' }"
			title="Execute Search"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<ExecuteSearchForm :rule-detail="rule" show-header @close="showExecuteModal = false" />
		</n-modal>

		<n-modal
			v-if="rule"
			v-model:show="showProvisionModal"
			preset="card"
			:style="{ maxWidth: 'min(550px, 90vw)' }"
			title="Provision Graylog Alert"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<ProvisionGraylogForm
				:rule-data="rule"
				@success="showProvisionModal = false"
				@close="showProvisionModal = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { RuleDetail } from "@/types/copilot-searches"
import { NButton, NEmpty, NModal, NSpin } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ExecuteSearchForm from "@/components/copilotSearches/ExecuteSearchForm.vue"
import ProvisionGraylogForm from "@/components/copilotSearches/ProvisionGraylogForm.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeCopilotSearchRule } = useNavigation()

const BackIcon = "carbon:arrow-left"
const PlayIcon = "carbon:play"
const ProvisionIcon = "carbon:add-alt"

const showExecuteModal = ref(false)
const showProvisionModal = ref(false)

const ruleId = useRouteParam("ruleId")

const { loading, entity: rule } = useEntityDetails<RuleDetail, string>({
	entity: () => null,
	id: () => ruleId.value,
	fetch: (id, signal) =>
		Api.copilotSearches.getRuleById(id, signal).then(res => ({
			entity: res.data.success ? (res.data.rule ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Rule not found",
	errorMessage: "An error occurred. Please try again later."
})
</script>
