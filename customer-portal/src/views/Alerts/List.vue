<template>
	<div class="page @container flex flex-col gap-6">
		<AlertsOverviewStatsCards />
		<AlertsList />
	</div>
</template>

<script setup lang="ts">
import AlertsOverviewStatsCards from "@/components/alerts/AlertsOverviewStatsCards.vue"
import AlertsList from "@/components/alerts/List.vue"
</script>
