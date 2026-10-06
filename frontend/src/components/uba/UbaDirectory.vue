<template>
	<div class="flex flex-col gap-9" data-testid="uba-directory">
		<UbaSection title="Directory sync" :caption="loaded ? `${sources.length} source${sources.length === 1 ? '' : 's'}` : undefined">
			<template #description>
				A directory sync gives UBA the customer's real accounts: names, departments, whether an account is
				enabled, and who holds admin roles (also roles granted through groups). Admins' findings weigh 1.5x.
				Without one, UBA learns accounts from events and sees role changes only as they happen.
			</template>

			<UbaError v-if="error" :error />

			<n-spin v-else :show="loading" class="min-h-24">
				<!-- No sync yet: how to add one, as two steps. -->
				<div
					v-if="loaded && !sources.length"
					class="panel border-default flex flex-col gap-4 rounded-lg border p-4"
					data-testid="uba-directory-setup"
				>
					<div class="flex items-center gap-2">
						<Icon name="carbon:catalog" :size="16" class="text-primary" />
						<span class="text-sm font-medium">No directory sync for this customer yet</span>
					</div>
					<ol class="m-0 flex list-none flex-col gap-4 p-0">
						<li class="step flex gap-3">
							<span class="step-number">1</span>
							<div class="flex min-w-0 flex-1 flex-col gap-2">
								<span class="text-secondary text-xs leading-relaxed">
									Create an Entra app registration with these read-only application permissions (admin consent):
								</span>
								<span class="flex flex-wrap gap-1.5">
									<span v-for="permission of PERMISSIONS" :key="permission" class="permission font-mono text-xs">
										{{ permission }}
									</span>
								</span>
							</div>
						</li>
						<li class="step flex gap-3">
							<span class="step-number">2</span>
							<div class="flex min-w-0 flex-1 flex-col gap-2">
								<span class="text-secondary text-xs leading-relaxed">
									Add it on the UBA host. The client secret is read from stdin and stored encrypted:
								</span>
								<CodeSource text :code="addCommand" lang="shellscript" data-testid="uba-directory-command" />
							</div>
						</li>
					</ol>
				</div>

				<div class="flex flex-col gap-3">
					<div v-for="s of sources" :key="s.id" class="panel border-default flex flex-col gap-2 rounded-lg border p-3">
						<div class="flex flex-wrap items-center gap-2">
							<Icon name="carbon:catalog" :size="15" class="text-primary" />
							<b>{{ s.type === "entra" ? "Entra ID" : s.type }}</b>
							<n-tag size="small" :type="statusType(s.status)" :bordered="false">{{ s.status }}</n-tag>
							<span class="text-secondary font-mono text-xs">directory {{ s.entra_tenant_id }} · app {{ s.client_id }}</span>
							<div class="ml-auto flex gap-2">
								<n-button size="small" secondary :loading="testing === s.id" @click="test(s)">Test</n-button>
								<n-button
									size="small"
									type="primary"
									secondary
									:disabled="s.status === 'disabled' || s.status === 'queued'"
									:loading="syncing === s.id"
									@click="sync(s)"
								>
									Sync now
								</n-button>
							</div>
						</div>
						<div class="text-secondary text-xs">
							last sync {{ s.last_sync ? formatDate(s.last_sync, dFormats.datetime) : "never" }}
							<template v-if="s.every_s">· every {{ Math.round(s.every_s / 60) }} min</template>
							<template v-if="resultSummary(s)">· {{ resultSummary(s) }}</template>
						</div>
						<n-alert v-if="s.last_error && s.status === 'error'" type="error" :bordered="false" class="text-xs">
							{{ s.last_error }}
						</n-alert>
						<n-alert
							v-if="testResults[s.id]"
							:type="testResults[s.id].ok ? 'success' : 'warning'"
							:bordered="false"
							closable
							class="text-xs"
							@close="delete testResults[s.id]"
						>
							{{ testResults[s.id].detail }}
						</n-alert>
						<p v-if="conflicts(s)" class="text-secondary m-0 text-xs">
							{{ conflicts(s) }} aliases belong to other identities UBA learned from events (merge candidates);
							they stay separate until merged.
						</p>
					</div>
				</div>
			</n-spin>
		</UbaSection>
		<UbaIdentityReview :customer-code />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaIdentitySource, UbaIdentitySourceStatus } from "@/types/uba"
