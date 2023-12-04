<template>
	<div class="soc-users-list">
		<n-spin :show="loading">
			<n-scrollbar x-scrollable style="width: 100%">
				<n-table :bordered="false" class="min-w-max">
					<thead>
						<tr>
							<th>ID</th>
							<th>Login</th>
							<th>Name</th>
							<th>Active</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="user of usersList"
							:key="user.user_id"
							:class="{ highlight: highlight === user.user_id.toString() }"
						>
							<td>
								<div class="flex gap-3 items-center">
									<span>#{{ user.user_id }}</span>
									<n-tooltip trigger="hover">
										<template #trigger>
											<Icon :name="InfoIcon" :size="16" class="cursor-help"></Icon>
										</template>
										{{ user.user_uuid }}
									</n-tooltip>
								</div>
							</td>
							<td>
								{{ user.user_login }}
							</td>
							<td>
								{{ user.user_name }}
							</td>
							<td>
								<strong
									class="active-field"
									:class="{ success: user.user_active, warning: !user.user_active }"
								>
									{{ user.user_active ? "Yes" : "No" }}
								</strong>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-scrollbar>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
// TODO : add alerts by user
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NTable, NTooltip, NScrollbar, NSpin } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import type { SocUser } from "@/types/soc/user.d"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const usersList = ref<SocUser[]>([])

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

<style lang="scss" scoped>
.soc-users-list {
	border-radius: var(--border-radius);
	overflow: hidden;
	.active-field {
		&.success {
			color: var(--success-color);
		}
		&.warning {
			color: var(--warning-color);
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
