<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeUser().navigate()">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to users
		</n-button>

		<UserDetails v-if="userId != null" :user-id @deleted="routeUser().navigate()" />
		<n-empty v-else description="Invalid user ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import UserDetails from "@/components/users/UserDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeUser } = useNavigation()

const BackIcon = "carbon:arrow-left"

const userId = useRouteIdParam("id")
</script>
