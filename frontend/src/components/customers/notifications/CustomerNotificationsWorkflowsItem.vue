<template>
	<div>
		<CardEntity :embedded clickable hoverable @click.stop="openForm()">
			<template #headerMain>shuffle_workflow_id</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<span :class="{ 'text-default': incidentNotification.enabled }">
						{{ incidentNotification.enabled ? "Enabled" : "Disabled" }}
					</span>
					<Icon
						v-if="incidentNotification.enabled"
						:name="EnabledIcon"
						:size="14"
						class="text-success"
					></Icon>
					<Icon v-else :name="DisabledIcon" :size="14" class="text-secondary"></Icon>
				</div>
			</template>
			<template #default>
				{{ incidentNotification.shuffle_workflow_id }}
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showForm"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			title="Notification"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<CustomerNotificationsWorkflowsForm
				:incident-notification
				:customer-code="incidentNotification.customer_code"
				@mounted="formCTX = $event"
				@submitted="emitUpdate"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"
import { NModal } from "naive-ui"
import { defineAsyncComponent, ref, toRefs, watch } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	incidentNotification: IncidentNotification
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "updated", value: IncidentNotification): void
}>()

const CustomerNotificationsWorkflowsForm = defineAsyncComponent(
	() => import("./CustomerNotificationsWorkflowsForm.vue")
)

const { incidentNotification, embedded } = toRefs(props)

const EnabledIcon = "carbon:circle-solid"
const DisabledIcon = "carbon:subtract-alt"

const formCTX = ref<{ reset: (incidentNotification?: IncidentNotification) => void } | null>(null)
const showForm = ref(false)

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset(incidentNotification.value)
	}
})

function openForm() {
	showForm.value = true
}

function emitUpdate(incidentNotification: IncidentNotification) {
	emit("updated", incidentNotification)
}
</script>
