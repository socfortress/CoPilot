<template>
	<div class="customer-ai-notifications">
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane name="routes" tab="Routes" display-directive="show:lazy">
				<CustomerAiNotificationRoutes :customer-code="customerCode" />
			</n-tab-pane>
			<n-tab-pane name="shuffle_integrations" tab="Shuffle integrations" display-directive="show:lazy">
				<CustomerShuffleIntegrations :customer-code="customerCode" />
			</n-tab-pane>
			<n-tab-pane name="dispatch_log" tab="Dispatch log" display-directive="show:lazy">
				<CustomerAiNotificationDispatchLog :customer-code="customerCode" />
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
import CustomerAiNotificationRoutes from "./CustomerAiNotificationRoutes.vue"
import CustomerShuffleIntegrations from "./CustomerShuffleIntegrations.vue"

defineProps<{
	customerCode: string
}>()
</script>
