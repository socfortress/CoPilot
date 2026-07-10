<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<EventDetails
			v-if="customerCode && sourceName && indexName && eventId"
			:customer-code
			:source-name
			:index-name
			:event-id
		/>
		<n-empty v-else description="Invalid event reference" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import EventDetails from "@/components/events/EventDetails.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeEventSearch } = useNavigation()

const BackIcon = "carbon:arrow-left"

function decodeParam(raw: string | string[] | undefined): string | null {
	if (!raw) return null
	const value = Array.isArray(raw) ? raw[0] : raw
	try {
		return decodeURIComponent(value)
	} catch {
		return value
	}
}

const customerCode = computed(() => decodeParam(route.params.customerCode))
const sourceName = computed(() => decodeParam(route.params.sourceName))
const indexName = computed(() => decodeParam(route.params.indexName))
const eventId = computed(() => decodeParam(route.params.eventId))

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	routeEventSearch({
		customer_code: customerCode.value ?? undefined,
		source_name: sourceName.value ?? undefined
	}).navigate()
}
</script>
