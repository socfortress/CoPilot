<template>
	<div class="page">
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane
				name="ConfiguredSources"
				:tab="`Configured Sources (${configuredSourcesListTotal})`"
				display-directive="show"
			>
				<ConfiguredSourcesList
					:show-toolbar="false"
					@mounted="configuredSourcesListCTX = $event"
					@loaded="configuredSourcesListTotal = $event"
				/>
			</n-tab-pane>
			<n-tab-pane name="ExclusionRules" tab="Exclusion Rules" display-directive="show">
				Exclusion Rules...
			</n-tab-pane>

			<template #suffix>
				<NewConfiguredSourceButton @success="reload()" />
			</template>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import ConfiguredSourcesList from "@/components/incidentManagement/sources/ConfiguredSourcesList.vue"
import NewConfiguredSourceButton from "@/components/incidentManagement/sources/NewConfiguredSourceButton.vue"
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"

const configuredSourcesListTotal = ref(0)
const configuredSourcesListCTX = ref<{ reload: () => void } | null>(null)

function reload() {
	if (configuredSourcesListCTX.value) {
		configuredSourcesListCTX.value.reload()
	}
}
</script>
