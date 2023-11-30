<template>
	<div class="soc-users-list">
		<n-data-table :columns="columns" :data="usersList" :bordered="false" :loading="loading" />
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NDataTable } from "naive-ui"
import Api from "@/api"
import type { SocUser } from "@/types/soc/user.d"

const message = useMessage()
const loading = ref(false)
const usersList = ref<SocUser[]>([])

const columns = [
	{
		title: "ID",
		key: "user_id"
	},
	{
		title: "Login",
		key: "user_login"
	},
	{
		title: "Name",
		key: "user_name"
	},
	{
		title: "UUID",
		key: "user_uuid"
	},
	{
		title: "Active",
		key: "user_active"
	}
]

function getData() {
	loading.value = true

	Api.soc
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

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
