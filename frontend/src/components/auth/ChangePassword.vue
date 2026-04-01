<template>
	<n-card title="Change Password">
		<p class="text-secondary mb-4">Update your account password to keep your profile secure.</p>
		<ChangePassword :user="{ username: userName, id: 0, email: '' }" type="primary" />
	</n-card>
</template>

<script lang="ts" setup>
import { NCard } from "naive-ui"
import ChangePassword from "@/components/users/ChangePassword.vue"
import { useAuthStore } from "@/stores/auth"

const authStore = useAuthStore()

const userName = authStore.userName
</script>
