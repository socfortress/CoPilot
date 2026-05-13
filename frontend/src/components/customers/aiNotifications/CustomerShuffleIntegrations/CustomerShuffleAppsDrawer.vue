<template>
	<n-drawer v-model:show="showLocal" :width="720" placement="right">
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
					@app-selected="onAppSelected"
				/>
			</div>
		</n-drawer-content>

		<!-- All-in-one app drawer for the picked app. Inline auth for
		     API-key/URL apps; OAuth apps still redirect on click. Stacks
		     visually on top of the picker drawer. -->
		<AppDetailDrawerEmbed v-model:open="appDrawerOpen" :app-name="appDrawerAppName" />
	</n-drawer>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { ShuffleIntegration } from "@/types/notifications.d"
import { NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import AppDetailDrawerEmbed from "@/components/shuffle/AppDetailDrawerEmbed.vue"
import Icon from "@/components/common/Icon.vue"
import ShuffleMCPEmbed from "@/components/shuffle/ShuffleMCPEmbed.vue"
import { getApiErrorMessage } from "@/utils"
import type { AppSelectedEvent } from "@shuffleio/shuffle-mcps"

// Per-integration "Manage apps" drawer. Opened from the Shuffle
// integration list when an admin wants to authenticate a new Shuffle
// app for that customer's org. The actual auth UI is the embedded
// ShuffleMCP picker; this drawer is responsible for:
//   1. Fetching the org auth token via Shuffle's existing connector
//      endpoint (already exposed on CoPilot's backend)
//   2. Passing the token into the embed
//   3. Surfacing a confirmation message when the admin picks an app

const props = defineProps<{
	show: boolean
	integration: ShuffleIntegration | null
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
}>()

// v-model:show bridge — lets the drawer's built-in close button
// propagate state back to the parent.
const showLocal = computed({
	get: () => props.show,
	set: (v: boolean) => emit("update:show", v)
})

const orgAuthToken = ref<string | null>(null)
const loadingToken = ref(false)
const error = ref<string | null>(null)

async function loadOrgToken(orgId: string) {
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

const appDrawerOpen = ref(false)
const appDrawerAppName = ref<string | null>(null)

function onAppSelected(payload: AppSelectedEvent) {
	// With prevent-default on the picker, Shuffle doesn't fire the
	// top-level OAuth redirect. We open AppDetailDrawer for the picked
	// app — the drawer renders an inline auth form for API-key/URL apps
	// and a redirect handoff button for OAuth ones, so the admin can
	// configure both kinds without leaving the page.
	const name = payload.app?.name
	if (!name) return
	appDrawerAppName.value = name
	appDrawerOpen.value = true
}

// Re-fetch the org token whenever the drawer opens or switches to a
// different integration. Cleared when closing so reopening on a
// different integration doesn't briefly flash stale data.
watch(
	() => [props.show, props.integration?.id] as const,
	([show, id]) => {
		if (show && id && props.integration?.shuffle_org_id) {
			loadOrgToken(props.integration.shuffle_org_id)
		} else if (!show) {
			orgAuthToken.value = null
			error.value = null
		}
	},
	{ immediate: true }
)
</script>
