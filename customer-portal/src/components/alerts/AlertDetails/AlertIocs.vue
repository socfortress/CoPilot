<template>
	<div v-if="alert.iocs?.length" class="flex flex-col gap-2">
		<CardEntity v-for="ioc in alert.iocs" :key="ioc.id" size="small" embedded>
			<template #header-main>{{ ioc.ioc_value }}</template>
			<template #header-extra>{{ ioc.ioc_type }}</template>
			<template #default>{{ ioc.ioc_description }}</template>
		</CardEntity>
	</div>

	<n-empty v-else description="No indicators of compromise found" class="min-h-50 justify-center" />
</template>

<script setup lang="ts">
import type { Alert } from "@/api/endpoints/alerts"
import { NEmpty } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"

defineProps<{
	alert: Alert
}>()
</script>
