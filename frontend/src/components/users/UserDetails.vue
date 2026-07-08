<template>
	<n-spin :show="loading">
		<div v-if="resolvedUser" class="flex flex-col gap-4">
			<CardEntity embedded>
				<template #headerMain>
					<span class="text-default text-lg font-bold">
						{{ resolvedUser.username }}
					</span>
				</template>
				<template #headerExtra>
					<n-tag :type="roleTagType" size="small">
						{{ resolvedUser.role_name || "No Role" }}
					</n-tag>
				</template>
				<template #default>
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted">
							<template #label>ID</template>
							<template #value>#{{ resolvedUser.id }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Email</template>
							<template #value>{{ resolvedUser.email }}</template>
						</Badge>
						<Badge v-if="resolvedUser.last_login_at" type="splitted">
							<template #label>Last login</template>
							<template #value>
								{{ formatDate(resolvedUser.last_login_at, dFormats.datetime, { tz: true }) }}
							</template>
						</Badge>
						<Badge v-else type="splitted">
							<template #label>Last login</template>
							<template #value>Never</template>
						</Badge>
					</div>
				</template>
			</CardEntity>

			<n-card size="small" title="Customer access" embedded>
				<n-spin :show="loadingCustomers" class="min-h-10">
					<div v-if="customerCodes.length" class="flex flex-wrap gap-2">
						<n-tag v-for="code in customerCodes" :key="code" type="info" size="small">
							{{ code }}
						</n-tag>
					</div>
					<p v-else class="text-secondary text-sm">No customer access assigned</p>
				</n-spin>
			</n-card>

			<n-card size="small" title="Tag access" embedded>
				<n-spin :show="loadingTags" class="min-h-10">
					<template v-if="tagRbacEnabled">
						<div v-if="accessibleTags.length" class="flex flex-wrap gap-2">
							<n-tag v-for="tag in accessibleTags" :key="tag.id" type="info" size="small">
								{{ tag.tag }}
							</n-tag>
						</div>
						<p v-else class="text-secondary text-sm">No restrictions (full access)</p>
					</template>
					<p v-else class="text-secondary text-sm">Tag RBAC is disabled</p>
				</n-spin>
			</n-card>

			<n-card v-if="isAdmin" size="small" title="Actions" embedded>
				<div class="flex flex-col gap-1">
					<AssignRole :user="resolvedUser" @success="reload" />
					<AssignCustomer :user="resolvedUser" @success="reload" />
					<AssignTags :user="resolvedUser" @success="reload" />
					<ChangePassword :user="resolvedUser" quaternary class-name="w-full! justify-start!" />
					<DeleteUser :user="resolvedUser" @success="handleDeleted" @loading="deleting = $event" />
				</div>
			</n-card>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AlertTag } from "@/types/tags"
import type { User } from "@/types/user"
import axios from "axios"
import { NCard, NSpin, NTag, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	user?: User | null
	userId?: number | null
}>()

const emit = defineEmits<{
	(e: "loaded", value: User): void
	(e: "deleted"): void
}>()

const AssignRole = defineAsyncComponent(() => import("./AssignRole.vue"))
const AssignCustomer = defineAsyncComponent(() => import("./AssignCustomer.vue"))
const AssignTags = defineAsyncComponent(() => import("./AssignTags.vue"))
const ChangePassword = defineAsyncComponent(() => import("./ChangePassword.vue"))
const DeleteUser = defineAsyncComponent(() => import("./DeleteUser.vue"))

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = useAuthStore().isAdmin

const loading = ref(false)
const loadingCustomers = ref(false)
const loadingTags = ref(false)
const deleting = ref(false)
const fetchedUser = ref<User | null>(null)
const customerCodes = ref<string[]>([])
const accessibleTags = ref<AlertTag[]>([])
const tagRbacEnabled = ref(false)

let abortController: AbortController | null = null

const resolvedUser = computed(() => props.user ?? fetchedUser.value)

const roleTagType = computed(() => {
	switch (resolvedUser.value?.role_name?.toLowerCase()) {
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
})

function loadUser(userId: number) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.users
		.getUser(userId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.user) {
				fetchedUser.value = res.data.user
				emit("loaded", res.data.user)
				loadAccessData(res.data.user.id)
			} else {
				message.warning(res.data?.message || "User not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load user.")
				loading.value = false
			}
		})
}

async function loadTagSettings() {
	try {
		const res = await Api.tagRbac.getSettings()
		if (res.data.success && res.data.settings) {
			tagRbacEnabled.value = res.data.settings.enabled
		}
	} catch {
		tagRbacEnabled.value = false
	}
}

function loadCustomerAccess(userId: number) {
	loadingCustomers.value = true

	Api.auth
		.getUserCustomerAccess(userId)
		.then(res => {
			if (res.data.success) {
				customerCodes.value = res.data.customer_codes || []
			}
		})
		.catch(() => {
			customerCodes.value = []
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function loadTagAccess(userId: number) {
	if (!tagRbacEnabled.value) {
		accessibleTags.value = []
		return
	}

	loadingTags.value = true

	Api.tagRbac
		.getUserTags(userId)
		.then(res => {
			if (res.data.success) {
				accessibleTags.value = res.data.accessible_tags || []
			}
		})
		.catch(() => {
			accessibleTags.value = []
		})
		.finally(() => {
			loadingTags.value = false
		})
}

async function loadAccessData(userId: number) {
	await loadTagSettings()
	loadCustomerAccess(userId)
	loadTagAccess(userId)
}

function reload() {
	const id = resolvedUser.value?.id
	if (id == null) return
	if (props.user) {
		loadAccessData(id)
		return
	}
	loadUser(id)
}

function handleDeleted() {
	emit("deleted")
}

watch(
	() => [props.user, props.userId] as const,
	([user, userId]) => {
		if (user) {
			abortController?.abort()
			fetchedUser.value = null
			loading.value = false
			loadAccessData(user.id)
			return
		}

		if (userId != null) {
			loadUser(userId)
			return
		}

		abortController?.abort()
		fetchedUser.value = null
		customerCodes.value = []
		accessibleTags.value = []
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading: computed(() => loading.value || deleting.value), resolvedUser, reload })
</script>
