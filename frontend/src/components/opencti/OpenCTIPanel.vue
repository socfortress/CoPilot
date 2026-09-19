<template>
	<div class="flex flex-col gap-5">
		<p class="text-secondary text-sm">
			Threat intelligence from your OpenCTI platform. Look up an IOC by exact value, or browse and filter
			indicators and open any of them for full context.
		</p>

		<!-- The view switch and the platform readout share one line: tabs lead, stats follow. -->
		<div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
			<n-tabs v-model:value="activeView" type="segment" animated size="small" class="w-full max-w-xs">
				<n-tab name="lookup" tab="IOC Lookup" />
				<n-tab name="indicators" tab="Indicators" />
			</n-tabs>
			<OpenCTIPlatformStats />
		</div>

		<OpenCTIForm v-if="activeView === 'lookup'" />
		<OpenCTIIndicatorsIndex v-else />
	</div>
</template>

<script setup lang="ts">
import { NTab, NTabs } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import OpenCTIForm from "./OpenCTIForm.vue"
import OpenCTIIndicatorsIndex from "./OpenCTIIndicatorsIndex.vue"
import OpenCTIPlatformStats from "./OpenCTIPlatformStats.vue"

// The OpenCTI tab of the Threat Intel page (#1153). Its own sub-view lives in
// `?view=` because the page already uses `?tab=` for the source.
const VIEWS = ["lookup", "indicators"] as const
type View = (typeof VIEWS)[number]

const route = useRoute()
const router = useRouter()

const activeView = computed<View>({
	get: () => (VIEWS.includes(route.query.view as View) ? (route.query.view as View) : "lookup"),
	set: view => {
		router.replace({ query: { ...route.query, view } })
	}
})
</script>
