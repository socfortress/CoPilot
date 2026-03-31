<template>
	<div class="page">
		<UsersList :highlight />

		<!-- SSO Configuration — admin only -->
		<template v-if="isAdmin">
			<n-divider class="mt-8">
				<span class="text-secondary text-sm font-normal">Single Sign-On</span>
			</n-divider>

			<!-- SSO Config Card -->
			<n-card title="Single Sign-On (SSO) Configuration" class="mb-4">
				<template #header-extra>
					<n-tag :type="ssoEnabled ? 'success' : 'default'" size="small">
						{{ ssoEnabled ? "Enabled" : "Disabled" }}
					</n-tag>
				</template>

				<n-spin :show="loading">
					<n-form :model="form" label-placement="left" label-width="220" class="max-w-220">
						<!-- Global toggle -->
						<n-form-item label="Enable SSO">
							<n-switch v-model:value="form.sso_enabled" />
							<n-text class="text-secondary ml-4 text-sm">
								When enabled, SSO login buttons will appear on the login page.
							</n-text>
						</n-form-item>

						<n-divider />

						<!-- ── Azure Entra ID ────────────────────────────────────── -->
						<div class="mb-4 flex items-center gap-3">
							<Icon :name="AzureIcon" :size="22" />
							<h3 class="text-lg font-semibold">Azure Entra ID (OAuth2 / OIDC)</h3>
							<n-button text size="small" @click="showAzureGuide = !showAzureGuide">
								<template #icon>
									<Icon :name="showAzureGuide ? 'carbon:chevron-up' : 'carbon:information'" />
								</template>
								{{ showAzureGuide ? "Hide guide" : "Setup guide" }}
							</n-button>
						</div>

						<n-collapse-transition :show="showAzureGuide">
							<n-alert type="info" class="mb-5" :show-icon="false">
								<div class="text-xs">
									<p class="mb-2 font-semibold">How to configure Azure Entra ID:</p>
									<ol>
										<li>
											Go to
											<n-button
												text
												tag="a"
												href="https://portal.azure.com"
												target="_blank"
												type="info"
											>
												portal.azure.com
											</n-button>
											→
											<strong>Azure Active Directory</strong>
											→
											<strong>App registrations</strong>
											→
											<strong>New registration</strong>
										</li>
										<li>
											Set a name (e.g.
											<code>CoPilot SSO</code>
											), choose
											<em>Accounts in this organizational directory only</em>
											, then click
											<strong>Register</strong>
											.
										</li>
										<li>
											Copy the
											<strong>Application (client) ID</strong>
											→ paste as
											<em>Client ID</em>
											below.
										</li>
										<li>
											Copy the
											<strong>Directory (tenant) ID</strong>
											→ paste as
											<em>Tenant ID</em>
											below.
										</li>
										<li>
											Go to
											<strong>Certificates &amp; secrets</strong>
											→
											<strong>New client secret</strong>
											→ copy the value → paste as
											<em>Client Secret</em>
											below.
										</li>
										<li>
											Go to
											<strong>Authentication</strong>
											→
											<strong>Add a platform</strong>
											→
											<strong>Web</strong>
											→ set Redirect URI to:
											<br />
											<code>https://&lt;your-domain&gt;/api/auth/sso/azure/callback</code>
										</li>
										<li>
											Under
											<strong>Token configuration</strong>
											add optional claim
											<code>email</code>
											(ID token).
										</li>
										<li>
											Fill in the fields below, save, then add allowed emails in the section
											below.
										</li>
									</ol>
								</div>
							</n-alert>
						</n-collapse-transition>

						<n-form-item label="Enable Azure SSO">
							<n-switch v-model:value="form.azure_enabled" :disabled="!form.sso_enabled" />
						</n-form-item>
						<n-form-item label="Tenant ID">
							<n-input
								v-model:value="form.azure_tenant_id"
								placeholder="e.g. 12345678-abcd-1234-efgh-123456789012"
								:disabled="!form.azure_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Client ID (Application ID)">
							<n-input
								v-model:value="form.azure_client_id"
								placeholder="e.g. 87654321-dcba-4321-hgfe-210987654321"
								:disabled="!form.azure_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Client Secret">
							<n-input
								v-model:value="form.azure_client_secret"
								type="password"
								show-password-on="click"
								:placeholder="
									azureSecretSet ? '••••••• (saved — leave empty to keep)' : 'Enter client secret'
								"
								:disabled="!form.azure_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Redirect URI">
							<n-input-group>
								<n-input
									v-model:value="form.azure_redirect_uri"
									placeholder="https://your-domain.com/api/auth/sso/azure/callback"
									:disabled="!form.azure_enabled || !form.sso_enabled"
								/>
								<n-button
									:disabled="!form.azure_enabled || !form.sso_enabled"
									@click="prefillRedirectUri"
								>
									Auto-fill
								</n-button>
							</n-input-group>
						</n-form-item>
						<n-divider />

						<!-- ── Google OAuth2 / OIDC ──────────────────────────────────── -->
						<div class="mb-4 flex items-center gap-3">
							<Icon :name="GoogleIcon" :size="22" />
							<h3 class="text-lg font-semibold">Google (OAuth2 / OIDC)</h3>
							<n-button text size="small" @click="showGoogleGuide = !showGoogleGuide">
								<template #icon>
									<Icon :name="showGoogleGuide ? 'carbon:chevron-up' : 'carbon:information'" />
								</template>
								{{ showGoogleGuide ? "Hide guide" : "Setup guide" }}
							</n-button>
						</div>

						<n-collapse-transition :show="showGoogleGuide">
							<n-alert type="info" class="mb-5" :show-icon="false">
								<div class="text-xs">
									<p class="mb-2 font-semibold">How to configure Google OAuth2:</p>
									<ol>
										<li>
											Go to
											<n-button
												text
												tag="a"
												href="https://console.cloud.google.com/apis/credentials"
												target="_blank"
												type="info"
											>
												Google Cloud Console &rarr; Credentials
											</n-button>
											and click
											<strong>Create Credentials &rarr; OAuth client ID</strong>
											.
										</li>
										<li>
											Choose
											<strong>Web application</strong>
											as the application type.
										</li>
										<li>
											Under
											<strong>Authorized redirect URIs</strong>
											, add:
											<code>https://&lt;your-domain&gt;/api/auth/sso/google/callback</code>
										</li>
										<li>
											Copy the
											<strong>Client ID</strong>
											&rarr; paste as
											<em>Client ID</em>
											below.
										</li>
										<li>
											Copy the
											<strong>Client Secret</strong>
											&rarr; paste as
											<em>Client Secret</em>
											below.
										</li>
										<li>
											Make sure the
											<strong>People API</strong>
											is enabled in your project (required for
											<code>email</code>
											and
											<code>profile</code>
											scopes).
										</li>
										<li>
											Fill in the fields below, save, then add allowed emails in the section
											below.
										</li>
									</ol>
								</div>
							</n-alert>
						</n-collapse-transition>

						<n-form-item label="Enable Google SSO">
							<n-switch v-model:value="form.google_enabled" :disabled="!form.sso_enabled" />
						</n-form-item>
						<n-form-item label="Client ID">
							<n-input
								v-model:value="form.google_client_id"
								placeholder="e.g. 123456789-abc...xyz.apps.googleusercontent.com"
								:disabled="!form.google_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Client Secret">
							<n-input
								v-model:value="form.google_client_secret"
								type="password"
								show-password-on="click"
								:placeholder="
									googleSecretSet
										? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (saved \u2014 leave empty to keep)'
										: 'Enter client secret'
								"
								:disabled="!form.google_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Redirect URI">
							<n-input-group>
								<n-input
									v-model:value="form.google_redirect_uri"
									placeholder="https://your-domain.com/api/auth/sso/google/callback"
									:disabled="!form.google_enabled || !form.sso_enabled"
								/>
								<n-button
									:disabled="!form.google_enabled || !form.sso_enabled"
									@click="prefillGoogleRedirectUri"
								>
									Auto-fill
								</n-button>
							</n-input-group>
						</n-form-item>

						<n-divider />

						<!-- ── Cloudflare Access ───────────────────────────────────── -->
						<div class="mb-4 flex items-center gap-3">
							<Icon :name="CloudflareIcon" :size="22" />
							<h3 class="text-lg font-semibold">Cloudflare Access (JWT Assertion)</h3>
							<n-button text size="small" @click="showCFGuide = !showCFGuide">
								<template #icon>
									<Icon :name="showCFGuide ? 'carbon:chevron-up' : 'carbon:information'" />
								</template>
								{{ showCFGuide ? "Hide guide" : "Setup guide" }}
							</n-button>
						</div>

						<n-collapse-transition :show="showCFGuide">
							<n-alert type="info" class="mb-5" :show-icon="false">
								<div class="text-xs">
									<p class="mb-2 font-semibold">How to configure Cloudflare Access:</p>
									<ol>
										<li>
											In
											<n-button
												text
												tag="a"
												href="https://one.dash.cloudflare.com"
												target="_blank"
												type="info"
											>
												Cloudflare Zero Trust dashboard
											</n-button>
											go to
											<strong>Access → Applications → Add an application</strong>
											.
										</li>
										<li>
											Choose
											<strong>Self-hosted</strong>
											. Set the domain to your CoPilot URL (e.g.
											<code>copilot.example.com</code>
											).
										</li>
										<li>
											Under
											<strong>Identity providers</strong>
											connect your IdP (e.g. Entra ID, Google, GitHub).
										</li>
										<li>
											After creating the app, open it →
											<strong>Overview</strong>
											→ copy the
											<strong>Application Audience (AUD) Tag</strong>
											→ paste as
											<em>Application Audience</em>
											below.
										</li>
										<li>
											Copy your
											<strong>Team Domain</strong>
											from
											<strong>Settings → Custom Pages</strong>
											(e.g.
											<code>myteam.cloudflareaccess.com</code>
											) → paste as
											<em>Team Domain</em>
											below.
										</li>
										<li>
											<strong>How it works:</strong>
											Cloudflare injects a signed
											<code>Cf-Access-Jwt-Assertion</code>
											header into every request. CoPilot verifies the JWT signature against
											Cloudflare's public JWKS — it is cryptographically impossible to forge
											without Cloudflare's private key.
										</li>
										<li>
											On the CoPilot login page click
											<strong>"Sign in with Cloudflare Access"</strong>
											— the backend reads the header automatically.
										</li>
									</ol>
								</div>
							</n-alert>
						</n-collapse-transition>

						<n-form-item label="Enable Cloudflare Access">
							<n-switch v-model:value="form.cf_enabled" :disabled="!form.sso_enabled" />
						</n-form-item>
						<n-form-item label="Team Domain">
							<n-input
								v-model:value="form.cf_team_domain"
								placeholder="e.g. myteam.cloudflareaccess.com"
								:disabled="!form.cf_enabled || !form.sso_enabled"
							/>
						</n-form-item>
						<n-form-item label="Application Audience (AUD)">
							<n-input
								v-model:value="form.cf_audience"
								placeholder="AUD tag from Cloudflare Access dashboard"
								:disabled="!form.cf_enabled || !form.sso_enabled"
							/>
						</n-form-item>

						<n-divider />

						<div class="flex justify-end">
							<n-button type="primary" :loading="saving" @click="saveSettings">
								Save SSO Settings
							</n-button>
						</div>
					</n-form>
				</n-spin>
			</n-card>

			<!-- Allowed Emails Card -->
			<n-card title="SSO Allowed Emails" class="mb-4">
				<template #header-extra>
					<n-button size="small" type="primary" @click="showAddEmail = true">
						<template #icon>
							<Icon :name="AddIcon" />
						</template>
						Add Email
					</n-button>
				</template>

				<n-text class="text-secondary mb-4 block text-sm">
					Only users with an email listed here are allowed to log in via SSO. After first login, a CoPilot
					account is automatically created with the assigned role.
				</n-text>

				<n-spin :show="loadingEmails">
					<p v-if="!allowedEmails.length" class="text-secondary py-4 text-center">
						No allowed emails configured. Add emails to permit SSO login.
					</p>
					<n-table v-else :bordered="false">
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
								<td>{{ formatDate(entry.created_at) }}</td>
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
			<n-modal
				v-model:show="showAddEmail"
				preset="card"
				title="Add SSO Allowed Email"
				:style="{ maxWidth: '450px' }"
			>
				<n-form :model="newEmail" label-placement="top">
					<n-form-item label="Email Address">
						<n-input v-model:value="newEmail.email" placeholder="user@company.com" />
					</n-form-item>
					<n-form-item label="Assigned Role">
						<n-select v-model:value="newEmail.role_id" :options="roleOptions" />
						<template #feedback>
							<span class="text-secondary text-xs">
								Role assigned when the user logs in for the first time via SSO.
							</span>
						</template>
					</n-form-item>
					<div class="flex justify-end gap-2 pt-2">
						<n-button @click="showAddEmail = false">Cancel</n-button>
						<n-button type="primary" :loading="addingEmail" :disabled="!newEmail.email" @click="addEmail">
							Add Email
						</n-button>
					</div>
				</n-form>
			</n-modal>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { SSOAllowedEmail, SSOConfigUpdate } from "@/api/endpoints/sso"
