<template>
	<n-modal
		:show="show"
		preset="card"
		segmented
		:style="{ width: 'min(760px, 94vw)', maxHeight: '90vh' }"
		content-class="p-0!"
		@update:show="onShow"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="RepoIcon" :size="20" />
				<span class="font-semibold">Custom rule repositories</span>
			</div>
		</template>

		<n-scrollbar style="max-height: 78vh">
			<div class="flex flex-col gap-5 p-5">
				<p class="text-secondary text-sm">
					Point a customer at their own GitHub repo of Graylog-only detection rules (layout
					<code>detections/&lt;folder&gt;/&lt;rule&gt;.yaml</code>, same as the shared catalog). Their rules then appear
					as <b>Custom</b> cards alongside the catalog — searchable, provisionable, backtestable. Rules stay in the
					client's repo; CoPilot only stores this pointer.
				</p>

				<!-- Configured repos -->
				<section class="flex flex-col gap-2">
					<div class="flex items-center gap-2">
						<h4 class="section-title">Configured ({{ repos.length }})</h4>
						<n-spin v-if="loading" :size="12" />
						<div class="grow" />
						<n-button size="tiny" secondary :loading="refreshing" @click="refreshCache">
							<template #icon><Icon :name="RefreshIcon" :size="14" /></template>
							Refresh rules now
						</n-button>
					</div>

					<n-empty v-if="!repos.length && !loading" description="No custom repositories configured yet." class="py-6" />

					<div
						v-for="r of repos"
						:key="r.customer_code"
						class="border-default flex flex-wrap items-center gap-3 rounded-lg border p-3"
					>
						<div class="flex min-w-0 grow flex-col">
							<div class="flex items-center gap-2">
								<code class="text-sm font-medium">{{ r.repo }}</code>
								<n-tag size="tiny" round :bordered="false">{{ r.branch }}</n-tag>
								<n-tag v-if="r.has_token" size="tiny" round :bordered="false" type="info">token</n-tag>
								<n-tag v-if="!r.enabled" size="tiny" round :bordered="false" type="warning">disabled</n-tag>
								<n-tag
									v-if="r.last_refresh_ok === true"
									size="tiny"
									round
									:bordered="false"
									type="success"
								>
									{{ r.rules_loaded ?? 0 }} rule{{ (r.rules_loaded ?? 0) === 1 ? "" : "s" }}
								</n-tag>
								<n-tooltip v-else-if="r.last_refresh_ok === false">
									<template #trigger>
										<n-tag size="tiny" round :bordered="false" type="error">refresh failed</n-tag>
									</template>
									{{ r.last_refresh_error || "The last cache refresh could not pull this repo." }}
								</n-tooltip>
							</div>
							<span class="text-secondary text-xs">customer {{ r.customer_code }}</span>
						</div>
						<n-button size="tiny" quaternary @click="editRepo(r)">
							<template #icon><Icon :name="EditIcon" :size="14" /></template>
							Edit
						</n-button>
						<n-popconfirm @positive-click="removeRepo(r.customer_code)">
							<template #trigger>
								<n-button size="tiny" quaternary type="error">
									<template #icon><Icon :name="DeleteIcon" :size="14" /></template>
								</n-button>
							</template>
							Remove the pointer for {{ r.customer_code }}? (Their GitHub repo is untouched.)
						</n-popconfirm>
					</div>
				</section>

				<!-- Add / update -->
				<section class="border-default flex flex-col gap-3 rounded-lg border p-4">
					<h4 class="section-title">{{ editing ? "Update repository" : "Add repository" }}</h4>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<div class="flex flex-col gap-1">
							<span class="text-secondary text-xs font-medium">Customer</span>
							<n-select
								v-model:value="form.customer_code"
								:options="customerOptions"
								:loading="loadingCustomers"
								filterable
								:disabled="editing"
								placeholder="Select a customer"
							/>
						</div>
						<div class="flex flex-col gap-1">
							<span class="text-secondary text-xs font-medium">Repository (owner/name)</span>
							<n-input v-model:value="form.repo" placeholder="acme-soc/detection-rules" />
						</div>
						<div class="flex flex-col gap-1">
							<span class="text-secondary text-xs font-medium">Branch</span>
							<n-input v-model:value="form.branch" placeholder="main" />
						</div>
						<div class="flex flex-col gap-1">
							<span class="text-secondary text-xs font-medium">
								Read token <span class="opacity-60">(private repos only)</span>
							</span>
							<n-input
								v-model:value="form.token"
								type="password"
								show-password-on="click"
								:placeholder="editing ? 'leave blank to keep existing' : 'optional PAT'"
							/>
						</div>
					</div>
					<div class="flex items-center gap-3">
						<n-switch v-model:value="form.enabled" size="small" />
						<span class="text-sm">Enabled</span>
						<div class="grow" />
						<n-button v-if="editing" size="small" quaternary @click="resetForm">Cancel</n-button>
						<n-button size="small" secondary :loading="testing" :disabled="!canSave" @click="testRepo">
							<template #icon><Icon :name="TestIcon" :size="16" /></template>
							Test
						</n-button>
						<n-button size="small" type="primary" :loading="saving" :disabled="!canSave" @click="save">
							<template #icon><Icon :name="SaveIcon" :size="16" /></template>
							{{ editing ? "Update" : "Add" }}
						</n-button>
					</div>
				</section>
			</div>
		</n-scrollbar>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomRepoConfig } from "@/types/copilot-searches"
