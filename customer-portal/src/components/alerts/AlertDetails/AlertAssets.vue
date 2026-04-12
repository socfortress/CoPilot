<template>
	<div v-if="alert.assets?.length" class="flex flex-col gap-2">
		<CardEntity v-for="asset in alert.assets" :key="asset.id" size="small" embedded>
			<template #header-main>#{{ asset.id }} - {{ asset.asset_name }}</template>
			<template #header-extra>{{ asset.index_name }}</template>
			<template #default>
				<div class="flex flex-wrap gap-2">
					<Chip size="small" :value="asset.agent_id" label="Agent ID" />
					<Chip
						v-if="asset.velociraptor_id"
						size="small"
						:value="asset.velociraptor_id"
						label="Velociraptor ID"
					/>
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
import { NCard, NEmpty } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"

defineProps<{
	alert: Alert
}>()
</script>
