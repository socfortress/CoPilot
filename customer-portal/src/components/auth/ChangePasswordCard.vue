<template>
	<n-card title="Change Password">
		<p class="text-secondary mb-4">Update your account password to keep your profile secure.</p>
		<n-button type="primary" :loading @click="openChangePasswordModal">Change Password</n-button>
		<ChangePasswordModal v-model:open="showChangePasswordModal" v-model:loading="loading" />
	</n-card>
</template>

<script lang="ts" setup>
import { NButton, NCard } from "naive-ui"
import { ref } from "vue"
import ChangePasswordModal from "@/components/ChangePasswordModal.vue"

const showChangePasswordModal = ref(false)
const loading = ref(false)

function openChangePasswordModal() {
	showChangePasswordModal.value = true
}
</script>
