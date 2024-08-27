<template>
	<div class="customer-notifications-workflows-item" :class="{ embedded }" @click="openForm()">
		<div class="px-4 py-3 flex flex-col gap-1">
			<div class="header-box flex justify-between items-center">
				<div class="label">shuffle_workflow_id</div>
				<div class="status flex gap-2 items-center">
					<span>{{ incidentNotification.enabled ? "Enabled" : "Disabled" }}</span>
					<Icon
						:name="EnabledIcon"
						:size="14"
						class="text-success-color"
						v-if="incidentNotification.enabled"
					></Icon>
					<Icon :name="DisabledIcon" :size="14" class="text-secondary-color" v-else></Icon>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col grow">
					<div class="title">{{ incidentNotification.shuffle_workflow_id }}</div>
				</div>
			</div>
		</div>

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
				:incidentNotification
				:customerCode="incidentNotification.customer_code"
				@mounted="formCTX = $event"
				@submitted="emitUpdate"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref, toRefs, watch } from "vue"
import { NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"

const CustomerNotificationsWorkflowsForm = defineAsyncComponent(
	() => import("./CustomerNotificationsWorkflowsForm.vue")
)

const props = defineProps<{
	incidentNotification: IncidentNotification
	embedded?: boolean
}>()
const { incidentNotification, embedded } = toRefs(props)

const emit = defineEmits<{
	(e: "updated", value: IncidentNotification): void
}>()

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

<style lang="scss" scoped>
.customer-notifications-workflows-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);
	cursor: pointer;

	.header-box {
		font-size: 13px;

		.label {
			font-size: 11px;
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.label {
				color: var(--fg-secondary-color);
				font-size: 11px;
			}
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
