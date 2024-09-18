<template>
	<div class="active-response-actions flex gap-2 justify-end">
		<n-button type="success" secondary :size="size" :loading="loadingInvoke" @click="showInvokeForm = true">
			<template #icon>
				<Icon :name="InvokeIcon"></Icon>
			</template>
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
				:active-response="activeResponse"
				:agent-id="agentId"
				@mounted="activeResponseInvokeFormCTX = $event"
				@submitted="close()"
				@start-loading="loadingInvoke = true"
				@stop-loading="loadingInvoke = false"
			>
				<template #additionalActions>
					<n-button secondary @click="close()">Close</n-button>
				</template>
			</ActiveResponseInvokeForm>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SupportedActiveResponse } from "@/types/activeResponse.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal } from "naive-ui"
import { computed, ref, watch } from "vue"
import ActiveResponseInvokeForm from "./ActiveResponseInvokeForm.vue"

const { activeResponse, size, agentId } = defineProps<{
	activeResponse: SupportedActiveResponse
	agentId?: string | number
	size?: Size
}>()

const emit = defineEmits<{
	(e: "startLoading"): void
	(e: "stopLoading"): void
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
