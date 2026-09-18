<template>
	<div class="flex flex-col gap-6">
		<header class="flex flex-col gap-4">
			<div class="flex flex-col gap-1">
				<div class="flex items-center gap-3">
					<Icon :name="OpenCTIIcon" :size="22" />
					<h2 class="text-2xl font-semibold">OpenCTI</h2>
				</div>
				<p class="text-sm">
					Threat intelligence from your OpenCTI platform. Look up an IOC by exact value, or browse and filter
					indicators and open any of them for full context.
				</p>
			</div>

			<OpenCTIPlatformStats v-if="available" />
		</header>

		<n-spin v-if="checking" class="min-h-40" />

		<n-alert v-else-if="!available" type="warning" show-icon>
			<template #header>OpenCTI is not configured</template>
			This page needs a verified OpenCTI connector. Set its URL and API token under
			<router-link :to="{ name: 'Connectors' }">Connectors</router-link>
			and press Verify.
		</n-alert>

		<n-tabs v-else v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="lookup" tab="IOC Lookup" display-directive="show:lazy">
				<div class="max-w-3xl">
					<OpenCTIForm />
				</div>
			</n-tab-pane>
			<n-tab-pane name="indicators" tab="Indicators" display-directive="show:lazy">
				<OpenCTIIndicatorsIndex />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import OpenCTIForm from "./OpenCTIForm.vue"
import OpenCTIIndicatorsIndex from "./OpenCTIIndicatorsIndex.vue"
import OpenCTIPlatformStats from "./OpenCTIPlatformStats.vue"

const TABS = ["lookup", "indicators"] as const
type Tab = (typeof TABS)[number]

const OpenCTIIcon = "mdi:shield-search"
const route = useRoute()
const router = useRouter()
const { available, loaded, refresh } = useOpenCTIAvailability()
const checking = ref(!loaded.value)

// The tab lives in the URL (`?tab=indicators`) so it survives a reload and can be
// linked to. `replace`, not `push`: switching tabs is not a navigation worth a
// history entry.
const activeTab = computed<Tab>({
	get: () => (TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "lookup"),
	set: tab => {
		router.replace({ query: { ...route.query, tab } })
	}
})

onBeforeMount(async () => {
	// A deep link can land here before the navbar's availability check has
	// answered; wait for it rather than flashing "not configured".
	if (!loaded.value) await refresh()
	checking.value = false
})
</script>