import { NAlert, NButton, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaIdentityReview from "./UbaIdentityReview.vue"
import UbaSection from "./ui/UbaSection.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const PERMISSIONS = ["User.Read.All", "RoleManagement.Read.Directory", "GroupMember.Read.All"]
const POLL_MS = 15_000
const POLL_FOR_MS = 180_000

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const loaded = ref(false)
const error = ref<ApiError | null>(null)
const sources = ref<UbaIdentitySource[]>([])
const testing = ref<string | null>(null)
const syncing = ref<string | null>(null)
const testResults = ref<Record<string, { ok: boolean; detail: string }>>({})
let poll: ReturnType<typeof setInterval> | null = null
let pollUntil = 0

const addCommand = computed(
	() =>
		`docker compose exec -T worker uba-admin identity-sources add --tenant ${customerCode} \\\n    --entra-tenant <directory id> --client-id <application id> < secret.txt`
)

function statusType(status: UbaIdentitySourceStatus) {
	return ({ ok: "success", error: "error", queued: "info", new: "default", disabled: "default" } as const)[status] ?? "default"
}

function resultSummary(s: UbaIdentitySource): string {
	const r = s.last_result ?? {}
	const parts: string[] = []
	if (typeof r.users === "number") parts.push(r.full ? `${r.users} users listed` : `${r.users} users changed`)
	if (typeof r.created === "number" && r.created) parts.push(`${r.created} new`)
	if (typeof r.deleted === "number" && r.deleted) parts.push(`${r.deleted} deleted`)
	if (typeof r.role_memberships === "number") parts.push(`${r.role_memberships} role memberships`)
	return parts.join(", ")
}

function conflicts(s: UbaIdentitySource): number {
	const value = s.last_result?.conflicts
	return typeof value === "number" ? value : 0
}

function load(quiet = false) {
	if (!quiet) loading.value = true
	error.value = null
	Api.uba
		.getIdentitySources(customerCode)
		.then(res => {
			sources.value = res.data.identity_sources
			if (!sources.value.some(s => s.status === "queued") || Date.now() > pollUntil) stopPolling()
		})
		.catch((err: ApiError) => {
			error.value = err
			stopPolling()
		})
		.finally(() => {
			loading.value = false
			loaded.value = true
		})
}

function stopPolling() {
	if (poll) clearInterval(poll)
	poll = null
}

function test(s: UbaIdentitySource) {
	testing.value = s.id
	Api.uba
		.testIdentitySource(customerCode, s.id)
		.then(res => {
			testResults.value[s.id] = { ok: res.data.ok, detail: res.data.detail }
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Testing the directory sync failed.")
		})
		.finally(() => {
			testing.value = null
		})
}

function sync(s: UbaIdentitySource) {
	syncing.value = s.id
	Api.uba
		.syncIdentitySource(customerCode, s.id)
		.then(res => {
			message.success(res.data.detail)
			load(true)
			// UBA's worker picks it up within about a minute: refresh until it has run.
			stopPolling()
			pollUntil = Date.now() + POLL_FOR_MS
			poll = setInterval(load, POLL_MS, true)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Queuing the directory sync failed.")
		})
		.finally(() => {
			syncing.value = null
		})
}

onBeforeMount(() => load())
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.panel {
	background-color: var(--bg-secondary-color);
}

.step-number {
	display: grid;
	place-items: center;
	flex-shrink: 0;
	width: 20px;
	height: 20px;
	border-radius: 999px;
	font-family: var(--font-family-mono);
	font-size: 11px;
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.12);
}

.permission {
	padding: 2px 8px;
	border: 1px solid var(--border-color);
	border-radius: 6px;
	background-color: var(--bg-default-color);
}
</style>
