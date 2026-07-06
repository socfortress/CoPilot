<template>
	<div class="overflow-hidden rounded-lg">
		<div class="mb-4 flex items-center justify-between gap-5">
			<div>
				Total:
				<strong class="font-mono">{{ usersList.length }}</strong>
			</div>
			<div class="flex gap-2">
				<n-button size="small" @click="showTagRbacSettings = true">
					<template #icon>
						<Icon :name="SettingsIcon" />
					</template>
					Tag RBAC Settings
				</n-button>
				<n-button size="small" type="primary" @click="showForm = true">
					<template #icon>
						<Icon :name="UserAddIcon" />
					</template>
					Add User
				</n-button>
			</div>
		</div>

		<n-spin :show="loading" content-class="min-h-32">
			<n-scrollbar x-scrollable class="w-full">
				<n-table class="min-h-50 min-w-max">
					<thead>
						<tr>
							<th>ID</th>
							<th>Username</th>
							<th>Email</th>
							<th>Role</th>
							<th class="max-w-75"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="user of usersList"
							:key="user.id"
							class="group hover:[&_td]:bg-primary/5"
							:class="
								highlight === user.id.toString()
									? '[&_td]:border-primary/30 [&_td]:bg-primary/5 [&_td]:border-y'
									: ''
							"
						>
							<td>#{{ user.id }}</td>
							<td>
								{{ user.username }}
							</td>
							<td>
								{{ user.email }}
							</td>
							<td>
								<n-tag :type="getRoleTagType(user.role_name)" size="small">
									{{ user.role_name || "No Role" }}
								</n-tag>
							</td>
							<td class="max-w-75">
								<div class="flex items-center justify-end gap-2">
									<EntityDetailsButton
										size="tiny"
										:order="['open']"
										open-show-label
										:url="routeUser(user.id).fullUrl()"
										@view="routeUser(user.id).navigate()"
									/>
									<UserDropdown
										v-if="isAdmin"
										:user
										@success="getUsers"
										@loading="updateLoadingDelete"
									/>
								</div>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-scrollbar>
		</n-spin>

		<n-modal
			v-model:show="showTagRbacSettings"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(700px, 90vw)', overflow: 'hidden' }"
			title="Tag RBAC Settings"
			:bordered="false"
			segmented
		>
			<TagRbacSettings />
		</n-modal>

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
import type { ApiError } from "@/types/common"
import type { User } from "@/types/user"
import { NButton, NModal, NScrollbar, NSpin, NTable, NTag, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import UserDropdown from "@/components/users/UserDropdown.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

const { highlight } = defineProps<{ highlight: string | null | undefined }>()
const { routeUser } = useNavigation()
const TagRbacSettings = defineAsyncComponent(() => import("./TagRbacSettings.vue"))
const SignUp = defineAsyncComponent(() => import("@/components/auth/SignUp.vue"))

const UserAddIcon = "carbon:user-follow"
const SettingsIcon = "carbon:settings"
const message = useMessage()
const loadingUsers = ref(false)
const loadingDelete = ref(false)
const showForm = ref(false)
const showTagRbacSettings = ref(false)
const usersList = ref<User[]>([])
const isAdmin = useAuthStore().isAdmin
const loading = computed(() => loadingUsers.value || loadingDelete.value)
const usernameList = computed(() => usersList.value.map(user => user.username))
const emailList = computed(() => usersList.value.map(user => user.email))

function getRoleTagType(roleName: string | null | undefined) {
	switch (roleName?.toLowerCase()) {
		case "admin":
			return "error"
		case "analyst":
			return "warning"
		case "scheduler":
			return "info"
		case "customer_user":
			return "success"
		default:
			return "default"
	}
}

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

			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

onBeforeMount(() => {
	getUsers()
})
</script>
