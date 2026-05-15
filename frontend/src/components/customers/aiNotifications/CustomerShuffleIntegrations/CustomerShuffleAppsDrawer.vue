<template>
	<n-drawer v-model:show="show" :width="720" placement="right" display-directive="show">
		<n-drawer-content closable>
			<template #header>
				<div class="flex items-center gap-2">
					<Icon name="carbon:integration" :size="18" />
					<span>Shuffle apps</span>
					<span v-if="integration" class="text-secondary">•</span>
					<span v-if="integration" class="text-secondary">{{ integration.display_name }}</span>
				</div>
			</template>

			<div class="flex flex-col gap-3">
				<div class="text-secondary text-sm">
					Browse Shuffle's catalog of 3,000+ integrations and authenticate the ones this org needs. Apps you
					authenticate here become available in the route form's app picker — Shuffle handles the OAuth flow;
					CoPilot just stores the resulting Org-Id and references it in routes.
				</div>

				<div v-if="loadingToken" class="text-tertiary py-6 text-center text-sm">
					Fetching org auth token from Shuffle…
				</div>

				<div v-else-if="error" class="text-error py-6 text-center text-sm">
					{{ error }}
				</div>

				<ShuffleMCPEmbed
					v-else-if="orgAuthToken"
					:auth-token="orgAuthToken"
					placeholder="Find a Shuffle app to authenticate…"
					inline
					layout="grid"
					:grid-columns="3"
					prevent-default
				/>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { ShuffleIntegration } from "@/types/notifications.d"
import { NDrawer, NDrawerContent } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ShuffleMCPEmbed from "@/components/shuffle/ShuffleMCPEmbed.vue"
import { getApiErrorMessage } from "@/utils"

// Per-integration "Manage apps" drawer. Opened from the Shuffle
// integration list when an admin wants to authenticate a new Shuffle
// app for that customer's org. The actual auth UI is the embedded
// ShuffleMCP picker; this drawer is responsible for:
//   1. Fetching the org auth token via Shuffle's existing connector
//      endpoint (already exposed on CoPilot's backend)
//   2. Passing the token into the embed
//   3. Surfacing a confirmation message when the admin picks an app

const props = defineProps<{
	integration: ShuffleIntegration | null
}>()

const show = defineModel<boolean>("show", { required: true, default: false })

const orgAuthToken = ref<string | null>(null)
const loadingToken = ref(false)
const error = ref<string | null>(null)

async function loadOrgToken(orgId: string) {
	if (orgAuthToken.value) return

	loadingToken.value = true
	error.value = null

	try {
		const res = await Api.shuffle.getOrganization(orgId)
		if (res.data.success) {
			orgAuthToken.value = res.data.data?.org_auth?.token ?? null
			if (!orgAuthToken.value) {
				error.value =
					"Shuffle returned an org without an org_auth.token. Check the Shuffle connector config or contact Shuffle support."
			}
		} else {
			error.value = res.data.message || "Failed to fetch org auth token"
		}
	} catch (err) {
		error.value = getApiErrorMessage(err as ApiError) || "Failed to fetch org auth token"
	} finally {
		loadingToken.value = false
	}
}

// Re-fetch the org token whenever the drawer opens or switches to a
// different integration. Cleared when closing so reopening on a
// different integration doesn't briefly flash stale data.
watch(
	[show, () => props.integration?.id],
	([showValue, integrationId]) => {
		if (showValue && integrationId && props.integration?.shuffle_org_id) {
			loadOrgToken(props.integration.shuffle_org_id)
		}
	},
	{ immediate: true }
)
</script>
