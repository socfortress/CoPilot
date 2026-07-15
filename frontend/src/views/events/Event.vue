<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader
			:back-route="
				routeEventSearch({
					customer_code: customerCode ?? undefined,
					source_name: sourceName ?? undefined
				})
			"
		/>

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
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import EventDetails from "@/components/events/EventDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeEventSearch } = useNavigation()

const customerCode = useRouteParam("customerCode")
const sourceName = useRouteParam("sourceName")
const indexName = useRouteParam("indexName")
const eventId = useRouteParam("eventId")
</script>