import {
	NButton,
	NEmpty,
	NInput,
	NModal,
	NPopconfirm,
	NScrollbar,
	NSelect,
	NSpin,
	NSwitch,
	NTag,
	NTooltip,
	useMessage
} from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "changed"): void
}>()

const RepoIcon = "carbon:logo-github"
const RefreshIcon = "carbon:renew"
const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const SaveIcon = "carbon:save"
const TestIcon = "carbon:plug"

const message = useMessage()

const repos = ref<CustomRepoConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const refreshing = ref(false)
const editing = ref(false)
const loadingCustomers = ref(false)
const customerOptions = ref<{ label: string; value: string }[]>([])

const form = reactive<{ customer_code: string | null; repo: string; branch: string; token: string; enabled: boolean }>({
	customer_code: null,
	repo: "",
	branch: "main",
	token: "",
	enabled: true
})

const canSave = computed(() => !!form.customer_code && /\S+\/\S+/.test(form.repo.trim()))

function resetForm() {
	editing.value = false
	form.customer_code = null
	form.repo = ""
	form.branch = "main"
	form.token = ""
	form.enabled = true
}

function editRepo(r: CustomRepoConfig) {
	editing.value = true
	form.customer_code = r.customer_code
	form.repo = r.repo
	form.branch = r.branch || "main"
	form.token = ""
	form.enabled = r.enabled
}

async function loadRepos() {
	loading.value = true
	try {
		const res = await Api.copilotSearches.listCustomRepos()
		repos.value = res.data.repos || []
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load custom repositories")
	} finally {
		loading.value = false
	}
}

async function loadCustomers() {
	loadingCustomers.value = true
	try {
		const res = await Api.customers.getCustomers({})
		customerOptions.value = (res.data.customers || []).map(c => ({
			label: `${c.customer_name} (${c.customer_code})`,
			value: c.customer_code
		}))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load customers")
	} finally {
		loadingCustomers.value = false
	}
}

async function save() {
	if (!form.customer_code || !canSave.value) return
	saving.value = true
	try {
		await Api.copilotSearches.setCustomRepo(form.customer_code, {
			repo: form.repo.trim(),
			branch: form.branch.trim() || "main",
			token: form.token ? form.token : undefined,
			enabled: form.enabled
		})
		message.success("Saved. Use “Refresh rules now” to pull this repo's rules.")
		resetForm()
		await loadRepos()
		emit("changed")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to save repository")
	} finally {
		saving.value = false
	}
}

async function testRepo() {
	if (!canSave.value) return
	testing.value = true
	try {
		const res = await Api.copilotSearches.testCustomRepo({
			repo: form.repo.trim(),
			branch: form.branch.trim() || "main",
			token: form.token ? form.token : undefined,
			// when editing with a blank token field, test with the stored token
			customer_code: editing.value && !form.token ? form.customer_code : undefined
		})
		if (res.data.ok) {
			message.success(`Connection OK — found ${res.data.rules_found} detection YAML(s).`)
		} else {
			message.error(res.data.error || "Test failed.")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Test request failed.")
	} finally {
		testing.value = false
	}
}

async function removeRepo(customerCode: string) {
	try {
		await Api.copilotSearches.deleteCustomRepo(customerCode)
		message.success("Removed. Refresh to drop its rules.")
		await loadRepos()
		emit("changed")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to remove repository")
	}
}

async function refreshCache() {
	refreshing.value = true
	try {
		const res = await Api.copilotSearches.refreshCache()
		message.success(`Rules refreshed — ${res.data.rules_loaded ?? "?"} loaded.`)
		await loadRepos() // pick up the fresh per-repo fetch status chips
		emit("changed")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Refresh failed")
	} finally {
		refreshing.value = false
	}
}

function onShow(value: boolean) {
	emit("update:show", value)
}

watch(
	() => props.show,
	shown => {
		if (shown) {
			loadRepos()
			if (!customerOptions.value.length) loadCustomers()
		} else {
			resetForm()
		}
	}
)
</script>

<style scoped>
.section-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--n-text-color-3, #888);
}
</style>
