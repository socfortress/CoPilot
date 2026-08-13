<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="template?.name" :back-route="routeMessageTemplates()">
			<template v-if="template" #meta>
				<span class="text-secondary font-mono text-sm">#{{ template.id }}</span>
				<Badge v-if="template.is_default" type="splitted" size="small">
					<template #label>built-in</template>
					<template #value>read-only</template>
				</Badge>
			</template>
		</DetailPageHeader>

		<NotificationTemplateOverview
			v-if="templateId != null"
			:key="templateId"
			:template-id
			full-width
			@loaded="template = $event"
			@deleted="routeMessageTemplates().navigate()"
			@duplicate="routeMessageTemplates({ duplicate: $event.id }).navigate()"
		/>
		<n-empty v-else description="Invalid template ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { NotificationTemplate } from "@/types/notifications"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Badge from "@/components/common/Badge.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import NotificationTemplateOverview from "@/components/notifications/NotificationTemplateOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

// Duplicating hands off to the list: the copy is an unsaved template, and the
// creation form lives there — a detail page for a row that doesn't exist yet
// would have nothing to be the detail of.

const { routeMessageTemplates } = useNavigation()

const template = ref<NotificationTemplate | null>(null)

const templateId = useRouteIdParam("id")

watch(templateId, () => {
	template.value = null
})
</script>
