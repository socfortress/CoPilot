<template>
	<div class="customer-ai-notifications">
		<n-tabs type="segment" animated tab-class="px-4! py-1!" class="[&_.n-tabs-nav]:mx-auto [&_.n-tabs-nav]:mb-6">
			<n-tab-pane name="routes" tab="Routes" display-directive="show:lazy" class="p-0!">
				<CustomerAiNotificationRoutes :customer-code />
			</n-tab-pane>
			<n-tab-pane
				name="shuffle_integrations"
				tab="Shuffle integrations"
				display-directive="show:lazy"
				class="p-0!"
			>
				<CustomerShuffleIntegrations :customer-code />
			</n-tab-pane>
			<n-tab-pane name="dispatch_log" tab="Dispatch log" display-directive="show:lazy" class="pt-3!">
				<CustomerAiNotificationDispatchLog :customer-code />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
// Container for the per-customer "AI Notifications" tab. Three
// sub-tabs:
//   - Routes: CRUD list + form for notification rules
//   - Shuffle integrations: CRUD for the customer's Shuffle Org-Id rows
//     used by 'shuffle'-channel routes
//   - Dispatch log: read-only audit trail of every dispatch attempt
import { NTabPane, NTabs } from "naive-ui"
import CustomerAiNotificationDispatchLog from "./CustomerAiNotificationDispatchLog.vue"
import CustomerAiNotificationRoutes from "./CustomerAiNotificationRoutes/CustomerAiNotificationRoutes.vue"
import CustomerShuffleIntegrations from "./CustomerShuffleIntegrations/CustomerShuffleIntegrations.vue"

defineProps<{
	customerCode: string
}>()
</script>
