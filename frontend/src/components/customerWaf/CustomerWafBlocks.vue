<template>
	<div class="flex flex-col gap-3">
		<!-- One search for both lists: an address or a word of the reason. -->
		<div class="flex flex-wrap items-center gap-2">
			<n-input
				v-model:value="query"
				size="small"
				clearable
				placeholder="Search IP or description"
				class="w-72!"
				data-testid="waf-blocks-search"
			>
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
			<n-button v-if="canBlock" size="small" type="error" secondary class="ml-auto!" @click="showBlock = true">
				<template #icon><Icon :name="BlockIcon" /></template>
				Block an IP
			</n-button>
		</div>

		<CustomerWafError v-if="error" :error />

		<template v-else>
			<!-- CoPilot's own blocks: the ones an analyst can lift from here. -->
			<section
				class="border-default bg-default overflow-hidden rounded-lg border"
				:aria-busy="loading"
				data-testid="waf-copilot-blocks"
			>
				<header class="bg-secondary border-default flex flex-wrap items-baseline justify-between gap-2 border-b px-4 py-2">
					<span :class="SECTION_LABEL">CoPilot blocks</span>
					<span class="text-tertiary text-2xs font-mono tabular-nums">
						<template v-if="searching">{{ shownCopilot.length }} of {{ copilotBlocks.length }} ·</template>
						{{ activeCount }} active · {{ copilotBlocks.length - activeCount }} lifted
					</span>
				</header>
				<p class="text-tertiary border-default m-0 border-b px-4 py-2 text-xs">
					Unblocking disables the rule rather than deleting it: re-blocking re-enables the same rule, and the
					WAF keeps its history.
				</p>

				<div class="text-tertiary hidden items-center gap-4 px-4 py-2 md:grid" :class="COLUMNS">
					<span :class="HEAD">State</span>
					<span :class="HEAD">Target</span>
					<span :class="HEAD">Reason</span>
					<span :class="HEAD">Rule</span>
					<span :class="HEAD">Created</span>
					<span />
				</div>

				<div v-if="loading" class="flex flex-col gap-2 p-3">
					<n-skeleton v-for="n of 3" :key="n" :height="44" :sharp="false" class="rounded-md" />
				</div>
				<n-empty
					v-else-if="!shownCopilot.length"
					:description="copilotBlocks.length ? 'No block matches the search' : 'CoPilot hasn\'t blocked anything on this WAF'"
					class="min-h-40 justify-center"
				/>
				<div v-else class="divide-border border-default flex flex-col divide-y border-t">
					<div
						v-for="b of shownCopilot"
						:key="b.rule_uuid"
						class="hover:bg-secondary/50 grid items-center gap-x-4 gap-y-1.5 border-l-2 px-4 py-2.5 transition-colors"
						:class="[COLUMNS_ROW, b.enabled ? 'border-l-error' : 'border-l-transparent']"
						data-testid="waf-copilot-block"
					>
						<span><BlockState :active="b.enabled" active-label="blocking" inactive-label="lifted" /></span>
						<span class="text-default truncate font-mono text-sm" :class="{ 'text-tertiary!': !b.enabled }">
							{{ b.target }}
						</span>
						<span class="text-secondary col-span-2 truncate text-xs md:col-span-1" :title="b.description">
							{{ b.description || "—" }}
						</span>
						<span class="text-tertiary hidden font-mono text-xs tabular-nums md:block">#{{ b.rule_id }}</span>
						<CreatedAt :value="b.created_at" class="hidden md:block" />
						<span class="flex justify-end">
							<n-button
								v-if="b.enabled && canBlock"
								size="tiny"
								secondary
								:loading="unblocking === b.target"
								@click="unblock(b.target)"
							>
								<template #icon><Icon :name="LiftedIcon" :size="12" /></template>
								Unblock
							</n-button>
						</span>
					</div>
				</div>
			</section>

			<!-- The WAF's own blocks (e.g. Threat Intel): shown, never changed from here. -->
			<section
				v-if="otherBlocks.length"
				class="border-default bg-default overflow-hidden rounded-lg border"
				data-testid="waf-managed-blocks"
			>
				<button
					type="button"
					class="bg-secondary flex w-full cursor-pointer flex-wrap items-baseline justify-between gap-2 px-4 py-2 text-left"
					:class="{ 'border-default border-b': managedVisible }"
					:aria-expanded="managedVisible"
					data-testid="waf-managed-toggle"
					@click="managedOpen = !managedOpen"
				>
					<span class="flex items-center gap-2">
						<Icon
							:name="ChevronIcon"
							:size="14"
							class="text-tertiary transition-transform duration-200"
							:class="{ '-rotate-90': !managedVisible }"
						/>
						<span :class="SECTION_LABEL">WAF-managed IP blocks</span>
					</span>
					<span class="text-tertiary text-2xs font-mono tabular-nums">
						<template v-if="searching">{{ shownOther.length }} of</template>
						{{ otherBlocks.length }} rules
					</span>
				</button>

				<template v-if="managedVisible">
					<p class="text-tertiary border-default m-0 border-b px-4 py-2 text-xs">
						Created on the WAF itself, e.g. by its Threat Intel. CoPilot respects them but never changes them:
						manage them in the WAF UI.
					</p>
					<div class="text-tertiary hidden items-center gap-4 px-4 py-2 md:grid" :class="COLUMNS">
						<span :class="HEAD">State</span>
						<span :class="HEAD">Target</span>
						<span :class="HEAD">Rule name</span>
						<span :class="HEAD">Rule</span>
						<span :class="HEAD">Created</span>
						<span />
					</div>
					<n-empty
						v-if="!shownOther.length"
						description="No WAF-managed block matches the search"
						class="min-h-32 justify-center"
						size="small"
					/>
					<div v-else class="divide-border border-default flex flex-col divide-y border-t">
						<div
							v-for="b of pagedOther"
							:key="b.rule_uuid"
							class="hover:bg-secondary/50 grid items-center gap-x-4 gap-y-1.5 px-4 py-2 transition-colors"
							:class="COLUMNS_ROW"
							data-testid="waf-managed-block"
						>
							<span><BlockState :active="b.enabled" active-label="enforced" inactive-label="disabled" /></span>
							<span class="text-default truncate font-mono text-sm" :class="{ 'text-tertiary! line-through': !b.enabled }">
								{{ b.target }}
							</span>
							<span class="text-secondary col-span-2 truncate text-xs md:col-span-1" :title="b.description || b.name">
								{{ b.name }}
								<span v-if="b.description && b.description !== b.name" class="text-tertiary">
									· {{ b.description }}
								</span>
							</span>
							<span class="text-tertiary hidden font-mono text-xs tabular-nums md:block">#{{ b.rule_id }}</span>
							<CreatedAt :value="b.created_at" class="hidden md:block" />
							<span />
						</div>
					</div>
					<footer
						v-if="shownOther.length > PAGE_SIZES[0]"
						class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
					>
						<span class="text-tertiary font-mono text-xs tabular-nums">{{ otherRange }}</span>
						<n-pagination
							v-model:page="otherPage"
							v-model:page-size="otherPageSize"
							:item-count="shownOther.length"
							:page-sizes="PAGE_SIZES"
							:page-slot="7"
							show-size-picker
							size="small"
						/>
					</footer>
				</template>
			</section>
		</template>

		<CustomerWafBlockDialog v-model:show="showBlock" :customer-code :instances="[instance]" @blocked="load()" />
	</div>
