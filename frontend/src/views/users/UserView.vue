<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeUser()" />

		<UserDetails v-if="userId != null" :user-id @deleted="routeUser().navigate()" />
		<n-empty v-else description="Invalid user ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import UserDetails from "@/components/users/UserDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeUser } = useNavigation()

const userId = useRouteIdParam("id")
</script>
