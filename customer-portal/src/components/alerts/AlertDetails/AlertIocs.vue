<template>
	<div v-if="alert.iocs?.length">
		<div
			v-for="ioc in alert.iocs"
			:key="ioc.id"
			class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
		>
			<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-3">
				<div>
					<span class="font-medium">Value:</span>
					<code class="rounded bg-gray-100 px-1 text-xs">{{ ioc.ioc_value }}</code>
				</div>
				<div>
					<span class="font-medium">Type:</span>
					{{ ioc.ioc_type }}
				</div>
				<div>
					<span class="font-medium">Description:</span>
					{{ ioc.ioc_description }}
				</div>
			</div>
		</div>
	</div>

	<n-empty v-else description="No indicators of compromise found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NEmpty } from "naive-ui"

defineProps<{
	alert: Alert
}>()
</script>
