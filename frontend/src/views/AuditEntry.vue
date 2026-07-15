<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAudit()" />

		<AuditDetails v-if="entryId != null" :entry-id :embedded="false" />
		<n-empty v-else description="Invalid audit entry ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import AuditDetails from "@/components/audit/AuditDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeAudit } = useNavigation()

const entryId = useRouteIdParam("id")
</script>
