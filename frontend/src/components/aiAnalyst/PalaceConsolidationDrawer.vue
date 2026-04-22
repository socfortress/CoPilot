<template>
	<n-drawer v-model:show="showLocal" :width="640" placement="right">
		<n-drawer-content closable>
			<template #header>
				Palace consolidation
				<span v-if="customerCode" class="text-secondary ml-2 text-sm">· {{ customerCode }}</span>
			</template>

			<n-spin :show="loading" class="min-h-40">
				<div v-if="!customerCode" class="pt-6 text-center">
					<n-empty description="Select a customer first" />
				</div>

				<div v-else-if="!data && !loading" class="flex flex-col items-center gap-3 pt-6">
					<n-empty description="No digest yet" />
				</div>

				<div v-else-if="data" class="flex flex-col gap-4">
					<!-- Summary tiles -->
					<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
						<CardEntity size="small" embedded>
							<template #default>
								<div class="flex flex-col gap-1">
									<div class="text-secondary text-xs tracking-wide uppercase">Active</div>
									<div class="text-2xl font-semibold">{{ data.total_lessons }}</div>
									<div class="text-secondary text-xs">{{ data.total_pending }} pending</div>
								</div>
							</template>
						</CardEntity>
						<CardEntity size="small" embedded>
							<template #default>
								<div class="flex flex-col gap-1">
									<div class="text-secondary text-xs tracking-wide uppercase">Durable</div>
									<div class="text-2xl font-semibold text-success">{{ data.total_durable }}</div>
									<div class="text-secondary text-xs">never expire</div>
								</div>
							</template>
						</CardEntity>
						<CardEntity size="small" embedded>
							<template #default>
								<div class="flex flex-col gap-1">
									<div class="text-secondary text-xs tracking-wide uppercase">One-off</div>
									<div class="text-2xl font-semibold text-warning">{{ data.total_one_off }}</div>
									<div class="text-secondary text-xs">7-day TTL</div>
								</div>
							</template>
						</CardEntity>
						<CardEntity size="small" embedded>
							<template #default>
								<div class="flex flex-col gap-1">
									<div class="text-secondary text-xs tracking-wide uppercase">Duplicates</div>
									<div
										class="text-2xl font-semibold"
										:class="data.duplicate_candidates.length ? 'text-warning' : ''"
									>
										{{ data.duplicate_candidates.length }}
									</div>
									<div class="text-secondary text-xs">near-dupe pairs</div>
								</div>
							</template>
						</CardEntity>
					</div>

					<!-- Upcoming expirations -->
					<CardEntity v-if="data.upcoming_expirations.length" size="small" embedded highlighted>
						<template #headerMain>
							<Icon :name="WarningIcon" :size="14" class="text-warning mr-1" />
							Expiring soon ({{ data.upcoming_expirations.length }})
						</template>
						<template #default>
							<div class="flex flex-col gap-2">
								<div
									v-for="ls of data.upcoming_expirations"
									:key="ls.id"
									class="border-color bg-secondary rounded border p-2 text-sm"
								>
									<div class="mb-1 flex flex-wrap items-center gap-2">
										<Badge type="splitted" bright color="warning">
											<template #label>{{ ls.lesson_type }}</template>
											<template #value>{{ expiryLabel(ls.days_until_expiry) }}</template>
										</Badge>
										<span class="text-secondary text-xs">id {{ ls.id }}</span>
									</div>
									<div class="break-words whitespace-pre-wrap">{{ ls.lesson_text }}</div>
								</div>
							</div>
						</template>
					</CardEntity>

					<!-- Near-duplicate pairs -->
					<CardEntity v-if="data.duplicate_candidates.length" size="small" embedded>
						<template #headerMain>
							Near-duplicate candidates ({{ data.duplicate_candidates.length }})
						</template>
						<template #default>
							<div class="flex flex-col gap-2">
								<div
									v-for="pair of data.duplicate_candidates"
									:key="`${pair.lesson_a_id}-${pair.lesson_b_id}`"
									class="border-color bg-secondary rounded border p-2 text-sm"
								>
									<div class="mb-1 flex flex-wrap items-center gap-2">
										<Badge
											type="splitted"
											bright
											:color="simColor(pair.similarity)"
										>
											<template #label>{{ pair.room }}</template>
											<template #value>{{ Math.round(pair.similarity * 100) }}%</template>
										</Badge>
									</div>
									<div class="mb-1">
										<span class="text-secondary text-xs">#{{ pair.lesson_a_id }}</span>
										<span class="ml-1 break-words whitespace-pre-wrap">{{ pair.lesson_a_text }}</span>
									</div>
									<div>
										<span class="text-secondary text-xs">#{{ pair.lesson_b_id }}</span>
										<span class="ml-1 break-words whitespace-pre-wrap">{{ pair.lesson_b_text }}</span>
									</div>
								</div>
							</div>
						</template>
					</CardEntity>

					<!-- Per-room breakdown -->
					<CardEntity size="small" embedded>
						<template #headerMain>By room</template>
						<template #default>
							<n-empty
								v-if="!data.rooms.length"
								description="No active lessons"
								class="min-h-20 justify-center"
							/>
							<n-collapse v-else>
								<n-collapse-item
									v-for="group of data.rooms"
									:key="group.room"
									:name="group.room"
								>
									<template #header>
										<div class="flex items-center gap-2">
											<span class="font-medium">{{ group.room }}</span>
											<Badge type="splitted">
												<template #label>Total</template>
												<template #value>{{ group.total }}</template>
											</Badge>
											<Badge type="splitted" color="success">
												<template #label>Durable</template>
												<template #value>{{ group.durable }}</template>
											</Badge>
											<Badge type="splitted" color="warning">
												<template #label>One-off</template>
												<template #value>{{ group.one_off }}</template>
											</Badge>
										</div>
									</template>
									<div class="flex flex-col gap-2">
										<div
											v-for="ls of group.lessons"
											:key="ls.id"
											class="border-color bg-secondary rounded border p-2 text-sm"
										>
											<div class="mb-1 flex flex-wrap items-center gap-2">
												<Badge
													type="splitted"
													:color="ls.durability === 'durable' ? 'success' : 'warning'"
												>
													<template #label>{{ ls.durability }}</template>
													<template #value>
														{{ ls.durability === "one_off"
															? expiryLabel(ls.days_until_expiry)
															: "∞" }}
													</template>
												</Badge>
												<Badge type="splitted" :color="statusColor(ls.status)">
													<template #label>Status</template>
													<template #value>{{ ls.status }}</template>
												</Badge>
												<span class="text-secondary text-xs">
													id {{ ls.id }} · {{ formatDate(ls.created_at, "MMM D") }}
												</span>
											</div>
											<div class="break-words whitespace-pre-wrap">{{ ls.lesson_text }}</div>
										</div>
									</div>
								</n-collapse-item>
							</n-collapse>
						</template>
					</CardEntity>

					<div class="text-secondary text-xs">
						Generated {{ formatDate(data.generated_at, "MMM D, YYYY HH:mm") }} UTC
					</div>
				</div>
			</n-spin>

			<template #footer>
				<div class="flex w-full items-center justify-between gap-2">
					<div class="text-secondary text-xs">
						<template v-if="data">
							{{ data.total_lessons }} lesson(s) · {{ data.rooms.length }} room(s)
						</template>
					</div>
					<div class="flex items-center gap-2">
						<n-button
							size="small"
							:disabled="!data || !data.markdown"
							@click="copyMarkdown"
						>
							<template #icon>
								<Icon :name="CopyIcon" :size="14" />
							</template>
							Copy markdown
						</n-button>
						<n-button
							size="small"
							:disabled="!customerCode || loading"
							@click="load()"
						>
							<template #icon>
								<Icon :name="RefreshIcon" :size="14" />
							</template>
							Refresh
						</n-button>
					</div>
				</div>
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { PalaceConsolidation } from "@/types/aiAnalyst.d"
import { NButton, NCollapse, NCollapseItem, NDrawer, NDrawerContent, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	show: boolean
	customerCode: string | null
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
}>()

