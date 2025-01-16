<template>
	<div class="users-list">
		<div class="mb-4 flex items-center justify-between gap-5">
			<div>
				Total:
				<strong class="font-mono">{{ usersList.length }}</strong>
			</div>
			<div>
				<n-button size="small" type="primary" @click="showForm = true">
					<template #icon>
						<Icon :name="UserAddIcon"></Icon>
					</template>
					Add User
				</n-button>
			</div>
		</div>

		<n-spin :show="loading" content-class="min-h-32">
			<n-scrollbar x-scrollable style="width: 100%">
				<n-table :bordered="false" class="min-w-max">
					<thead>
						<tr>
							<th>ID</th>
							<th>Username</th>
							<th>Email</th>
							<th style="max-width: 300px"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="user of usersList"
							:key="user.id"
							:class="{ highlight: highlight === user.id.toString() }"
						>
							<td>#{{ user.id }}</td>
							<td>
								{{ user.username }}
							</td>
							<td>
								{{ user.email }}
							</td>
							<td style="max-width: 300px">
								<div v-if="isAdmin" class="flex justify-end">
									<n-dropdown
										trigger="click"
										:options
										to="body"
										display-directive="show"
										:keyboard="false"
										@click="selectedUser = user"
									>
										<n-button text>
											<template #icon>
												<Icon :name="DropdownIcon" :size="24"></Icon>
											</template>
										</n-button>
									</n-dropdown>
								</div>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-scrollbar>
		</n-spin>

		<n-modal
			v-model:show="showForm"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			title="Add a new User"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<SignUp
				:unavailable-username-list="usernameList"
				:unavailable-email-list="emailList"
				@success="addUserSuccess()"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { User } from "@/types/user.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { NButton, NDropdown, NModal, NScrollbar, NSpin, NTable, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, h, onBeforeMount, ref } from "vue"

const { highlight } = defineProps<{ highlight: string | null | undefined }>()
const ChangePassword = defineAsyncComponent(() => import("./ChangePassword.vue"))
const DeleteUser = defineAsyncComponent(() => import("./DeleteUser.vue"))
const SignUp = defineAsyncComponent(() => import("@/components/auth/SignUp.vue"))

const UserAddIcon = "carbon:user-follow"
const DropdownIcon = "carbon:overflow-menu-horizontal"
const message = useMessage()
const loadingUsers = ref(false)
const loadingDelete = ref(false)
const showForm = ref(false)
const usersList = ref<User[]>([])
const isAdmin = useAuthStore().isAdmin
const selectedUser = ref<User | null>(null)
const loading = computed(() => loadingUsers.value || loadingDelete.value)
const usernameList = computed(() => usersList.value.map(user => user.username))
const emailList = computed(() => usersList.value.map(user => user.email))

const options = [
	{
		key: "ChangePassword",
		type: "render",
		render: () => h(ChangePassword, { user: selectedUser.value || undefined })
	},
	{
		key: "DeleteUser",
		type: "render",
		render: () =>
			h(DeleteUser, {
				user: selectedUser.value || undefined,
				onSuccess: getUsers,
				onLoading: updateLoadingDelete
			})
	}
]

function updateLoadingDelete(value: boolean) {
	loadingDelete.value = value
}

function addUserSuccess() {
	getUsers()
	showForm.value = false
}

function getUsers() {
	loadingUsers.value = true

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

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

onBeforeMount(() => {
	getUsers()
})
</script>

<style lang="scss" scoped>
.users-list {
	border-radius: var(--border-radius);
	overflow: hidden;

	tr:hover {
		td {
			background-color: rgba(var(--primary-color-rgb) / 0.05);
		}
	}

	.highlight {
		td {
			border-top: 1px solid rgba(var(--primary-color-rgb) / 0.3);
			border-bottom: 1px solid rgba(var(--primary-color-rgb) / 0.3);
			background-color: rgba(var(--primary-color-rgb) / 0.05);
		}
	}
}
</style>
