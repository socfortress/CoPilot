<template>
	<n-popselect
		v-model:value="userSelected"
		v-model:show="ownerListVisible"
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
import type { SocAlert } from "@/types/soc/alert.d"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import { useMessage, NPopselect } from "naive-ui"
import type { SocUser } from "@/types/soc/user.d"
import { watch } from "vue"

const props = defineProps<{
	alert: SocAlert
	users?: SocUser[]
}>()
const { alert, users } = toRefs(props)

const emit = defineEmits<{
	(e: "updated", value: SocAlert): void
}>()

const loadingUsers = ref(false)
const message = useMessage()

const ownerListVisible = ref(false)
const ownerId = computed(() => alert.value.owner?.id)
const usersOptions = ref<
	{
		label: string
		value: number
	}[]
>([])
const userSelected = ref<number | null>(null)

function getUsers() {
	loadingUsers.value = true

	Api.soc
		.getUsers()
		.then(res => {
			if (res.data.success) {
				const usersList = res.data?.users || []
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
	if (userSelected.value !== ownerId.value) {
		loadingUsers.value = true

		const method = userSelected.value ? "assignUserToAlert" : "removeUserAlertAssign"
		const userId = userSelected.value ? userSelected.value : ownerId.value || 0

		Api.soc[method](alert.value.alert_id.toString(), userId.toString())
			.then(res => {
				if (res.data.success) {
					emit("updated", res.data.alert)
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

function parseUsers(users: SocUser[]) {
	usersOptions.value = users.map(o => ({ label: "#" + o.user_id + " • " + o.user_login, value: o.user_id }))

	usersOptions.value.push({
		label: "- Set default owner -",
		value: 0
	})
}

watch(
	() => users?.value,
	val => {
		if (val !== undefined && val.length) {
			parseUsers(val)
		}
	}
)

watch(userSelected, () => {
	assignUser()
})

watch(ownerListVisible, val => {
	if (val && !usersOptions.value.length) {
		getUsers()
	}
})

onBeforeMount(() => {
	if (ownerId.value) {
		userSelected.value = ownerId.value
	}

	if (users?.value?.length) {
		parseUsers(users.value)
	}
})
</script>
