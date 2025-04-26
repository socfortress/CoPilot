<template>
	<div class="page" ref="page">
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane
				name="ConfiguredSources"
				:tab="`Configured Sources (${configuredSourcesListTotal})`"
				display-directive="show"
			>
				<ConfiguredSourcesList
					:show-toolbar="showConfiguredSourcesListToolbar"
					@mounted="configuredSourcesListCTX = $event"
					@loaded="configuredSourcesListTotal = $event"
				/>
			</n-tab-pane>
			<n-tab-pane name="ExclusionRules" tab="Exclusion Rules" display-directive="show">
				<ExclusionRulesList
					:show-creation-button="showExclusionRulesListCreationButton"
					:show-info-popover="showExclusionRulesListInfoPopover"
					@mounted="exclusionRulesListCTX = $event"
				/>
			</n-tab-pane>

			<template #suffix>
				<div class="flex items-center gap-2">
					<NewConfiguredSourceButton
						@success="reloadConfiguredSourcesList()"
						v-if="!showConfiguredSourcesListToolbar"
					/>
					<NewExclusionRuleButton
						@success="reloadExclusionRulesList()"
						v-if="!showExclusionRulesListCreationButton"
					/>
				</div>
			</template>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import ExclusionRulesList from "@/components/incidentManagement/exclusionRules/ExclusionRulesList.vue"
import ConfiguredSourcesList from "@/components/incidentManagement/sources/ConfiguredSourcesList.vue"
import NewConfiguredSourceButton from "@/components/incidentManagement/sources/NewConfiguredSourceButton.vue"
import NewExclusionRuleButton from "@/components/incidentManagement/exclusionRules/NewExclusionRuleButton.vue"

import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import { useResizeObserver } from "@vueuse/core"

const configuredSourcesListTotal = ref(0)
const configuredSourcesListCTX = ref<{ reload: () => void } | null>(null)
const exclusionRulesListCTX = ref<{ reload: () => void } | null>(null)
const page = ref()

const showConfiguredSourcesListToolbar = ref(false)
const showExclusionRulesListCreationButton = ref(false)
const showExclusionRulesListInfoPopover = ref(false)

function reloadConfiguredSourcesList() {
	if (configuredSourcesListCTX.value) {
		configuredSourcesListCTX.value.reload()
	}
}

function reloadExclusionRulesList() {
	if (exclusionRulesListCTX.value) {
		exclusionRulesListCTX.value.reload()
	}
}

useResizeObserver(page, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	showConfiguredSourcesListToolbar.value = width < 600
	showExclusionRulesListCreationButton.value = width < 800
	showExclusionRulesListInfoPopover.value = width > 600
})
</script>
