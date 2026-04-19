<template>
	<div>
		<n-button type="primary" :secondary :size @click="showModal = true">
			<template #icon>
				<Icon name="carbon:add" />
			</template>
			Create case
		</n-button>

		<n-modal
			v-model:show="showModal"
			title="Create Case"
			preset="card"
			display-directive="show"
			class="w-[90vw]! max-w-160!"
			segmented
		>
			<CreateCaseForm @success="handleSuccess" @cancel="showModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import { NButton, NModal } from "naive-ui"
import { ref } from "vue"
import CreateCaseForm from "@/components/cases/CreateCaseForm.vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	secondary?: boolean
	size?: ButtonSize
}>()

const emit = defineEmits<{
	(e: "success"): void
}>()

const showModal = ref(false)

function handleSuccess() {
	showModal.value = false
	emit("success")
}
</script>
