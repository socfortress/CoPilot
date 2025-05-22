<template>
	<n-button :size type="primary" :loading="loading" @click="showForm = true">
		<template v-if="showIcon" #icon>
			<Icon :name="NewCaseIcon" :size="14"></Icon>
		</template>
		<span>Create Case</span>
	</n-button>

	<n-modal
		v-model:show="showForm"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		title="Create a new Case"
		:bordered="false"
		segmented
	>
		<CaseCreationForm
			v-model:loading="loading"
			@mounted="formCTX = $event"
			@submitted="emit('submitted', $event)"
		/>
	</n-modal>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { Case } from "@/types/incidentManagement/cases"
import { NButton, NModal } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import CaseCreationForm from "./CaseCreationForm.vue"

const { showIcon, size } = defineProps<{ showIcon?: boolean; size?: Size }>()

const emit = defineEmits<{
	(e: "submitted", value: Case): void
}>()

const NewCaseIcon = "carbon:fetch-upload-cloud"
const formCTX = ref<{ load: () => void } | null>(null)
const showForm = ref(false)
const loading = ref(false)

watch(showForm, val => {
	if (val) {
		formCTX.value?.load()
	}
})
</script>