</template>

<script setup lang="tsx">
import type { ApiError } from "@/types/common"
import type { CustomerWafBlock, CustomerWafInstance } from "@/types/customer-waf"
import { NButton, NEmpty, NInput, NPagination, NSkeleton, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles } from "./utils"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()

const BlockIcon = "carbon:locked"
const LiftedIcon = "carbon:unlocked"
const SearchIcon = "carbon:search"
const ChevronIcon = "carbon:chevron-down"
const PAGE_SIZES = [25, 50, 100]
// One grid for the column heads and every row of both lists, so they line up with each other.
const COLUMNS = "grid-cols-[7rem_10rem_minmax(0,1fr)_5rem_7rem_6rem]"
const COLUMNS_ROW = "grid-cols-[auto_minmax(0,1fr)] md:grid-cols-[7rem_10rem_minmax(0,1fr)_5rem_7rem_6rem]"
const HEAD = "text-2xs font-medium tracking-[0.12em] uppercase"
const dFormats = useSettingsStore().dateFormat

/** A state chip: a word and an icon, coloured only while the block is in force. */
function BlockState(props: { active: boolean; activeLabel: string; inactiveLabel: string }) {
	return (
		<span
			class={[
				"text-2xs inline-flex items-center gap-1 rounded border px-2 py-0.5 font-medium tracking-wide uppercase",
				props.active ? "border-error/40 bg-error/5 text-error" : "border-default text-tertiary"
			]}
		>
			<Icon name={props.active ? BlockIcon : LiftedIcon} size={11} />
			{props.active ? props.activeLabel : props.inactiveLabel}
		</span>
	)
}

