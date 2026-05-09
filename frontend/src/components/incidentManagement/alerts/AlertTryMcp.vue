<template>
	<div class="flex flex-col gap-4">
		<!-- No customer code on alert -->
		<n-alert v-if="!alert.customer_code" type="warning" title="No customer associated with this alert">
			Try MCP needs the alert's customer to look up their Shuffle integration.
		</n-alert>

		<!-- Loading customer integration -->
		<div v-else-if="loadingIntegration" class="text-tertiary py-6 text-center text-sm">
			Loading Shuffle integration for customer {{ alert.customer_code }}…
		</div>

		<!-- No integration configured -->
		<n-alert v-else-if="!activeIntegration" type="info" title="No Shuffle integration configured">
			This customer has no enabled Shuffle integration. Configure one in
			<strong>Customer → AI Notifications → Shuffle integrations</strong>
			before using Try MCP.
		</n-alert>

		<!-- Loading the org auth token -->
		<div v-else-if="loadingToken" class="text-tertiary py-6 text-center text-sm">Fetching org auth token…</div>

		<!-- Token fetch error -->
		<n-alert v-else-if="tokenError" type="error" title="Couldn't fetch Shuffle auth token">
			{{ tokenError }}
		</n-alert>

		<!-- Active flow: pick an app, then mount TryMcpSection -->
		<template v-else-if="orgAuthToken">
			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<span class="text-sm">
						Acting as
						<strong>{{ activeIntegration.display_name }}</strong>
						<span class="text-tertiary">· alert #{{ alert.id }}</span>
					</span>
					<n-button v-if="selectedAppName" size="tiny" @click="selectedAppName = null">
						<template #icon>
							<Icon :name="ResetIcon" :size="14" />
						</template>
						Pick a different app
					</n-button>
				</div>

				<!-- App picker: only mounted until a selection is made -->
				<ShuffleMCPEmbed
					v-if="!selectedAppName"
					:auth-token="orgAuthToken"
					placeholder="Pick an app to act on this alert (e.g. Crowdstrike, Cloudflare, VirusTotal)…"
					inline
					layout="list"
					@app-selected="onAppSelected"
				/>

				<!-- Try MCP for the chosen app -->
				<TryMcpEmbed v-else :app-name="selectedAppName" :auth-token="orgAuthToken" />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import type { ShuffleIntegration } from "@/types/notifications.d"
import { NAlert, NButton, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ShuffleMCPEmbed from "@/components/common/ShuffleMCPEmbed.vue"
import TryMcpEmbed from "@/components/common/TryMcpEmbed.vue"

const props = defineProps<{ alert: Alert }>()

const ResetIcon = "carbon:reset"

const message = useMessage()

const integrations = ref<ShuffleIntegration[]>([])
const loadingIntegration = ref(false)
const orgAuthToken = ref<string | null>(null)
const loadingToken = ref(false)
const tokenError = ref<string | null>(null)
const selectedAppName = ref<string | null>(null)

// First enabled integration wins. Multi-integration customers will need
// a picker in a follow-up; vast majority have one.
const activeIntegration = computed<ShuffleIntegration | null>(
	() => integrations.value.find(i => i.enabled) ?? integrations.value[0] ?? null
)

async function loadIntegrations() {
	if (!props.alert.customer_code) return
	loadingIntegration.value = true
	try {
		const res = await Api.notifications.listShuffleIntegrations(props.alert.customer_code)
		if (res.data.success) {
			integrations.value = res.data?.integrations || []
			if (activeIntegration.value?.shuffle_org_id) {
				await loadOrgToken(activeIntegration.value.shuffle_org_id)
			}
		} else {
			message.warning(res.data?.message || "Failed to load Shuffle integrations.")
		}
	} catch (err: unknown) {
		const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
		message.error(msg || "Failed to load Shuffle integrations.")
	} finally {
		loadingIntegration.value = false
	}
}

async function loadOrgToken(orgId: string) {
	loadingToken.value = true
	tokenError.value = null
	try {
		const res = await Api.shuffle.getOrganization(orgId)
		if (res.data.success) {
			orgAuthToken.value = res.data.data?.org_auth?.token ?? null
			if (!orgAuthToken.value) {
				tokenError.value = "Shuffle returned an org without an org_auth.token."
			}
		} else {
			tokenError.value = res.data.message || "Failed to fetch org auth token."
		}
	} catch (err: unknown) {
		const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
		tokenError.value = msg || "Failed to fetch org auth token."
	} finally {
		loadingToken.value = false
	}
}

function onAppSelected(payload: unknown) {
	const name = (payload as { app?: { name?: string } } | undefined)?.app?.name
	if (name) {
		selectedAppName.value = name
	}
}

onBeforeMount(() => {
	loadIntegrations()
})
</script>
