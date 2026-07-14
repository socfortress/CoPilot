<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeAudit().navigate()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to audit
		</n-button>

		<AuditDetails v-if="entryId != null" :entry-id :embedded="false" />
		<n-empty v-else description="Invalid audit entry ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import AuditDetails from "@/components/audit/AuditDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeAudit } = useNavigation()

const BackIcon = "carbon:arrow-left"

const entryId = useRouteIdParam("id")
</script>
