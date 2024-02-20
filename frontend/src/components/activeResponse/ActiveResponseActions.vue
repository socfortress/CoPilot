<template>
	<div class="active-response-actions flex gap-2 justify-end">
		<n-button type="success" secondary :size="size" @click="showInvokeWizard = true">
			<template #icon><Icon :name="InvokeIcon"></Icon></template>
			Invoke Wizard
		</n-button>

		<n-modal
			v-model:show="showInvokeWizard"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="activeResponse.name"
			:bordered="false"
			segmented
		>
			showInvokeWizard
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { computed, ref } from "vue"
import { watch } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const { activeResponse, size } = defineProps<{
	activeResponse: SupportedActiveResponse
	agentId?: string | number
	size?: "tiny" | "small" | "medium" | "large"
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeWizard = ref(false)

const loadingInvoke = ref(false)
const loading = computed(() => loadingInvoke.value)

watch(loading, val => {
	emit(val ? "startLoading" : "startLoading")
})
</script>
