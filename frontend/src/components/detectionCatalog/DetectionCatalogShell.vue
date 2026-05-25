<template>
	<div class="flex flex-col gap-6">
		<header class="flex flex-col gap-4">
			<div class="flex flex-wrap items-end justify-between gap-3">
				<div class="flex flex-col gap-1">
					<div class="flex items-center gap-3">
						<Icon :name="CatalogIcon" :size="22" />
						<h2 class="m-0 text-2xl font-semibold">Detections Catalog</h2>
					</div>
					<p class="text-sm">
						Discovery surface for the CoPilot detection corpus and the Wazuh ruleset. Browse the CoPilot
						Searches grouped by analytic story, inspect every Wazuh rule shipped by the manager, see your
						MITRE coverage gaps, and pivot by compliance framework.
					</p>
				</div>
			</div>

			<DetectionCatalogStats />
		</header>

		<n-tabs type="line" animated>
			<n-tab-pane name="stories" display-directive="show:lazy">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="StoryIcon" :size="15" />
						CoPilot Searches
					</div>
				</template>
				<StoriesIndex />
			</n-tab-pane>
			<n-tab-pane name="wazuh" display-directive="show:lazy">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="WazuhIcon" :size="15" />
						Wazuh Rules
					</div>
				</template>
				<WazuhRulesIndex />
			</n-tab-pane>
			<n-tab-pane name="gaps" display-directive="show:lazy">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="GapsIcon" :size="15" />
						Coverage Gaps
					</div>
				</template>
				<CoverageGapsIndex />
			</n-tab-pane>
			<n-tab-pane name="compliance" display-directive="show:lazy">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="ComplianceIcon" :size="15" />
						Compliance
					</div>
				</template>
				<ComplianceIndex />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import ComplianceIndex from "./ComplianceIndex.vue"
import CoverageGapsIndex from "./CoverageGapsIndex.vue"
import DetectionCatalogStats from "./DetectionCatalogStats.vue"
import StoriesIndex from "./StoriesIndex.vue"
import WazuhRulesIndex from "./WazuhRulesIndex.vue"

const CatalogIcon = "carbon:catalog"
const StoryIcon = "carbon:book"
const WazuhIcon = "carbon:document-security"
const GapsIcon = "carbon:warning-square"
const ComplianceIcon = "carbon:certificate-check"
</script>
