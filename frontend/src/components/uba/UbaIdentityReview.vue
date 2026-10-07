<template>
	<UbaSection title="Identity review">
		<template #description>
			Accounts UBA learned from events and the customer's directory users may be the same person. Merging moves
			the account's findings, alerts, history and risk to the person it belongs to; it cannot be undone. UBA runs
			a merge within a minute.
			<template v-if="!isAdmin">Only admins can merge.</template>
		</template>

		<UbaError v-if="error" :error />
		<n-spin v-else :show="loading" class="min-h-16">
			<div v-if="review" class="flex flex-col gap-7">
				<!-- Pairs to merge: what links them, the two identities, the decision. -->
				<div class="flex flex-col gap-2.5" data-testid="uba-review-candidates">
					<header class="flex items-baseline gap-2">
						<span class="text-sm font-semibold">Probably the same person</span>
						<span class="count font-mono text-[11px] tabular-nums">{{ review.candidates.length }}</span>
					</header>
					<p v-if="!review.candidates.length" class="text-secondary m-0 text-xs">
						{{
							review.has_directory
								? "Nothing to review: the directory sync found no account that another identity already owns."
								: "Merge suggestions come from a directory sync, and none is connected for this customer."
						}}
					</p>
					<article
						v-for="c of review.candidates"
						:key="c.id"
						class="panel border-default @container overflow-hidden rounded-lg border"
						data-testid="uba-review-candidate"
					>
						<header
							class="pair-head border-default flex flex-wrap items-center gap-x-3 gap-y-2 border-b px-3 py-2"
						>
							<div class="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
								<Icon name="carbon:link" :size="14" class="text-primary shrink-0" />
								<span class="text-secondary text-xs">Both claim</span>
								<span class="shared-alias flex min-w-0 items-center gap-1.5 font-mono text-xs">
									<span v-if="splitAlias(c.alias).type" class="shared-type text-[10px]">
										{{ splitAlias(c.alias).type }}
									</span>
									<span class="truncate" :title="splitAlias(c.alias).value">
										{{ splitAlias(c.alias).value }}
									</span>
								</span>
								<span class="text-tertiary font-mono text-[11px]">{{ linkOrigin(c) }}</span>
							</div>
							<div v-if="isAdmin" class="flex shrink-0 gap-2">
								<n-button
									size="small"
									quaternary
									:disabled="busy === c.identity.id"
									@click="dismiss(c)"
								>
									Not the same
								</n-button>
								<n-popconfirm @positive-click="merge(c.identity.id, c.candidate.id)">
									<template #trigger>
										<n-button
											size="small"
											type="primary"
											secondary
											:loading="busy === c.identity.id"
										>
											Merge
										</n-button>
									</template>
									Merge {{ label(c.identity) }} into {{ label(c.candidate) }}? This cannot be undone.
								</n-popconfirm>
							</div>
						</header>
						<div class="grid items-start gap-3 px-3 py-3 @2xl:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
							<IdentityCard
								caption="Learned from events"
								:identity="c.identity"
								:shared-alias="c.alias"
							/>
							<span
								class="merge-arrow grid size-7 place-items-center self-center rounded-full"
								title="merges into"
							>
								<!-- The icon's own display beats a utility class: hide its wrapper instead. -->
								<span class="flex @2xl:hidden"><Icon name="carbon:arrow-down" :size="14" /></span>
								<span class="hidden @2xl:flex"><Icon name="carbon:arrow-right" :size="14" /></span>
							</span>
							<IdentityCard caption="Directory user" :identity="c.candidate" :shared-alias="c.alias" />
						</div>
					</article>
				</div>

				<!-- Accounts no directory user matched: the account, then merge-into or keep. -->
				<div v-if="review.has_directory" class="flex flex-col gap-2.5" data-testid="uba-review-unmatched">
					<header class="flex flex-col gap-1">
						<div class="flex items-baseline gap-2">
							<span class="text-sm font-semibold">Accounts not matched to the directory</span>
							<span class="count font-mono text-[11px] tabular-nums">{{ review.unmatched.length }}</span>
						</div>
						<p class="text-secondary m-0 text-xs">
							With findings in the last 14 days. Merge one into the person it belongs to, or keep it as it
							is (for example a local or service account).
						</p>
					</header>
					<article
						v-for="u of review.unmatched"
						:key="u.id"
						class="panel border-default @container rounded-lg border px-3 py-2.5"
						data-testid="uba-review-account"
					>
						<div class="flex flex-col gap-3 @3xl:flex-row @3xl:items-center">
							<IdentityCard :identity="u" :max-aliases="2" class="flex-1" />
							<div
								v-if="isAdmin"
								class="flex flex-wrap items-center gap-2 @3xl:shrink-0 @3xl:flex-nowrap"
							>
								<n-button size="small" quaternary :disabled="busy === u.id" @click="keep(u)">
									Keep as is
								</n-button>
								<!-- naive-ui sizes its select to 100% of its parent: the wrapper sets the width. -->
								<div class="min-w-0 flex-1 @3xl:w-64 @3xl:flex-none">
									<n-select
										v-model:value="targets[u.id]"
										size="small"
										filterable
										remote
										clearable
										placeholder="Merge into… (search a name)"
										:options="options[u.id] ?? []"
										:loading="searching === u.id"
										@search="q => search(u.id, q)"
									/>
								</div>
								<n-popconfirm @positive-click="merge(u.id, targets[u.id] ?? '')">
									<template #trigger>
										<n-button
											size="small"
											type="primary"
											secondary
											:disabled="!targets[u.id]"
											:loading="busy === u.id"
										>
											Merge
										</n-button>
									</template>
									Merge {{ label(u) }} into the selected identity? This cannot be undone.
								</n-popconfirm>
							</div>
						</div>
					</article>
				</div>

				<!-- Merges already asked for: status, from → into, who and when, and why one failed. -->
				<div v-if="review.merges.length" class="flex flex-col gap-2.5" data-testid="uba-review-merges">
					<header class="flex items-baseline gap-2">
						<span class="text-sm font-semibold">Recent merges</span>
						<span class="count font-mono text-[11px] tabular-nums">{{ review.merges.length }}</span>
					</header>
					<ul class="panel border-default @container m-0 list-none overflow-hidden rounded-lg border p-0">
						<li
							v-for="m of review.merges"
							:key="m.id"
							class="merge-row grid items-center gap-x-3 gap-y-1 px-3 py-2 @2xl:grid-cols-[96px_minmax(0,1fr)_auto]"
							data-testid="uba-review-merge"
						>
							<n-tag
								size="small"
								round
								:type="MERGE_STATUS[m.status].type"
								:bordered="false"
								class="justify-self-start"
							>
								<template #icon><Icon :name="MERGE_STATUS[m.status].icon" :size="12" /></template>
								{{ MERGE_STATUS[m.status].label }}
							</n-tag>
							<span class="flex min-w-0 items-center gap-2 text-sm">
								<span
									class="text-secondary truncate font-mono text-xs"
									:title="m.from_name || m.from_identity"
								>
									{{ m.from_name || m.from_identity }}
								</span>
								<Icon name="carbon:arrow-right" :size="12" class="text-tertiary shrink-0" />
								<span class="truncate font-medium" :title="m.into_name || m.into_identity">
									{{ m.into_name || m.into_identity }}
								</span>
							</span>
							<span
								class="text-tertiary font-mono text-[11px] whitespace-nowrap"
								:title="
									m.requested_at ? String(formatDate(m.requested_at, dFormats.datetime)) : undefined
								"
							>
								{{ requested(m) }}
							</span>
							<p v-if="m.error" class="text-error col-span-full m-0 text-xs @2xl:col-start-2">
								{{ m.error }}
							</p>
						</li>
					</ul>
				</div>
			</div>
		</n-spin>
	</UbaSection>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaIdentityMerge, UbaIdentityReview, UbaIdentitySummary, UbaMergeCandidate } from "@/types/uba"
