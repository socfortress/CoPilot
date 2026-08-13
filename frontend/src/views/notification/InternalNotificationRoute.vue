<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="notificationRoute?.name" :back-route="routeInternalNotificationRoute()">
			<template v-if="notificationRoute" #meta>
				<span class="text-secondary font-mono text-sm">#{{ notificationRoute.id }}</span>
				<Badge type="splitted" size="small" :color="notificationRoute.enabled ? 'success' : undefined">
					<template #label>status</template>
					<template #value>{{ notificationRoute.enabled ? "enabled" : "disabled" }}</template>
				</Badge>
			</template>
		</DetailPageHeader>

		<CustomerAiNotificationRouteOverview
			v-if="routeId != null"
			:key="routeId"
			:route-id
			scope="internal"
			full-width
			@loaded="notificationRoute = $event"
			@deleted="routeInternalNotificationRoute().navigate()"
		/>
		<n-empty v-else description="Invalid route ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { NotificationRoute } from "@/types/notifications"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Badge from "@/components/common/Badge.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CustomerAiNotificationRouteOverview from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

// Internal-scope only: a customer's route is reached through its customer, and
// its endpoint needs the tenant code that a bare id doesn't carry.

const { routeInternalNotificationRoute } = useNavigation()

const notificationRoute = ref<NotificationRoute | null>(null)

const routeId = useRouteIdParam("id")

watch(routeId, () => {
	notificationRoute.value = null
})
</script>
