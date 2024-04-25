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
				@mounted="activeResponseInvokeFormCTX = $event"
				@submitted="close()"
				@startLoading="loadingInvoke = true"
				@stopLoading="loadingInvoke = false"
			>
				<template #additionalActions>
					<n-button @click="close()" secondary>Close</n-button>
				</template>
			</ActiveResponseInvokeForm>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { computed, ref } from "vue"
import { watch } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse.d"
import ActiveResponseInvokeForm from "./ActiveResponseInvokeForm.vue"
import type { Size } from "naive-ui/es/button/src/interface"

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
}>()

const { activeResponse, size, agentId } = defineProps<{
	activeResponse: SupportedActiveResponse
	agentId?: string | number
	size?: Size
}>()

const InvokeIcon = "solar:playback-speed-outline"
const showInvokeForm = ref(false)
const loadingInvoke = ref(false)
const loading = computed(() => loadingInvoke.value)
const activeResponseInvokeFormCTX = ref<{ reset: () => void } | null>(null)

watch(loading, val => {
	if (val) {
		emit("startLoading")
	} else {
		emit("stopLoading")
	}
})

function close() {
	activeResponseInvokeFormCTX.value?.reset()
	showInvokeForm.value = false
}
</script>
