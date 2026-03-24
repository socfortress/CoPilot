<template>
	<n-button :size :type :secondary :loading @click="openModal">
		<template #icon>
			<Icon :name="InvokeIcon" />
		</template>
		Active Response
	</n-button>

	<n-modal
		v-model:show="showInvokeWizard"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Active Response Wizard"
		:bordered="false"
		content-class="flex flex-col p-0!"
		segmented
	>
		<ActiveResponseWizard v-model:loading="loading" @mounted="activeResponseWizardCTX = $event" />
	</n-modal>
</template>

<script setup lang="ts">
import type { ButtonSize, ButtonType } from "naive-ui"
import { NButton, NModal } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import ActiveResponseWizard from "./ActiveResponseWizard.vue"

defineProps<{
	size?: ButtonSize
	type?: ButtonType
	secondary?: boolean
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeWizard = ref(false)
const activeResponseWizardCTX = ref<{ reset: () => void } | null>(null)
const loading = ref(false)

function openModal() {
	showInvokeWizard.value = true
}

function closeModal() {
	showInvokeWizard.value = false
}

watch(showInvokeWizard, () => {
	activeResponseWizardCTX.value?.reset()
})

defineExpose({
	openModal,
	closeModal
})
</script>