import { NButton, NPopconfirm, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import IdentityCard from "./ui/IdentityCard.vue"
import UbaSection from "./ui/UbaSection.vue"
import { identityLabel, identitySourceLabel, splitAlias } from "./utils"

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

/** Where the shared alias was found and for how long: "Entra ID (directory sync) · for 6 days". */
function linkOrigin(c: UbaMergeCandidate): string {
	const source = identitySourceLabel(c.source)
	return c.first_seen ? `${source} · for ${dayjs(c.first_seen).fromNow(true)}` : source
}

/** Who asked for a merge and when: "admin1 · 2 hours ago". */
function requested(m: UbaIdentityMerge): string {
	return [m.requested_by, m.requested_at ? dayjs(m.requested_at).fromNow() : null].filter(Boolean).join(" · ")
}

/** How a merge's status reads: an icon and a word, always with the colour. */
const MERGE_STATUS: Record<
	UbaIdentityMerge["status"],
	{ icon: string; label: string; type: "default" | "success" | "error" }
> = {
	queued: { icon: "carbon:time", label: "queued", type: "default" },
	done: { icon: "carbon:checkmark-filled", label: "merged", type: "success" },
	error: { icon: "carbon:warning-filled", label: "failed", type: "error" }
}

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

.count {
	padding: 0 6px;
	border-radius: 999px;
	color: var(--fg-secondary-color);
	background-color: var(--hover-color);
}

.pair-head {
	background-color: var(--bg-default-color);
}

.shared-alias {
	color: var(--primary-color);
}

.shared-type {
	padding: 0 5px;
	border-radius: 4px;
	line-height: 1.6;
	background-color: rgb(var(--primary-color-rgb) / 0.12);
}

.merge-arrow {
	justify-self: start;
	color: var(--fg-secondary-color);
	border: 1px solid var(--border-color);
	background-color: var(--bg-default-color);
}

.merge-row + .merge-row {
	border-top: 1px solid var(--border-color);
}
</style>