import dayjs from "dayjs"
import {
	NAlert,
	NButton,
	NCard,
	NCollapseTransition,
	NDivider,
	NForm,
	NFormItem,
	NInput,
	NInputGroup,
	NModal,
	NSelect,
	NSpin,
	NSwitch,
	NTable,
	NTag,
	NText,
	useMessage
} from "naive-ui"
import { onBeforeMount, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import UsersList from "@/components/users/UsersList.vue"
import { useAuthStore } from "@/stores/auth"

const AzureIcon = "mdi:microsoft-azure"
const GoogleIcon = "mdi:google"
const CloudflareIcon = "simple-icons:cloudflare"
const AddIcon = "carbon:add"
const DeleteIcon = "carbon:trash-can"

const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

const highlight = ref<string | undefined>(undefined)
const isAdmin = ref(authStore.isAdmin)

// ── SSO state ────────────────────────────────────────────────────────────────
const loading = ref(false)
const saving = ref(false)
const loadingEmails = ref(false)
const addingEmail = ref(false)
const showAddEmail = ref(false)
const showAzureGuide = ref(false)
const showGoogleGuide = ref(false)
const showCFGuide = ref(false)
const azureSecretSet = ref(false)
const googleSecretSet = ref(false)
const ssoEnabled = ref(false)

const form = ref<SSOConfigUpdate>({
	sso_enabled: false,
	azure_enabled: false,
	azure_tenant_id: null,
	azure_client_id: null,
	azure_client_secret: null,
	azure_redirect_uri: null,
	google_enabled: false,
	google_client_id: null,
	google_client_secret: null,
	google_redirect_uri: null,
	cf_enabled: false,
	cf_team_domain: null,
	cf_audience: null
})

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

function formatDate(dateStr: string) {
	return dayjs(dateStr).format("YYYY-MM-DD HH:mm")
}

function prefillRedirectUri() {
	form.value.azure_redirect_uri = `${window.location.origin}/api/auth/sso/azure/callback`
}

function prefillGoogleRedirectUri() {
	form.value.google_redirect_uri = `${window.location.origin}/api/auth/sso/google/callback`
}

async function loadSettings() {
	loading.value = true
	try {
		const res = await Api.sso.getSettings()
		const d = res.data
		ssoEnabled.value = d.sso_enabled
		azureSecretSet.value = d.azure_client_secret_set
		googleSecretSet.value = d.google_client_secret_set
		form.value = {
			sso_enabled: d.sso_enabled,
			azure_enabled: d.azure_enabled,
			azure_tenant_id: d.azure_tenant_id,
			azure_client_id: d.azure_client_id,
			azure_client_secret: null,
			azure_redirect_uri: d.azure_redirect_uri,
			google_enabled: d.google_enabled,
			google_client_id: d.google_client_id,
			google_client_secret: null,
			google_redirect_uri: d.google_redirect_uri,
			cf_enabled: d.cf_enabled,
			cf_team_domain: d.cf_team_domain,
			cf_audience: d.cf_audience
		}
	} finally {
		loading.value = false
	}
}

async function saveSettings() {
	saving.value = true
	try {
		const res = await Api.sso.updateSettings(form.value)
		ssoEnabled.value = res.data.sso_enabled
		azureSecretSet.value = res.data.azure_client_secret_set
		googleSecretSet.value = res.data.google_client_secret_set
		message.success("SSO settings saved successfully")
	} catch (err: any) {
		message.error(err.response?.data?.detail || "Failed to save SSO settings")
	} finally {
		saving.value = false
	}
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
		message.error(err.response?.data?.detail || "Failed to add email")
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
		message.error(err.response?.data?.detail || "Failed to remove email")
	}
}

onBeforeMount(() => {
	if (route.query?.user_id) {
		highlight.value = route.query.user_id.toString()
	}
})

onMounted(() => {
	if (isAdmin.value) {
		loadSettings()
		loadEmails()
	}
})
</script>
