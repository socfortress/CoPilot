<template>
	<div class="page flex flex-col gap-4">
		<n-button
			quaternary
			class="self-start"
			@click="
				goBack(
					routeEventSearch({
						customer_code: customerCode ?? undefined,
						source_name: sourceName ?? undefined
					})
				)
			"
		>
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
import Icon from "@/components/common/Icon.vue"
import EventDetails from "@/components/events/EventDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeEventSearch } = useNavigation()

const BackIcon = "carbon:arrow-left"

const customerCode = useRouteParam("customerCode")
const sourceName = useRouteParam("sourceName")
const indexName = useRouteParam("indexName")
const eventId = useRouteParam("eventId")
</script>
