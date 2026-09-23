<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="text-secondary max-w-2xl text-xs">
				IP blocks CoPilot created on this WAF. Unblocking disables the rule rather than deleting it, so
				re-blocking re-enables the same rule and the WAF keeps its history.
			</p>
			<n-button v-if="canBlock" size="small" type="error" secondary @click="showBlock = true">
				<template #icon><Icon :name="BlockIcon" /></template>
				Block an IP
			</n-button>
		</div>

		<CustomerWafError v-if="error" :error />

		<section v-else class="border-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<header class="bg-secondary border-default flex items-baseline justify-between gap-2 border-b px-3 py-2">
				<span :class="SECTION_LABEL">CoPilot blocks</span>
				<span class="text-tertiary text-2xs">{{ activeCount }} active · {{ copilotBlocks.length - activeCount }} lifted</span>
			</header>
			<div v-if="loading" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 3" :key="n" :height="40" :sharp="false" class="rounded-md" />
			</div>
			<n-empty v-else-if="!copilotBlocks.length" description="CoPilot hasn't blocked anything on this WAF" class="min-h-40 justify-center" />
			<ul v-else class="divide-border flex flex-col divide-y">
				<li
					v-for="b of copilotBlocks"
					:key="b.rule_uuid"
					class="hover:bg-secondary/60 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-3 py-2 transition-colors"
					:class="{ 'opacity-60': !b.enabled }"
				>
					<n-tag size="small" round :bordered="false" :type="b.enabled ? 'error' : 'default'" class="min-w-24 justify-center">
						<template #icon><Icon :name="b.enabled ? BlockIcon : LiftedIcon" :size="12" /></template>
						{{ b.enabled ? "blocking" : "lifted" }}
					</n-tag>
					<div class="flex min-w-0 flex-col">
						<span class="font-mono text-sm">{{ b.target }}</span>
						<span class="text-secondary truncate text-xs">{{ b.description || "—" }}</span>
					</div>
					<div class="flex items-center gap-3">
						<span class="text-tertiary hidden font-mono text-xs sm:inline">rule {{ b.rule_id }}</span>
						<n-button
							v-if="b.enabled && canBlock"
							size="tiny"
							secondary
							:loading="unblocking === b.target"
							@click="unblock(b.target)"
						>
							Unblock
						</n-button>
					</div>
				</li>
			</ul>
		</section>

		<CollapsibleCard v-if="otherBlocks.length" default-collapsed>
			<template #header>
				<span :class="SECTION_LABEL">WAF-managed IP blocks ({{ otherBlocks.length }})</span>
			</template>
			<div class="flex flex-col gap-2 p-3">
				<p class="text-secondary text-xs">
					Created on the WAF itself, e.g. its Threat Intel blocks. CoPilot respects them but never changes them;
					manage them in the WAF UI.
				</p>
				<div class="flex flex-wrap gap-1.5">
					<n-tooltip v-for="b of otherBlocks" :key="b.rule_uuid">
						<template #trigger>
							<span
								class="border-default bg-secondary rounded-md border px-2 py-0.5 font-mono text-xs"
								:class="{ 'line-through opacity-50': !b.enabled }"
							>
								{{ b.target }}
							</span>
						</template>
						{{ b.name }} · rule {{ b.rule_id }}{{ b.enabled ? "" : " · disabled" }}
					</n-tooltip>
				</div>
			</div>
		</CollapsibleCard>

		<CustomerWafBlockDialog v-model:show="showBlock" :customer-code :instances="[instance]" @blocked="load()" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafBlock, CustomerWafInstance } from "@/types/customer-waf"
import { NButton, NEmpty, NSkeleton, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { getApiErrorMessage } from "@/utils"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles } from "./utils"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()

const BlockIcon = "carbon:locked"
const LiftedIcon = "carbon:unlocked"
const message = useMessage()
const loading = ref(false)
const error = ref<ApiError | null>(null)
const copilotBlocks = ref<CustomerWafBlock[]>([])
const otherBlocks = ref<CustomerWafBlock[]>([])
const unblocking = ref<string | null>(null)
const showBlock = ref(false)

const canBlock = computed(() => capabilitiesFromRoles(instance.last_verified_role).can_block)
const activeCount = computed(() => copilotBlocks.value.filter(b => b.enabled).length)

function load() {
	loading.value = true
	error.value = null
	Api.customerWaf
		.getBlocks(customerCode, instance.id)
		.then(res => {
			// Active first, then lifted; stable within each group.
			copilotBlocks.value = [...res.data.copilot_blocks].sort((a, b) => Number(b.enabled) - Number(a.enabled))
			otherBlocks.value = res.data.other_ip_blocks
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function unblock(target: string) {
	unblocking.value = target
	Api.customerWaf
		.unblock(customerCode, instance.id, target)
		.then(res => {
			message.success(res.data.message)
			load()
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Unblock failed.")
		})
		.finally(() => {
			unblocking.value = null
		})
}

defineExpose({ load })
onBeforeMount(load)
</script>
