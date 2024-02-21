<template>
	<n-button :size="size" :type="type" @click="showInvokeWizard = true">
		<template #icon><Icon :name="InvokeIcon"></Icon></template>
		Active Response
	</n-button>

	<n-modal
		v-model:show="showInvokeWizard"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Active Response Wizard"
		:bordered="false"
		content-style="padding:0"
		content-class="flex flex-col"
		segmented
	>
		<ActiveResponseWizard />
	</n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import ActiveResponseWizard from "./ActiveResponseWizard.vue"

const { type, size } = defineProps<{
	size?: "tiny" | "small" | "medium" | "large"
	type?: "default" | "tertiary" | "primary" | "info" | "success" | "warning" | "error"
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeWizard = ref(false)
// const threatIntelCTX = ref<{ restore: () => void } | null>(null)

watch(showInvokeWizard, () => {
	// threatIntelCTX.value?.restore()
})
</script>
