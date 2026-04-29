<template>
	<div class="customer-ai-notifications">
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane name="routes" tab="Routes" display-directive="show:lazy">
				<CustomerAiNotificationRoutes :customer-code="customerCode" />
			</n-tab-pane>
			<n-tab-pane name="dispatch_log" tab="Dispatch log" display-directive="show:lazy">
				<CustomerAiNotificationDispatchLog :customer-code="customerCode" />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
// Container for the per-customer "AI Notifications" tab. Splits route
// management from the read-only dispatch log so admins editing routes
// don't accidentally scroll a noisy log, and analysts auditing a
// missed message can land directly on the log via tab-deep-link later.
import { NTabPane, NTabs } from "naive-ui"
import CustomerAiNotificationDispatchLog from "./CustomerAiNotificationDispatchLog.vue"
import CustomerAiNotificationRoutes from "./CustomerAiNotificationRoutes.vue"

defineProps<{
	customerCode: string
}>()
</script>
