<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedIntegration" :embedded>
			<template #headerMain>{{ resolvedIntegration.name }}</template>

			<template #default>
				<p v-if="resolvedIntegration.description" class="text-secondary mb-4">
					{{ resolvedIntegration.description }}
				</p>
				<Markdown v-if="resolvedIntegration.details" :source="resolvedIntegration.details" />
				<n-empty v-else description="No integration details" class="h-32 justify-center" />
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of resolvedIntegration.keys" :key="authKey.auth_key_name">
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
import type { AvailableIntegration } from "@/types/integrations"
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
		integration?: ServiceItemData | AvailableIntegration | null
		integrationId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: ServiceItemData): void
}>()

const message = useMessage()
const loading = ref(false)
const fetchedIntegration = ref<ServiceItemData | null>(null)

let abortController: AbortController | null = null

function toServiceItemData(integration: AvailableIntegration): ServiceItemData {
	return {
		id: integration.id,
		name: integration.integration_name,
		description: integration.description,
		details: integration.integration_details,
		keys: integration.auth_keys
	}
}

function normalizeIntegration(integration: ServiceItemData | AvailableIntegration): ServiceItemData {
	if ("integration_name" in integration) {
		return toServiceItemData(integration)
	}

	return integration
}

const resolvedIntegration = computed(() => {
	if (props.integration) {
		return normalizeIntegration(props.integration)
	}

	return fetchedIntegration.value
})

function loadIntegration(integrationId: number) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.integrations
		.getAvailableIntegration(integrationId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.available_integration) {
				const item = toServiceItemData(res.data.available_integration)
				fetchedIntegration.value = item
				emit("loaded", item)
			} else {
				message.warning(res.data?.message || "Integration not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load integration.")
				loading.value = false
			}
		})
}

watch(
	() => [props.integration, props.integrationId] as const,
	([integration, integrationId]) => {
		if (integration) {
			abortController?.abort()
			fetchedIntegration.value = null
			loading.value = false
			return
		}

		if (integrationId != null) {
			loadIntegration(integrationId)
			return
		}

		abortController?.abort()
		fetchedIntegration.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedIntegration })
</script>
