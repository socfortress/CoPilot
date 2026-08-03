<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create a template" :back-route="routeMessageTemplates()" />

		<!--
			Same form the list page opens inline — a template written here and one
			written there must not be able to differ.
		-->
		<n-card size="small">
			<NotificationTemplateForm @submitted="onSubmitted()" @close="goBack(routeMessageTemplates())" />
		</n-card>
	</div>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import NotificationTemplateForm from "@/components/notifications/NotificationTemplateForm.vue"
import { useNavigation } from "@/composables/useNavigation"

// The form already reports the outcome, so this only decides where to land.

const { goBack, routeMessageTemplates } = useNavigation()

function onSubmitted() {
	// `replace`, so browser-back doesn't return to a form for a template that
	// now exists — the list is where the operator continues from.
	routeMessageTemplates().replace()
}
</script>