const RefreshIcon = "carbon:renew"
const CopyIcon = "carbon:copy"
const WarningIcon = "carbon:warning"

const message = useMessage()

// v-model:show bridge — local ref mirrors the prop so the drawer's
// internal close button also propagates back to the parent.
const showLocal = computed({
	get: () => props.show,
	set: (v: boolean) => emit("update:show", v)
})

const loading = ref(false)
const data = ref<PalaceConsolidation | null>(null)

function simColor(sim: number): "success" | "warning" | "danger" {
	// Similarity is always >= threshold (0.7) when flagged — calibrate bands
	// for "probably rewrite" vs "review manually" at a glance.
	if (sim >= 0.9) return "danger"
	if (sim >= 0.8) return "warning"
	return "success"
}

function statusColor(status: string): "success" | "warning" | "danger" | undefined {
	if (status === "ingested") return "success"
	if (status === "pending") return "warning"
	if (status === "failed") return "danger"
	return undefined
}

function expiryLabel(days: number | null): string {
	if (days == null) return "—"
	if (days <= 0) return "due"
	if (days === 1) return "1d"
	return `${days}d`
}

async function load() {
	if (!props.customerCode) {
		data.value = null
		return
	}
	loading.value = true
	try {
		const res = await Api.aiAnalyst.getPalaceConsolidation(props.customerCode)
		if (res.data.success) {
			data.value = res.data
		} else {
			message.warning(res.data.message || "Failed to build consolidation")
			data.value = null
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to build consolidation")
		data.value = null
	} finally {
		loading.value = false
	}
}

async function copyMarkdown() {
	if (!data.value?.markdown) return
	try {
		await navigator.clipboard.writeText(data.value.markdown)
		message.success("Markdown copied to clipboard")
	} catch {
		message.error("Clipboard unavailable — select + copy from the drawer body")
	}
}

// Auto-load on open (and reload if customer changes while open).
// NB: don't destructure oldValue in the handler — on `immediate: true` the
// initial oldValue is `undefined`, which throws on tuple destructure and
// crashes setup, which Vue's error-recovery retries → infinite remount loop.
watch(
	() => [props.show, props.customerCode] as const,
	(curr, prev) => {
		const [show, code] = curr
		const prevShow = prev ? prev[0] : false
		if (show && code && (!prevShow || data.value?.customer_code !== code)) {
			load()
		}
		// When show flips back to false we keep the previous data around so
		// re-opening feels instant; reset only when the customer changes.
	},
	{ immediate: true }
)
</script>
