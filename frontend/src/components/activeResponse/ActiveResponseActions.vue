<template>
	<div class="active-response-actions flex gap-2 justify-end">
		<n-button type="success" secondary :size="size" @click="showInvokeForm = true" :loading="loadingInvoke">
			<template #icon><Icon :name="InvokeIcon"></Icon></template>
			Invoke Action
		</n-button>

		<n-modal
			v-model:show="showInvokeForm"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			:title="activeResponse.name"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<ActiveResponseInvokeForm
				:activeResponse="activeResponse"
				:agentId="agentId"
				@close="showInvokeForm = false"
				@submitted="showInvokeForm = false"
				@startLoading="loadingInvoke = true"
				@stopLoading="loadingInvoke = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { computed, ref } from "vue"
import { watch } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse"
import ActiveResponseInvokeForm from "./ActiveResponseInvokeForm.vue"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const { activeResponse, size, agentId } = defineProps<{
	activeResponse: SupportedActiveResponse
	agentId?: string | number
	size?: "tiny" | "small" | "medium" | "large"
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeForm = ref(false)

const loadingInvoke = ref(false)
const loading = computed(() => loadingInvoke.value)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})
</script>
