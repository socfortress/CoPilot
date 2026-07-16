<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeUser()" />

		<div class="w-full">
			<h1 class="font-display mb-4 text-xl font-semibold">Add a new User</h1>
			<SignUp
				:unavailable-username-list="usernameList"
				:unavailable-email-list="emailList"
				@success="onSuccess"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { User } from "@/types/user"
import { useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const SignUp = defineAsyncComponent(() => import("@/components/auth/SignUp.vue"))

const { routeUser } = useNavigation()
const message = useMessage()
const usersList = ref<User[]>([])

const usernameList = computed(() => usersList.value.map(user => user.username))
const emailList = computed(() => usersList.value.map(user => user.email))

function onSuccess() {
	routeUser().navigate()
}

function getUsers() {
	Api.users
		.getUsers()
		.then(res => {
			if (res.data.success) {
				usersList.value = res.data?.users || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			usersList.value = []
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
}

onBeforeMount(() => {
	getUsers()
})
</script>
