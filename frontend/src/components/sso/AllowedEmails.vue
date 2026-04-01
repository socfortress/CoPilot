<template>
	<div v-if="isAdmin">
		<!-- Allowed Emails Card -->
		<n-card title="SSO Allowed Emails" size="small">
			<template #header-extra>
				<div class="flex justify-end gap-2">
					<n-button size="small" @click="routeSSOConfig().navigate()">
						<template #icon>
							<Icon :name="SSOConfigIcon" />
						</template>
						SSO Configuration
					</n-button>

					<n-button size="small" type="primary" @click="showAddEmail = true">
						<template #icon>
							<Icon :name="AddIcon" />
						</template>
						Add Email
					</n-button>
				</div>
			</template>

			<n-text class="text-secondary mb-4 block text-sm">
				Existing users are automatically enabled for SSO login. Add email addresses to allow new users to sign
				in and create an account via SSO.
			</n-text>

			<n-spin :show="loadingEmails">
				<p v-if="!allowedEmails.length" class="text-secondary py-4 text-center">
					No allowed emails configured. Add an email to allow access via SSO.
				</p>
				<n-table v-else>
					<thead>
						<tr>
							<th>Email</th>
							<th>Role</th>
							<th>Added</th>
							<th class="w-16"></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="entry of allowedEmails" :key="entry.id">
							<td>{{ entry.email }}</td>
							<td>
								<n-tag :type="getRoleTagType(entry.role_id)" size="small">
									{{ getRoleName(entry.role_id) }}
								</n-tag>
							</td>
							<td>{{ formatDate(entry.created_at, dFormats.datetime) }}</td>
							<td>
								<n-button text type="error" size="small" @click="removeEmail(entry.id)">
									<template #icon>
										<Icon :name="DeleteIcon" />
									</template>
								</n-button>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-spin>
		</n-card>

		<!-- Add Email Modal -->
		<n-modal v-model:show="showAddEmail" preset="card" title="Add SSO Allowed Email" :style="{ maxWidth: '450px' }">
			<n-form :model="newEmail" label-placement="top">
				<n-form-item label="Email Address">
					<n-input v-model:value="newEmail.email" placeholder="user@company.com" />
				</n-form-item>
				<n-form-item label="Assigned Role" class="w-full">
					<div class="flex w-full flex-col gap-2">
						<n-select v-model:value="newEmail.role_id" :options="roleOptions" />
						<span class="text-secondary text-xs">
							Role assigned when the user logs in for the first time via SSO.
						</span>
					</div>
				</n-form-item>
				<div class="flex justify-end gap-2 pt-2">
					<n-button @click="showAddEmail = false">Cancel</n-button>
					<n-button type="primary" :loading="addingEmail" :disabled="!newEmail.email" @click="addEmail">
						Add Email
					</n-button>
				</div>
			</n-form>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SSOAllowedEmail } from "@/api/endpoints/sso"
import {
	NButton,
	NCard,
	NForm,
	NFormItem,
	NInput,
	NModal,
	NSelect,
	NSpin,
	NTable,
	NTag,
	NText,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { routeSSOConfig } = useNavigation()

const SSOConfigIcon = "carbon:rule-locked"
const AddIcon = "carbon:add"
const DeleteIcon = "carbon:trash-can"

const authStore = useAuthStore()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const isAdmin = computed(() => authStore.isAdmin)

const loadingEmails = ref(false)
const addingEmail = ref(false)
const showAddEmail = ref(false)

const allowedEmails = ref<SSOAllowedEmail[]>([])
const newEmail = ref({ email: "", role_id: 2 })

const roleOptions = [
	{ label: "Admin", value: 1 },
	{ label: "Analyst (default)", value: 2 }
]

function getRoleName(roleId: number) {
	return roleId === 1 ? "admin" : roleId === 2 ? "analyst" : roleId === 3 ? "scheduler" : "customer_user"
}

function getRoleTagType(roleId: number) {
	return roleId === 1 ? "error" : roleId === 2 ? "warning" : "default"
}

async function loadEmails() {
	loadingEmails.value = true

	try {
		const res = await Api.sso.getAllowedEmails()
		allowedEmails.value = res.data.emails
	} catch {
		allowedEmails.value = []
	} finally {
		loadingEmails.value = false
	}
}

async function addEmail() {
	if (!newEmail.value.email) return

	addingEmail.value = true

	try {
		await Api.sso.addAllowedEmail({ email: newEmail.value.email, role_id: newEmail.value.role_id })
		message.success(`Email ${newEmail.value.email} added to allowlist`)
		newEmail.value = { email: "", role_id: 2 }
		showAddEmail.value = false
		loadEmails()
	} catch (err: any) {
		message.error(err.response?.data?.message || err.response?.data?.detail || "Failed to add email")
	} finally {
		addingEmail.value = false
	}
}

async function removeEmail(id: number) {
	try {
		await Api.sso.removeAllowedEmail(id)
		message.success("Email removed from allowlist")
		loadEmails()
	} catch (err: any) {
		message.error(err.response?.data?.message || err.response?.data?.detail || "Failed to remove email")
	}
}

onBeforeMount(() => {
	if (isAdmin.value) {
		loadEmails()
	}
})
</script>
