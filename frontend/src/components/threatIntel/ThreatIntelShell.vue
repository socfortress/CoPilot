<template>
	<div class="flex flex-col gap-6">
		<header class="flex flex-col gap-1">
			<div class="flex items-center gap-3">
				<Icon :name="ThreatIcon" :size="22" />
				<h2 class="text-2xl font-semibold">Threat Intel</h2>
			</div>
			<p class="text-sm">
				Look up an indicator or submit a file to the threat intelligence sources connected to CoPilot.
			</p>
		</header>

		<n-alert v-if="openCTIRequestedButMissing" type="warning" show-icon closable>
			<template #header>OpenCTI is not configured</template>
			Set its URL and API token under
			<router-link :to="{ name: 'Connectors' }">Connectors</router-link>
			and press Verify, and it appears here as a tab.
		</n-alert>

		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="socfortress" tab="SOCFortress" display-directive="show:lazy">
				<div class="flex max-w-3xl flex-col gap-4">
					<p class="text-secondary text-sm">
						Reputation lookup for an IP address, domain or SHA256 hash against SOCFortress Threat Intel.
					</p>
					<ThreatIntelForm />
				</div>
			</n-tab-pane>
			<n-tab-pane name="virustotal" tab="VirusTotal" display-directive="show:lazy">
				<div class="flex max-w-3xl flex-col gap-4">
					<p class="text-secondary text-sm">
						Submit a file to VirusTotal for analysis. Uploading a file shares it with VirusTotal and its
						community, so don't submit customer data you can't disclose.
					</p>
					<VirusTotalForm />
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="openCTIAvailable" name="opencti" tab="OpenCTI" display-directive="show:lazy">
				<OpenCTIPanel />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NAlert, NTabPane, NTabs } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import OpenCTIPanel from "@/components/opencti/OpenCTIPanel.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import ThreatIntelForm from "./ThreatIntelForm.vue"
import VirusTotalForm from "./VirusTotalForm.vue"

const TABS = ["socfortress", "virustotal", "opencti"] as const
type Tab = (typeof TABS)[number]

const ThreatIcon = "mynaui:info-waves"
const route = useRoute()
const router = useRouter()
const { available: openCTIAvailable, loaded, refresh } = useOpenCTIAvailability()
const checked = ref(loaded.value)

const requestedTab = computed<Tab>(() =>
	TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "socfortress"
)

// The OpenCTI tab exists only for a verified connector. Until the check answers,
// a deep link to it (including the old /opencti URL) waits rather than falling
// back and jumping once the answer arrives.
const activeTab = computed<Tab>({
	get: () =>
		requestedTab.value === "opencti" && checked.value && !openCTIAvailable.value
			? "socfortress"
			: requestedTab.value,
	set: tab => {
		// `replace`, not `push`: switching source is not a navigation worth a
		// history entry. The OpenCTI sub-view only means something on its own tab.
		const { view: _view, ...query } = route.query
		router.replace({ query: tab === "opencti" ? { ...route.query, tab } : { ...query, tab } })
	}
})

const openCTIRequestedButMissing = computed(
	() => requestedTab.value === "opencti" && checked.value && !openCTIAvailable.value
)

onBeforeMount(async () => {
	if (!loaded.value) await refresh()
	checked.value = true
})
</script>
