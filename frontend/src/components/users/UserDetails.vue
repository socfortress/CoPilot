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
import type { AlertTag } from "@/types/tags"
import type { User } from "@/types/user"
import { NCard, NSpin, NTag } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
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

const dFormats = useSettingsStore().dateFormat
const isAdmin = useAuthStore().isAdmin

const loadingCustomers = ref(false)
const loadingTags = ref(false)
const deleting = ref(false)
const customerCodes = ref<string[]>([])
const accessibleTags = ref<AlertTag[]>([])
const tagRbacEnabled = ref(false)

const {
	loading,
	entity: resolvedUser,
	reload: reloadUser
} = useEntityDetails<User, number>({
	entity: () => props.user,
	id: () => props.userId,
	fetch: (id, signal) =>
		Api.users.getUser(id, signal).then(res => ({
			entity: res.data.success ? (res.data.user ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "User not found.",
	errorMessage: "Failed to load user.",
	onLoaded: value => {
		emit("loaded", value)
		loadAccessData(value.id)
	}
})

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

	return Api.auth
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
	// customer access does not depend on the tag settings, only tag access does
	await Promise.all([loadTagSettings(), loadCustomerAccess(userId)])
	loadTagAccess(userId)
}

function reload() {
	const id = resolvedUser.value?.id
	if (id == null) return
	if (props.user) {
		loadAccessData(id)
		return
	}
	reloadUser()
}

function handleDeleted() {
	emit("deleted")
}

watch(
	() => [props.user, props.userId] as const,
	([user, userId]) => {
		if (user) {
			loadAccessData(user.id)
			return
		}

		if (userId == null) {
			customerCodes.value = []
			accessibleTags.value = []
		}
	},
	{ immediate: true }
)

defineExpose({ loading: computed(() => loading.value || deleting.value), resolvedUser, reload })
</script>
