<template>
	<n-popselect
		v-model:value="userSelected"
		v-model:show="usersListVisible"
		:options="usersOptions"
		:disabled="loadingUsers"
		size="medium"
		scrollable
		to="body"
	>
		<slot :loading="loadingUsers" />
	</n-popselect>
</template>

<script setup lang="ts">
import type { Ref } from "vue"
import type { Case } from "@/types/incidentManagement/cases.d"
import { NPopselect, useMessage } from "naive-ui"
import { computed, inject, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	caseData: Case
}>()
const emit = defineEmits<{
	(e: "updated", value: Case): void
}>()

const { caseData } = toRefs(props)

const loadingUsers = ref(false)
const users = inject<Ref<string[]>>("assignable-users", ref([]))
const message = useMessage()
const usersListVisible = ref(false)
const assignedTo = computed(() => caseData.value.assigned_to)
const usersOptions = ref<
	{
		label: string
		value: string
	}[]
>([])
const userSelected = ref<string | null>(null)

function getUsers() {
	loadingUsers.value = true

	Api.incidentManagement.alerts
		.getAvailableUsers()
		.then(res => {
			if (res.data.success) {
				const usersList = res.data?.available_users || []
				parseUsers(usersList)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

function assignUser() {
	if (userSelected.value && userSelected.value !== assignedTo.value) {
		loadingUsers.value = true

		Api.incidentManagement.cases
			.updateCaseAssignedUser(caseData.value.id, userSelected.value)
			.then(res => {
				if (res.data.success) {
					emit("updated", { ...caseData.value, assigned_to: userSelected.value })
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingUsers.value = false
			})
	}
}

function parseUsers(users: string[]) {
	usersOptions.value = users.map(o => ({ label: o, value: o }))
}

watch(users, val => {
	if (val !== undefined && val.length) {
		parseUsers(val)
	}
})

watch(userSelected, () => {
	assignUser()
})

watch(usersListVisible, val => {
	if (val && !usersOptions.value.length) {
		getUsers()
	}
})

onBeforeMount(() => {
	if (assignedTo.value) {
		userSelected.value = assignedTo.value
	}

	if (users.value.length) {
		parseUsers(users.value)
	}
})
</script>
