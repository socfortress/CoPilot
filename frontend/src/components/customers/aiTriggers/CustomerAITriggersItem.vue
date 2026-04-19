<template>
	<div>
		<CardEntity :embedded clickable hoverable @click.stop="openForm()">
			<template #headerMain>AI Trigger</template>
			<template #headerExtra>
				<div class="flex items-center gap-2">
					<span :class="{ 'text-default': aiTrigger.enabled }">
						{{ aiTrigger.enabled ? "Enabled" : "Disabled" }}
					</span>
					<Icon v-if="aiTrigger.enabled" :name="EnabledIcon" :size="14" class="text-success" />
					<Icon v-else :name="DisabledIcon" :size="14" class="text-secondary" />
				</div>
			</template>
			<template #default>
				{{ aiTrigger.customer_code }}
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showForm"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			title="AI Trigger"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<CustomerAITriggersForm
				:ai-trigger
				:customer-code="aiTrigger.customer_code"
				@mounted="formCTX = $event"
				@submitted="emitUpdate"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AITrigger } from "@/types/incidentManagement/aiTriggers.d"
import { NModal } from "naive-ui"
import { defineAsyncComponent, ref, toRefs, watch } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	aiTrigger: AITrigger
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "updated", value: AITrigger): void
}>()

const CustomerAITriggersForm = defineAsyncComponent(() => import("./CustomerAITriggersForm.vue"))

const { aiTrigger } = toRefs(props)

const EnabledIcon = "carbon:circle-solid"
const DisabledIcon = "carbon:subtract-alt"

const formCTX = ref<{ reset: (aiTrigger?: AITrigger) => void } | null>(null)
const showForm = ref(false)

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset(aiTrigger.value)
	}
})

function openForm() {
	showForm.value = true
}

function emitUpdate(aiTrigger: AITrigger) {
	emit("updated", aiTrigger)
}
</script>
