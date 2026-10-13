<template>
	<div class="page @container flex flex-col gap-6">
		<AlertsOverviewStatsCards :status="filters.status" @update:status="status => setFilters({ status })" />
		<AlertsList :filters @change="setFilters" />
	</div>
</template>

<script setup lang="ts">
import AlertsOverviewStatsCards from "@/components/alerts/AlertsOverviewStatsCards.vue"
import { useAlertsFilters } from "@/components/alerts/filters/useAlertsFilters"
import AlertsList from "@/components/alerts/List.vue"

// One owner for the filters, which live in the URL (#1245): the cards set the status,
// the list's filter bar sets everything.
const { filters, setFilters } = useAlertsFilters()
</script>
