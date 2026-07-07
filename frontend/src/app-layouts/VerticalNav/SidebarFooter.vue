<template>
	<div class="sidebar-footer bg-body flex flex-col gap-4 rounded-lg p-2" :class="{ 'collapsed gap-2!': collapsed }">
		<GlobalCustomerFilter v-if="isLogged" :collapsed />

		<SidebarContextPanel v-if="isLogged" :collapsed />
	</div>
</template>

<script lang="ts" setup>
import { computed } from "vue"
import GlobalCustomerFilter from "@/app-layouts/VerticalNav/GlobalCustomerFilter.vue"
import SidebarContextPanel from "@/app-layouts/VerticalNav/SidebarContextPanel.vue"
import { useAuthStore } from "@/stores/auth"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const authStore = useAuthStore()
const isLogged = computed(() => authStore.isLogged)
</script>
