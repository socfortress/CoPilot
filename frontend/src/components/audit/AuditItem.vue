<template>
	<AuditDetails :entry>
		<template #footerExtra>
			<EntityDetailsButton size="tiny" :order="['open']" open-show-label :url="routeAudit(entry.id).fullUrl()" />
		</template>
	</AuditDetails>
</template>

<script setup lang="ts">
import type { AuditLogEntry } from "@/types/audit"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import AuditDetails from "./AuditDetails.vue"

const { entry } = defineProps<{ entry: AuditLogEntry }>()

const { routeAudit } = useNavigation()
</script>
