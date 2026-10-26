<template>
	<n-card :title="$t('auth.changePassword.title')">
		<p class="text-secondary mb-4">{{ $t("auth.changePassword.description") }}</p>
		<n-button type="primary" :loading @click="openChangePasswordModal">
			{{ $t("auth.changePassword.title") }}
		</n-button>
		<ChangePasswordModal v-model:open="showChangePasswordModal" v-model:loading="loading" />
	</n-card>
</template>

<script lang="ts" setup>
import { NButton, NCard } from "naive-ui"
import { ref } from "vue"
import ChangePasswordModal from "@/components/auth/ChangePasswordModal.vue"

const showChangePasswordModal = ref(false)
const loading = ref(false)

function openChangePasswordModal() {
	showChangePasswordModal.value = true
}
</script>
