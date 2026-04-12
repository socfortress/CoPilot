<template>
	<div class="page @container flex flex-col gap-6">
		<CasesOverviewStatsCards />
		<CasesList />
	</div>
</template>

<script setup lang="ts">
import CasesOverviewStatsCards from "@/components/cases/CasesOverviewStatsCards.vue"
import CasesList from "@/components/cases/List.vue"
</script>
