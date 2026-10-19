<template>
	<n-modal
		v-model:show="isOpen"
		preset="card"
		display-directive="show"
		class="w-[90vw]! max-w-133!"
		segmented
		title="Change Password"
	>
		<ChangePasswordForm ref="form" v-model:loading="loading" @cancel="closeModal" @success="succeeded" />
	</n-modal>
</template>

<script setup lang="ts">
import { NModal } from "naive-ui"
import { useTemplateRef } from "vue"
import ChangePasswordForm from "./ChangePasswordForm.vue"

const emit = defineEmits<{
	(e: "close"): void
	(e: "success"): void
}>()

const isOpen = defineModel<boolean>("open", { default: false })
const loading = defineModel<boolean>("loading", { default: false })
const form = useTemplateRef<InstanceType<typeof ChangePasswordForm>>("form")

function closeModal() {
	if (!loading.value) {
		form.value?.reset()
		isOpen.value = false
		emit("close")
	}
}

function succeeded() {
	emit("success")
	closeModal()
}
</script>
