<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'Users' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to users
		</n-button>

		<UserDetails v-if="userId != null" :user-id="userId" @deleted="router.push({ name: 'Users' })" />
		<n-empty v-else description="Invalid user ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import UserDetails from "@/components/users/UserDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const userId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
