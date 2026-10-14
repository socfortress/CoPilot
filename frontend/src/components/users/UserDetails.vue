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
					<n-tag :type="roleTagType(resolvedUser.role_name)" size="small">
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
					<p v-if="!accessReadable" class="text-secondary text-sm" data-testid="user-access-hidden">
						{{ ACCESS_HIDDEN }}
					</p>
					<div v-else-if="customerCodes.length" class="flex flex-wrap gap-2">
						<n-tag v-for="code in customerCodes" :key="code" type="info" size="small">
							{{ code }}
						</n-tag>
					</div>
					<p v-else-if="seesEveryCustomer(resolvedUser.role_name)" class="text-secondary text-sm">
						Admins see every customer.
					</p>
					<p
						v-else-if="needsCustomers(resolvedUser.role_name)"
						class="text-warning text-sm"
						data-testid="user-no-customers"
					>
						No customer assigned: this user sees nothing. {{ NEEDS_A_CUSTOMER }}
					</p>
					<p v-else class="text-secondary text-sm">No customer access assigned</p>
				</n-spin>
			</n-card>

			<n-card size="small" title="Tag access" embedded>
				<n-spin :show="loadingTags" class="min-h-10">
					<p v-if="!accessReadable" class="text-secondary text-sm">{{ ACCESS_HIDDEN }}</p>
					<template v-else-if="tagRbacEnabled">
						<div v-if="accessibleTags.length" class="flex flex-wrap gap-2">
							<n-tag v-for="tag in accessibleTags" :key="tag.id" type="info" size="small">
								{{ tag.tag }}
							</n-tag>
						</div>
						<p v-else-if="tagsUnrestricted" class="text-secondary text-sm">No restrictions (full access)</p>
						<p v-else class="text-secondary text-sm">No tag access: tagged alerts are hidden</p>
					</template>
					<p v-else class="text-secondary text-sm">Tag RBAC is disabled</p>
				</n-spin>
			</n-card>

			<n-card v-if="isAdmin" size="small" title="Actions" embedded>
				<div class="flex flex-col gap-1">
					<AssignRole :user="resolvedUser" @success="reload" />
					<AssignCustomer
						v-if="!seesEveryCustomer(resolvedUser.role_name)"
						:user="resolvedUser"
						@success="reload"
					/>
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
import { NEEDS_A_CUSTOMER, needsCustomers, roleTagType, seesEveryCustomer } from "./roles"

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

// Another user's access is the admin's to read (those routes are admin-only); anyone
// may read their own, through the "me" route. Anything else would show a 403 as "no
// customer" — a false warning.
const ACCESS_HIDDEN = "Only admins can see another user's access."

const dFormats = useSettingsStore().dateFormat
const authStore = useAuthStore()
const isAdmin = authStore.isAdmin

const loadingCustomers = ref(false)
const loadingTags = ref(false)
const deleting = ref(false)
const customerCodes = ref<string[]>([])
const accessibleTags = ref<AlertTag[]>([])
const tagRbacEnabled = ref(false)
const tagsUnrestricted = ref(true)

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
		loadAccessData(value)
	}
})

// Usernames are unique, and the token names the signed-in user by username, not id.
function isSelf(user: User) {
	return user.username === authStore.userName
}

const accessReadable = computed(() => !!resolvedUser.value && (isAdmin || isSelf(resolvedUser.value)))

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
				tagsUnrestricted.value = !accessibleTags.value.length
			}
		})
		.catch(() => {
			accessibleTags.value = []
		})
		.finally(() => {
			loadingTags.value = false
		})
}

/** The signed-in user's own access, from the one route that serves it to non-admins. */
async function loadOwnAccess() {
	loadingCustomers.value = true
	loadingTags.value = true

	try {
		const res = await Api.tagRbac.getMyEffectiveAccess()
		customerCodes.value = (res.data.accessible_customers || []).filter(code => code !== "*")
		tagRbacEnabled.value = res.data.tag_rbac_enabled
		tagsUnrestricted.value = res.data.is_tag_unrestricted
		accessibleTags.value = res.data.is_tag_unrestricted ? [] : res.data.accessible_tags || []
	} catch {
		customerCodes.value = []
		accessibleTags.value = []
	} finally {
		loadingCustomers.value = false
		loadingTags.value = false
	}
}

async function loadAccessData(user: User) {
	if (!isAdmin) {
		if (isSelf(user)) {
			await loadOwnAccess()
		} else {
			customerCodes.value = []
			accessibleTags.value = []
		}
		return
	}

	// customer access does not depend on the tag settings, only tag access does
	await Promise.all([loadTagSettings(), loadCustomerAccess(user.id)])
	loadTagAccess(user.id)
}

function reload() {
	const user = resolvedUser.value
	if (!user) return
	if (props.user) {
		loadAccessData(user)
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
			loadAccessData(user)
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
