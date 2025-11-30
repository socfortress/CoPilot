<template>
	<n-button :size="size" :type="type" :loading="loading" @click="showInvokeWizard = true">
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
		content-class="flex flex-col !p-0"
		segmented
	>
		<ActiveResponseWizard v-model:loading="loading" @mounted="activeResponseWizardCTX = $event" />
	</n-modal>
</template>

<script setup lang="ts">
import type { Size, Type } from "naive-ui/es/button/src/interface"
import { NButton, NModal } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import ActiveResponseWizard from "./ActiveResponseWizard.vue"

const { type, size } = defineProps<{
	size?: Size
	type?: Type
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeWizard = ref(false)
const activeResponseWizardCTX = ref<{ reset: () => void } | null>(null)
const loading = ref(false)

watch(showInvokeWizard, () => {
	activeResponseWizardCTX.value?.reset()
})
</script>