// Declared, so kebab-case attributes from the template arrive camelCased.
BlockState.props = ["active", "activeLabel", "inactiveLabel"]

/** When a rule was created: relative, with the exact time on hover. */
function CreatedAt(props: { value: string | null }) {
	if (!props.value) return <span class="text-tertiary text-xs">—</span>
	return (
		<NTooltip>
			{{
				trigger: () => <span class="text-secondary text-xs whitespace-nowrap">{dayjs(props.value).fromNow()}</span>,
				default: () => formatDate(props.value as string, dFormats.datetime)
			}}
		</NTooltip>
	)
}

CreatedAt.props = ["value"]

const message = useMessage()
const loading = ref(false)
const error = ref<ApiError | null>(null)
const copilotBlocks = ref<CustomerWafBlock[]>([])
const otherBlocks = ref<CustomerWafBlock[]>([])
const unblocking = ref<string | null>(null)
const showBlock = ref(false)
const query = ref("")
const managedOpen = ref(false)
const otherPage = ref(1)
const otherPageSize = ref(PAGE_SIZES[0])

const canBlock = computed(() => capabilitiesFromRoles(instance.last_verified_role).can_block)
const activeCount = computed(() => copilotBlocks.value.filter(b => b.enabled).length)
const needle = computed(() => query.value.trim().toLowerCase())
const searching = computed(() => !!needle.value)

/** An address or a word of the reason: the target, the description, and the rule's name. */
function matches(b: CustomerWafBlock) {
	const q = needle.value
	return !q || [b.target, b.description, b.name].some(text => (text ?? "").toLowerCase().includes(q))
}

const shownCopilot = computed(() => copilotBlocks.value.filter(matches))
const shownOther = computed(() => otherBlocks.value.filter(matches))
// Folded by default; a search opens it, so a match there is never hidden behind the fold.
const managedVisible = computed(() => managedOpen.value || searching.value)
const otherOffset = computed(() => (otherPage.value - 1) * otherPageSize.value)
const pagedOther = computed(() => shownOther.value.slice(otherOffset.value, otherOffset.value + otherPageSize.value))
const otherRange = computed(() => {
	const last = Math.min(otherOffset.value + otherPageSize.value, shownOther.value.length)
	return `${(otherOffset.value + 1).toLocaleString()}–${last.toLocaleString()} of ${shownOther.value.length.toLocaleString()}`
})

watch([query, otherPageSize], () => {
	otherPage.value = 1
})

async function load() {
	loading.value = true
	error.value = null
	try {
		const res = await Api.customerWaf.getBlocks(customerCode, instance.id)
		// Active first, then lifted; stable within each group.
		copilotBlocks.value = [...res.data.copilot_blocks].sort((a, b) => Number(b.enabled) - Number(a.enabled))
		otherBlocks.value = [...res.data.other_ip_blocks].sort((a, b) => Number(b.enabled) - Number(a.enabled))
	} catch (err) {
		error.value = err as ApiError
	} finally {
		loading.value = false
	}
}

async function unblock(target: string) {
	unblocking.value = target
	try {
		const res = await Api.customerWaf.unblock(customerCode, instance.id, target)
		message.success(res.data.message)
		await load()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Unblock failed.")
	} finally {
		unblocking.value = null
	}
}

defineExpose({ load })
onBeforeMount(load)
</script>
