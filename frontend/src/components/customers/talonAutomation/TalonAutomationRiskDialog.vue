<template>
	<n-modal
		:show
		preset="card"
		:title="`Raise level ${levelsText} for ${customerCode}`"
		class="max-w-xl"
		:mask-closable="!saving"
		:closable="!saving"
		data-testid="automation-risk-dialog"
		@update:show="value => !value && emit('cancel')"
	>
		<div class="flex flex-col gap-4">
			<n-alert type="warning" :bordered="false" title="The honest risk">
				<div class="flex flex-col gap-2 text-sm" data-testid="automation-risk-text">
					<p v-for="paragraph of HONEST_RISK_TEXT" :key="paragraph">{{ paragraph }}</p>
				</div>
			</n-alert>
			<n-checkbox v-model:checked="acknowledged" :disabled="saving" data-testid="automation-risk-ack">
				I understand this risk and raise level {{ levelsText }} for {{ customerCode }}.
			</n-checkbox>
			<div class="flex justify-end gap-2">
				<n-button size="small" :disabled="saving" data-testid="automation-risk-cancel" @click="emit('cancel')">
					Cancel
				</n-button>
				<n-button
					size="small"
					type="warning"
					:disabled="!acknowledged"
					:loading="saving"
					data-testid="automation-risk-confirm"
					@click="acknowledged && emit('confirm')"
				>
					Acknowledge and save
				</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
// The confirm before raising level 3 or 4 (plan Q7: one admin, after acknowledging the honest
// risk). Saving is offered only once the box is ticked; the parent then sends `acknowledge_risk: true`.
import type { TalonAutomationLevel } from "@/api/endpoints/talonAutomation"
import { NAlert, NButton, NCheckbox, NModal } from "naive-ui"
import { computed, ref, watch } from "vue"
import { HONEST_RISK_TEXT } from "./automation"

const props = defineProps<{
	show: boolean
	customerCode: string
	levels: TalonAutomationLevel[]
	saving?: boolean
}>()

const emit = defineEmits<{
	(e: "confirm"): void
	(e: "cancel"): void
}>()

const acknowledged = ref(false)
// Every opening asks again.
watch(
	() => props.show,
	() => {
		acknowledged.value = false
	}
)

const levelsText = computed(() => props.levels.join(" and "))
</script>
