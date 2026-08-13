<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create an internal route" :back-route="routeInternalNotificationRoute()" />

		<!--
			The per-customer form, told to build an internal route. `scope` is what
			narrows the triggers and channels — Shuffle is unavailable here, since
			its integrations are per-customer and this route belongs to no tenant.
		-->
		<n-card size="small">
			<CustomerAiNotificationRouteForm
				:editing-route="null"
				scope="internal"
				@submitted="onSubmitted()"
				@close="goBack(routeInternalNotificationRoute())"
			/>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CustomerAiNotificationRouteForm from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteForm.vue"
import { useNavigation } from "@/composables/useNavigation"

// The form reports success without the saved row, so there is no id to land on
// — the list is the destination either way.

const { goBack, routeInternalNotificationRoute } = useNavigation()

function onSubmitted() {
	// `replace`, so browser-back doesn't return to a form for a route that now
	// exists.
	routeInternalNotificationRoute().replace()
}
</script>
