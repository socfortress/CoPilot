<template>
	<UbaSection title="Identity review">
		<template #description>
			Accounts UBA learned from events and the customer's directory users may be the same person. Merging
			moves the account's findings, alerts, history and risk to the person it belongs to; it cannot be
			undone. UBA runs a merge within a minute.
			<template v-if="!isAdmin">Only admins can merge.</template>
		</template>

		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-16">
			<template v-if="review">
				<div class="flex flex-col gap-2">
					<span class="text-sm font-semibold">Probably the same person ({{ review.candidates.length }})</span>
					<p v-if="!review.candidates.length" class="text-secondary text-xs">
						{{
							review.has_directory
								? "Nothing to review: the directory sync found no account that another identity already owns."
								: "Merge suggestions come from a directory sync, and none is connected for this customer."
						}}
					</p>
					<div
						v-for="c of review.candidates"
						:key="c.id"
						class="panel border-default flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 text-sm"
					>
						<div class="flex min-w-60 flex-col">
							<span class="text-tertiary text-xs">Learned from events</span>
							<b>{{ label(c.identity) }}</b>
							<span class="text-secondary text-xs">{{ details(c.identity) }}</span>
						</div>
						<Icon name="carbon:arrow-right" :size="16" class="text-tertiary" />
						<div class="flex min-w-60 flex-col">
							<span class="text-tertiary text-xs">Directory user</span>
							<b>{{ label(c.candidate) }}</b>
							<span class="text-secondary text-xs">{{ details(c.candidate) }}</span>
						</div>
						<span class="text-tertiary text-xs">both claim <span class="font-mono">{{ c.alias }}</span></span>
						<div v-if="isAdmin" class="ml-auto flex gap-2">
							<n-popconfirm @positive-click="merge(c.identity.id, c.candidate.id)">
								<template #trigger>
									<n-button size="small" type="primary" secondary :loading="busy === c.identity.id">Merge</n-button>
								</template>
								Merge {{ label(c.identity) }} into {{ label(c.candidate) }}? This cannot be undone.
							</n-popconfirm>
							<n-button size="small" quaternary :disabled="busy === c.identity.id" @click="dismiss(c)">
								Not the same
							</n-button>
						</div>
					</div>
				</div>

				<div v-if="review.has_directory" class="mt-3 flex flex-col gap-2">
					<span class="text-sm font-semibold">Accounts not matched to the directory ({{ review.unmatched.length }})</span>
					<p class="text-secondary text-xs">
						With findings in the last 14 days. Merge one into the person it belongs to, or keep it as it is
						(for example a local or service account).
					</p>
					<div
						v-for="u of review.unmatched"
						:key="u.id"
						class="panel border-default flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 text-sm"
					>
						<div class="flex min-w-60 flex-col">
							<b>{{ label(u) }}</b>
							<span class="text-secondary text-xs">{{ details(u) }}</span>
						</div>
						<div v-if="isAdmin" class="ml-auto flex flex-wrap items-center gap-2">
							<n-select
								v-model:value="targets[u.id]"
								class="w-72"
								size="small"
								filterable
								remote
								clearable
								placeholder="Merge into… (search a name)"
								:options="options[u.id] ?? []"
								:loading="searching === u.id"
								@search="q => search(u.id, q)"
							/>
							<n-popconfirm @positive-click="merge(u.id, targets[u.id] ?? '')">
								<template #trigger>
									<n-button size="small" type="primary" secondary :disabled="!targets[u.id]" :loading="busy === u.id">
										Merge
									</n-button>
								</template>
								Merge {{ label(u) }} into the selected identity? This cannot be undone.
							</n-popconfirm>
							<n-button size="small" quaternary :disabled="busy === u.id" @click="keep(u)">Keep as is</n-button>
						</div>
					</div>
				</div>

				<div v-if="review.merges.length" class="mt-3 flex flex-col gap-1">
					<span class="text-sm font-semibold">Recent merges</span>
					<ul class="m-0 flex list-none flex-col gap-1 p-0 text-xs">
						<li v-for="m of review.merges" :key="m.id" class="flex flex-wrap items-center gap-2">
							<n-tag size="tiny" :bordered="false" :type="m.status === 'done' ? 'success' : m.status === 'error' ? 'error' : 'default'">
								{{ m.status }}
							</n-tag>
							<span>{{ m.from_name || m.from_identity }} → {{ m.into_name || m.into_identity }}</span>
							<span class="text-tertiary">
								{{ m.requested_by }}{{ m.requested_at ? ` · ${formatDate(m.requested_at, dFormats.datetime)}` : "" }}
							</span>
							<span v-if="m.error" class="text-error">{{ m.error }}</span>
						</li>
					</ul>
				</div>
			</template>
		</n-spin>
	</UbaSection>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaIdentityReview, UbaIdentitySummary, UbaMergeCandidate } from "@/types/uba"
import { NButton, NPopconfirm, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaSection from "./ui/UbaSection.vue"
import { identityDetails, identityLabel } from "./utils"

const { customerCode } = defineProps<{ customerCode: string }>()

const POLL_MS = 10000
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const review = ref<UbaIdentityReview | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const busy = ref<string | null>(null)
const searching = ref<string | null>(null)
const targets = reactive<Record<string, string | null>>({})
const options = reactive<Record<string, { label: string; value: string }[]>>({})
let poll: ReturnType<typeof setInterval> | null = null

const label = identityLabel
const details = identityDetails

function load(quiet = false) {
	if (!quiet) loading.value = true
	error.value = null
	Api.uba
		.getIdentityReview(customerCode)
		.then(res => {
			review.value = res.data
			const queued = res.data.merges.some(m => m.status === "queued")
			if (queued && !poll) poll = setInterval(load, POLL_MS, true)
			if (!queued && poll) {
				clearInterval(poll)
				poll = null
			}
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function search(identityId: string, q: string) {
	if (q.trim().length < 2) return
	searching.value = identityId
	Api.uba
		.searchIdentities(customerCode, q.trim())
		.then(res => {
			options[identityId] = res.data.identities
				.filter(i => i.id !== identityId)
				.map(i => ({ label: `${identityLabel(i)}${i.shadow ? " (learned)" : ""}`, value: i.id }))
		})
		.finally(() => {
			searching.value = null
		})
}

function merge(identityId: string, into: string) {
	busy.value = identityId
	Api.uba
		.mergeIdentity(customerCode, identityId, into)
		.then(() => {
			message.success("Merge queued: UBA runs it within a minute.")
			load(true)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Queuing the merge failed")
		})
		.finally(() => {
			busy.value = null
		})
}

function dismiss(c: UbaMergeCandidate) {
	busy.value = c.identity.id
	Api.uba
		.dismissMergeCandidate(customerCode, c.id)
		.then(() => load(true))
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Dismissing failed")
		})
		.finally(() => {
			busy.value = null
		})
}

function keep(u: UbaIdentitySummary) {
	busy.value = u.id
	Api.uba
		.markIdentityReviewed(customerCode, u.id)
		.then(() => load(true))
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Marking the account failed")
		})
		.finally(() => {
			busy.value = null
		})
}

onBeforeMount(() => load())
onBeforeUnmount(() => {
	if (poll) clearInterval(poll)
})
</script>

<style scoped>
.panel {
	background-color: var(--bg-secondary-color);
}
</style>
