<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedConnector" :embedded>
			<template #headerMain>{{ resolvedConnector.name }}</template>

			<template #default>
				<p v-if="resolvedConnector.description" class="text-secondary mb-4">
					{{ resolvedConnector.description }}
				</p>
				<Markdown v-if="resolvedConnector.details" :source="resolvedConnector.details" />
				<n-empty v-else description="No connector details" class="h-32 justify-center" />
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of resolvedConnector.keys" :key="authKey.auth_key_name">
						<template #value>{{ authKey.auth_key_name }}</template>
					</Badge>
				</div>
			</template>

			<template v-if="$slots.footerExtra" #footerExtra>
				<slot name="footerExtra" />
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { ServiceItemData } from "@/components/services/types"
import type { ApiError } from "@/types/common"
import type { NetworkConnector } from "@/types/network-connectors"
import axios from "axios"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Markdown from "@/components/common/Markdown.vue"
import { getApiErrorMessage } from "@/utils"

const props = withDefaults(
	defineProps<{
		connector?: ServiceItemData | NetworkConnector | null
		connectorId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: ServiceItemData): void
}>()

const message = useMessage()
const loading = ref(false)
const fetchedConnector = ref<ServiceItemData | null>(null)

let abortController: AbortController | null = null

function toServiceItemData(connector: NetworkConnector): ServiceItemData {
	return {
		id: connector.id,
		name: connector.network_connector_name,
		description: connector.description,
		details: connector.network_connector_details,
		keys: connector.network_connector_keys
	}
}

function normalizeConnector(connector: ServiceItemData | NetworkConnector): ServiceItemData {
	if ("network_connector_name" in connector) {
		return toServiceItemData(connector)
	}

	return connector
}

const resolvedConnector = computed(() => {
	if (props.connector) {
		return normalizeConnector(props.connector)
	}

	return fetchedConnector.value
})

function loadConnector(connectorId: number) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.networkConnectors
		.getAvailableNetworkConnector(connectorId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.network_connector) {
				const item = toServiceItemData(res.data.network_connector)
				fetchedConnector.value = item
				emit("loaded", item)
			} else {
				message.warning(res.data?.message || "Network connector not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load network connector.")
				loading.value = false
			}
		})
}

watch(
	() => [props.connector, props.connectorId] as const,
	([connector, connectorId]) => {
		if (connector) {
			abortController?.abort()
			fetchedConnector.value = null
			loading.value = false
			return
		}

		if (connectorId != null) {
			loadConnector(connectorId)
			return
		}

		abortController?.abort()
		fetchedConnector.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedConnector })
</script>
