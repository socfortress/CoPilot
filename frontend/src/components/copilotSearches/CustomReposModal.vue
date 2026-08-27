<template>
	<n-modal
		:show
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
				<p class="text-default text-sm">
					Point a customer at their own GitHub repo of Graylog-only detection rules (layout
					<code>detections/&lt;folder&gt;/&lt;rule&gt;.yaml</code>
					, same as the shared catalog). Their rules then appear as
					<b>Custom</b>
					cards alongside the catalog — searchable, provisionable, backtestable. Rules stay in the client's
					repo; CoPilot only stores this pointer.
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

					<n-empty
						v-if="!repos.length && !loading"
						description="No custom repositories configured yet."
						class="py-6"
					/>

					<div v-for="r of repoRows" :key="r.customer_code" class="repo-row" :class="`is-${r.status}`">
						<Icon :name="RepoIcon" :size="16" class="repo-row__glyph" />

						<div class="repo-row__body">
							<span class="repo-row__name" :title="r.repo">{{ r.repo }}</span>
							<div class="repo-row__meta">
								<span class="repo-row__customer">{{ r.customer_code }}</span>
								<span class="repo-row__sep">·</span>
								<span>{{ r.branch || "main" }}</span>
								<template v-if="r.has_token">
									<span class="repo-row__sep">·</span>
									<span>token</span>
								</template>
								<span class="repo-row__sep">·</span>
								<n-tooltip v-if="r.status === 'error'">
									<template #trigger>
										<span class="repo-row__status">{{ r.statusLabel }}</span>
									</template>
									{{ r.last_refresh_error || "The last cache refresh could not pull this repo." }}
								</n-tooltip>
								<span v-else class="repo-row__status">{{ r.statusLabel }}</span>
							</div>
						</div>

						<div class="repo-row__actions">
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
					</div>
				</section>

				<!-- Add / update -->
				<section class="border-default flex flex-col gap-3 rounded-lg border p-4">
					<h4 class="section-title">{{ editing ? "Update repository" : "Add repository" }}</h4>
					<n-form :model="form" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<n-form-item label="Customer" path="customer_code" :show-feedback="false">
							<n-select
								v-model:value="form.customer_code"
								:options="customerOptions"
								:loading="loadingCustomers"
								filterable
								:disabled="editing"
								placeholder="Select a customer"
							/>
						</n-form-item>
						<n-form-item label="Repository (owner/name)" path="repo" :show-feedback="false">
							<n-input v-model:value="form.repo" placeholder="acme-soc/detection-rules" />
						</n-form-item>
						<n-form-item label="Branch" path="branch" :show-feedback="false">
							<n-input v-model:value="form.branch" placeholder="main" />
						</n-form-item>
						<n-form-item path="token" :show-feedback="false">
							<template #label>
								Read token
								<span class="opacity-60">(private repos only)</span>
							</template>
							<n-input
								v-model:value="form.token"
								type="password"
								show-password-on="click"
								:placeholder="editing ? 'leave blank to keep existing' : 'optional PAT'"
							/>
						</n-form-item>
					</n-form>
					<div class="flex items-center gap-3">
						<n-switch v-model:value="form.enabled" size="small" />
						<span class="text-sm">Enabled</span>
						<div class="grow" />
						<n-button v-if="editing" size="small" quaternary @click="resetForm">Reset</n-button>
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
	NForm,
	NFormItem,
	NInput,
	NModal,
	NPopconfirm,
	NScrollbar,
	NSelect,
	NSpin,
	NSwitch,
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

type RepoStatus = "ok" | "error" | "disabled" | "idle"

function resolveStatus(r: CustomRepoConfig): RepoStatus {
	if (!r.enabled) return "disabled"
	if (r.last_refresh_ok === false) return "error"
	if (r.last_refresh_ok === true) return "ok"
	return "idle"
}

function resolveStatusLabel(r: CustomRepoConfig, status: RepoStatus): string {
	if (status === "disabled") return "disabled"
	if (status === "error") return "refresh failed"
	if (status === "idle") return "not synced"

	const count = r.rules_loaded ?? 0
	return `${count} rule${count === 1 ? "" : "s"}`
}

/** Repos decorated with the single status that drives both the accent rail and the meta label. */
const repoRows = computed(() =>
	repos.value.map(r => {
		const status = resolveStatus(r)
		return { ...r, status, statusLabel: resolveStatusLabel(r, status) }
	})
)

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

<style scoped lang="scss">
.repo-row {
	--rail-color: transparent;
	--status-color: var(--fg-secondary-color);

	position: relative;
	display: flex;
	align-items: center;
	gap: 12px;
	overflow: hidden;
	padding: 10px 10px 10px 16px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	transition:
		background-color 0.2s var(--bezier-ease),
		border-color 0.2s var(--bezier-ease);

	&::before {
		content: "";
		position: absolute;
		inset: 0 auto 0 0;
		width: 3px;
		background-color: var(--rail-color);
		transition: background-color 0.2s var(--bezier-ease);
	}

	&.is-ok {
		--status-color: var(--success-color);
	}

	&.is-error {
		--rail-color: var(--error-color);
		--status-color: var(--error-color);
	}

	&.is-disabled {
		--rail-color: var(--warning-color);
		--status-color: var(--warning-color);

		.repo-row__glyph,
		.repo-row__name {
			opacity: 0.55;
		}
	}

	&:hover {
		background-color: var(--hover-005-color);
		border-color: rgba(var(--primary-color-rgb) / 0.35);
	}

	.repo-row__glyph {
		flex-shrink: 0;
		color: var(--fg-secondary-color);
	}

	.repo-row__body {
		display: flex;
		min-width: 0;
		flex-grow: 1;
		flex-direction: column;
		gap: 2px;
	}

	.repo-row__name {
		overflow: hidden;
		font-family: var(--font-family-mono);
		font-size: 13px;
		font-weight: 500;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.repo-row__meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		font-family: var(--font-family-mono);
		font-size: 11px;
		color: var(--fg-secondary-color);
	}

	.repo-row__customer {
		color: var(--fg-default-color);
		font-weight: 500;
	}

	.repo-row__sep {
		opacity: 0.4;
	}

	.repo-row__status {
		color: var(--status-color);
		font-weight: 500;
	}

	&.is-error .repo-row__status {
		cursor: help;
		text-decoration: underline dotted;
		text-underline-offset: 2px;
	}

	.repo-row__actions {
		display: flex;
		flex-shrink: 0;
		align-items: center;
		gap: 2px;
	}
}

.section-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--n-text-color-3, #888);
}
</style>
