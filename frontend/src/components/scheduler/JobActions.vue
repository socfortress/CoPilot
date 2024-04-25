<template>
	<div class="job-actions flex flex-col gap-3" :class="{ '!flex-row': inline }">
		<n-button :size="size" type="success" secondary @click="showForm = true" :loading="loading">
			<div class="flex items-center gap-2">
				<Icon :name="StartIcon" :size="16"></Icon>
				Start
			</div>
		</n-button>
		<div class="flex gap-3">
			<n-button :size="size" type="success" secondary @click="showForm = true" :loading="loading">
				<div class="flex items-center gap-2">
					<Icon :name="RunIcon"></Icon>
					Run once
				</div>
			</n-button>
			<n-button :size="size" secondary @click="showForm = true" :loading="loading">
				<div class="flex items-center gap-2">
					<Icon :name="UpdatedIcon"></Icon>
				</div>
			</n-button>
		</div>
	</div>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Create a Custom Alert"
		:bordered="false"
		segmented
	>
		<CustomAlertForm @mounted="formCTX = $event" v-model:loading="loading" />
	</n-modal>
</template>

<script setup lang="ts">
import { ref, toRefs, watch } from "vue"
import { NButton, NModal } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import CustomAlertForm from "./CustomAlertForm.vue"
import type { Job } from "@/types/scheduler"
import type { Size } from "naive-ui/es/button/src/interface"

const props = defineProps<{ job: Job; size?: Size; inline?: boolean }>()
const { job, size, inline } = toRefs(props)

const StartIcon = "material-symbols:autoplay"
const PauseIcon = "carbon:pause-filled"
const RunIcon = "carbon:play"
const UpdatedIcon = "carbon:settings-adjust"

const formCTX = ref<{ reset: () => void } | null>(null)
const showForm = ref(false)
const loading = ref(false)

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset()
	}
})
</script>
