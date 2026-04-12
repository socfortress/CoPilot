<template>
	<div v-if="alert.assets?.length" class="flex flex-col gap-2">
		<CardEntity v-for="asset in alert.assets" :key="asset.id" size="small" embedded>
			<template #header-main>#{{ asset.id }} - {{ asset.asset_name }}</template>
			<template #header-extra>{{ asset.index_name }}</template>
			<template #default>
				<div class="flex flex-wrap gap-2">
					<n-tag size="small">
						<div class="flex items-center gap-2">
							<div class="text-secondary">Agent ID</div>
							<div>{{ asset.agent_id }}</div>
						</div>
					</n-tag>
					<n-tag v-if="asset.velociraptor_id" size="small">
						<div class="flex items-center gap-2">
							<div class="text-secondary">Velociraptor ID</div>
							<div>{{ asset.velociraptor_id }}</div>
						</div>
					</n-tag>
				</div>
			</template>
		</CardEntity>
	</div>

	<n-card v-else-if="alert.asset_name" size="small">
		<template #header>
			<div class="text-secondary text-sm">Asset name</div>
		</template>
		{{ alert.asset_name }}
	</n-card>

	<n-empty v-else description="No assets found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NCard, NEmpty, NTag } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"

defineProps<{
	alert: Alert
}>()
</script>
