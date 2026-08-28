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
						<SectionHeading class="whitespace-nowrap">Configured ({{ repos.length }})</SectionHeading>
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

					<!--
						The 3px rail is the only carrier of status: transparent when healthy, painted
						when the repo needs attention. `--status-color` keeps the meter label in step.
					-->
					<div
						v-for="r of repoRows"
						:key="r.customer_code"
						class="border-default hover:bg-hover-005 relative flex items-center gap-3 overflow-hidden rounded-lg border py-2.5 pr-2.5 pl-4 transition-colors hover:border-[rgba(var(--primary-color-rgb)/0.35)] before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:bg-(--rail-color) before:transition-colors"
						:class="RAIL_CLASSES[r.status]"
					>
						<Icon
							:name="RepoIcon"
							:size="16"
							class="text-secondary shrink-0"
							:class="{ 'opacity-55': r.status === 'disabled' }"
						/>

						<div class="flex min-w-0 grow flex-col gap-0.5">
							<span
								class="truncate font-mono text-[13px] font-medium"
								:class="{ 'opacity-55': r.status === 'disabled' }"
								:title="r.repo"
							>
								{{ r.repo }}
							</span>
							<div class="text-secondary text-2xs flex flex-wrap items-center gap-1.5 font-mono">
								<span class="text-default font-medium">{{ r.customer_code }}</span>
								<span class="opacity-40">·</span>
								<span>{{ r.branch || "main" }}</span>
								<template v-if="r.has_token">
									<span class="opacity-40">·</span>
									<span>token</span>
								</template>
								<span class="opacity-40">·</span>
								<n-tooltip v-if="r.status === 'error'">
									<template #trigger>
										<span
											class="cursor-help font-medium text-(--status-color) underline decoration-dotted underline-offset-2"
										>
											{{ r.statusLabel }}
										</span>
									</template>
									{{ r.last_refresh_error || "The last cache refresh could not pull this repo." }}
								</n-tooltip>
								<span v-else class="font-medium text-(--status-color)">{{ r.statusLabel }}</span>
							</div>
						</div>

						<div class="flex shrink-0 items-center gap-0.5">
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
					<SectionHeading>{{ editing ? "Update repository" : "Add repository" }}</SectionHeading>
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
import SectionHeading from "@/components/copilotSearches/SectionHeading.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "changed"): void
}>()

/** Rail + status colour per state; healthy repos deliberately paint no rail. */
const RAIL_CLASSES: Record<RepoStatus, string> = {
	ok: "[--rail-color:transparent] [--status-color:var(--success-color)]",
	error: "[--rail-color:var(--error-color)] [--status-color:var(--error-color)]",
	disabled: "[--rail-color:var(--warning-color)] [--status-color:var(--warning-color)]",
	idle: "[--rail-color:transparent] [--status-color:var(--fg-secondary-color)]"
}

const RepoIcon = "carbon:logo-github"
const RefreshIcon = "carbon:renew"
const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const SaveIcon = "carbon:save"
const TestIcon = "carbon:plug"

const message = useMessage()
const { options: customerOptions, loading: loadingCustomers, load: loadCustomers } = useCustomerOptions()
const { applyGlobalCustomerPrefill } = useGlobalCustomerFilter()

const repos = ref<CustomRepoConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const refreshing = ref(false)
const editing = ref(false)

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
		if (!shown) {
			resetForm()
			return
		}

		loadRepos()
		// Seed the picker from the sidebar scope, after the options exist so the select can
		// resolve the code to a name. Only writes an empty field, so it never fights the
		// customer carried in by "Edit".
		loadCustomers().then(() => applyGlobalCustomerPrefill("customer_code", form))
	}
)
</script>
