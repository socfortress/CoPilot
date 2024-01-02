<template>
	<div class="users-list">
		<n-spin :show="loadingUsers">
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
								<div class="flex justify-end" v-if="isAdmin">
									<n-dropdown
										trigger="hover"
										:options="options"
										display-directive="show"
										:keyboard="false"
										@click="selectedUser = user.username"
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
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, h } from "vue"
import { useMessage, NTable, NScrollbar, NSpin, NDropdown, NButton } from "naive-ui"
import Api from "@/api"
import type { AuthUser } from "@/types/auth.d"
import ChangePassword from "./ChangePassword.vue"
import { useAuthStore } from "@/stores/auth"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

const DropdownIcon = "carbon:overflow-menu-horizontal"
const message = useMessage()
const loadingUsers = ref(false)
const usersList = ref<AuthUser[]>([])
const isAdmin = useAuthStore().isAdmin
const selectedUser = ref("")

const options = [
	{
		key: "ChangePassword",
		type: "render",
		render: () => h(ChangePassword, { username: selectedUser.value })
	}
]

function getUsers() {
	loadingUsers.value = true

	Api.auth
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
			background-color: var(--primary-005-color);
		}
	}

	.highlight {
		td {
			border-top: 1px solid var(--primary-030-color);
			border-bottom: 1px solid var(--primary-030-color);
			background-color: var(--primary-005-color);
		}
	}
}
</style>
