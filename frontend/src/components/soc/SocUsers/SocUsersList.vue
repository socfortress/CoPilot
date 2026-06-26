<template>
	<div class="overflow-hidden rounded-lg">
		<n-spin :show="loadingUsers">
			<n-scrollbar x-scrollable style="width: 100%">
				<n-table :bordered="false" class="min-w-max">
					<thead>
						<tr>
							<th>ID</th>
							<th>Login</th>
							<th>Name</th>
							<th>Active</th>
							<th style="max-width: 300px">Alerts</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="user of usersList"
							:key="user.user_id"
							class="group hover:[&_td]:bg-primary/5"
							:class="
								highlight === user.user_id.toString()
									? '[&_td]:border-y [&_td]:border-primary/30 [&_td]:bg-primary/5'
									: ''
							"
						>
							<td>
								<div class="flex items-center gap-3">
									<span>#{{ user.user_id }}</span>
									<n-tooltip trigger="hover">
										<template #trigger>
											<Icon :name="InfoIcon" :size="16" class="cursor-help" />
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
								<strong :class="user.user_active ? 'text-success' : 'text-warning'">
									{{ user.user_active ? "Yes" : "No" }}
								</strong>
							</td>
							<td style="max-width: 300px">
								<SocUserAlerts :user-id="user.user_id" />
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-scrollbar>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SocAlert } from "@/types/soc/alert"
import type { SocUser } from "@/types/soc/user"
import { NScrollbar, NSpin, NTable, NTooltip, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import SocUserAlerts from "./SocUserAlerts.vue"

const props = defineProps<{ highlight: string | null | undefined }>()
const { highlight } = toRefs(props)

const InfoIcon = "carbon:information"

const message = useMessage()
const loadingAlerts = ref(false)
const loadingUsers = ref(false)
const usersList = ref<SocUser[]>([])
const alertsList = ref<SocAlert[]>([])

function getUsers() {
	loadingUsers.value = true

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

			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

function getAlerts() {
	loadingAlerts.value = true

	Api.soc
		.getAlerts({})
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

onBeforeMount(() => {
	getUsers()
	getAlerts()
})
</script>
