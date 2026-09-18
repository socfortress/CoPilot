<template>
	<div class="flex flex-col gap-5">
		<p class="text-secondary text-sm">
			Threat intelligence from your OpenCTI platform. Look up an IOC by exact value, or browse and filter
			indicators and open any of them for full context.
		</p>

		<OpenCTIPlatformStats />

		<n-tabs v-model:value="activeView" type="segment" animated class="max-w-md">
			<n-tab name="lookup" tab="IOC Lookup" />
			<n-tab name="indicators" tab="Indicators" />
		</n-tabs>

		<div v-if="activeView === 'lookup'" class="max-w-3xl">
			<OpenCTIForm />
		</div>
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
