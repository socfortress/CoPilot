<template>
	<div class="@container flex flex-col gap-6" data-testid="exposure-page">
		<header class="flex flex-col gap-1.5">
			<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">
				{{ $t("exposure.page.title") }}
			</h1>
			<p class="text-secondary max-w-prose text-sm">
				{{ $t("exposure.page.intro") }}
			</p>
		</header>

		<n-tabs :value="tab" type="line" animated data-testid="exposure-tabs" @update:value="setTab">
			<n-tab-pane name="vulnerabilities" :tab="$t('exposure.page.vulnerabilitiesTab')" display-directive="show:lazy">
				<VulnerabilitiesTab />
			</n-tab-pane>
			<n-tab-pane name="compliance" :tab="$t('exposure.page.complianceTab')" display-directive="show:lazy">
				<ComplianceTab />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { ExposureTab } from "./exposure"
import { NTabPane, NTabs } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import ComplianceTab from "./ComplianceTab.vue"
import { tabFromQuery, withExposureQuery } from "./exposure"
import VulnerabilitiesTab from "./VulnerabilitiesTab.vue"

/**
 * The Exposure page (#1289): the customer's vulnerabilities and compliance across all their
 * agents, one tab each, the tab in the URL. Each tab loads when first opened.
 */

const route = useRoute()
const router = useRouter()

const tab = computed<ExposureTab>(() => tabFromQuery(route.query))

function setTab(next: ExposureTab) {
	if (next !== tab.value) router.replace({ query: withExposureQuery(route.query, next) })
}
</script>
