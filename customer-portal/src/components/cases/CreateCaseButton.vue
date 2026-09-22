<template>
	<div>
		<n-button type="primary" :secondary :size @click="openModal()">
			<template #icon>
				<Icon name="carbon:add" />
			</template>
			Create case
		</n-button>

		<!--
			`show` keeps the form mounted while the modal is closed, so a create request still
			in flight when the user dismisses the modal can complete and emit `success`. The
			form is reset on every open instead, so it re-seeds its customer from the current
			global filter and never carries a previous case's fields.
		-->
		<n-modal
			v-model:show="showModal"
			title="Create Case"
			preset="card"
			display-directive="show"
			class="w-[90vw]! max-w-160!"
			segmented
		>
			<CreateCaseForm ref="formRef" @success="handleSuccess" @cancel="showModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import { NButton, NModal } from "naive-ui"
import { ref, useTemplateRef } from "vue"
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
const formRef = useTemplateRef<InstanceType<typeof CreateCaseForm>>("formRef")

function openModal() {
	// Null on the very first open (the modal body is mounted lazily) — the form seeds
	// itself in setup in that case.
	formRef.value?.reset()
	showModal.value = true
}

function handleSuccess() {
	showModal.value = false
	emit("success")
}
</script>
