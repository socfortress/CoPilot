<template>
	<div class="flex min-h-40 flex-col gap-4">
		<n-spin :show="loading" class="grow">
			<div v-if="!data && !loading" class="flex flex-col items-center gap-3 pt-6">
				<n-empty description="No digest yet" />
			</div>

			<div v-else-if="data" class="@container flex flex-col gap-4">
				<!-- Summary tiles -->
				<div class="grid gap-3 @sm:grid-cols-2 @xl:grid-cols-4">
					<CardLink
						v-for="tile of summaryTiles"
						:key="tile.title"
						embedded
						size="small"
						:title="tile.title"
						:value="tile.value"
						:subtitle="tile.subtitle"
						:color="tile.color"
					/>
				</div>

				<!-- Upcoming expirations -->
				<CardEntity v-if="data.upcoming_expirations.length" size="small" embedded highlighted>
					<template #headerMain>
						<Icon :name="WarningIcon" :size="14" class="text-warning relative top-0.5 mr-1" />
						Expiring soon ({{ data.upcoming_expirations.length }})
					</template>
					<template #default>
						<div class="flex flex-col gap-2">
							<CardEntity v-for="ls of data.upcoming_expirations" :key="ls.id" size="small">
								<template #header>
									<div class="text-default flex flex-wrap items-center gap-2">
										<Badge type="splitted" bright size="small">
											<template #label>ID</template>
											<template #value>{{ ls.id }}</template>
										</Badge>
										<Badge type="splitted" color="warning" size="small">
											<template #label>{{ ls.lesson_type }}</template>
											<template #value>{{ expiryLabel(ls.days_until_expiry) }}</template>
										</Badge>
									</div>
								</template>
								<template #default>
									<div class="text-sm">
										{{ ls.lesson_text }}
									</div>
								</template>
							</CardEntity>
						</div>
					</template>
				</CardEntity>

				<!-- Near-duplicate pairs -->
				<CardEntity v-if="data.duplicate_candidates.length" size="small" embedded>
					<template #headerMain>Near-duplicate candidates ({{ data.duplicate_candidates.length }})</template>
					<template #default>
						<div class="flex flex-col gap-2">
							<CardEntity
								v-for="pair of data.duplicate_candidates"
								:key="`${pair.lesson_a_id}-${pair.lesson_b_id}`"
								size="small"
							>
								<template #header>
									<div class="text-default flex flex-wrap items-center gap-2">
										<Badge type="splitted" bright :color="simColor(pair.similarity)" size="small">
											<template #label>{{ pair.room }}</template>
											<template #value>{{ Math.round(pair.similarity * 100) }}%</template>
										</Badge>
									</div>
								</template>
								<template #default>
									<dl class="mt-1 flex flex-col gap-2">
										<div class="flex flex-col gap-1">
											<dt class="text-secondary font-mono text-[10px] tracking-wider uppercase">
												Lesson {{ pair.lesson_a_id }}
											</dt>
											<dd
												class="text-default font-mono text-xs leading-snug wrap-break-word whitespace-pre-wrap"
											>
												{{ pair.lesson_a_text }}
											</dd>
										</div>
										<div class="border-border flex flex-col gap-1 border-t pt-3">
											<dt class="text-secondary font-mono text-[10px] tracking-wider uppercase">
												Lesson {{ pair.lesson_b_id }}
											</dt>
											<dd
												class="text-default font-mono text-xs leading-snug wrap-break-word whitespace-pre-wrap"
											>
												{{ pair.lesson_b_text }}
											</dd>
										</div>
									</dl>
								</template>
							</CardEntity>
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
							<n-collapse-item v-for="group of data.rooms" :key="group.room" :name="group.room">
								<template #header>
									<div class="flex w-full flex-wrap items-center justify-between gap-2">
										<span class="font-medium">{{ group.room }}</span>
										<div class="ml-auto flex flex-wrap items-center gap-2">
											<Badge type="splitted" size="small">
												<template #label>Total</template>
												<template #value>{{ group.total }}</template>
											</Badge>
											<Badge type="splitted" color="success" size="small">
												<template #label>Durable</template>
												<template #value>{{ group.durable }}</template>
											</Badge>
											<Badge type="splitted" color="warning" size="small">
												<template #label>One-off</template>
												<template #value>{{ group.one_off }}</template>
											</Badge>
										</div>
									</div>
								</template>
								<div class="flex flex-col gap-2">
									<CardEntity v-for="ls of group.lessons" :key="ls.id" size="small">
										<template #default>
											<div class="flex flex-wrap items-center gap-2">
												<Badge
													type="splitted"
													size="small"
													:color="ls.durability === 'durable' ? 'success' : 'warning'"
												>
													<template #label>{{ ls.durability }}</template>
													<template #value>
														{{
															ls.durability === "one_off"
																? expiryLabel(ls.days_until_expiry)
																: "∞"
														}}
													</template>
												</Badge>
												<Badge type="splitted" size="small" :color="statusColor(ls.status)">
													<template #label>Status</template>
													<template #value>{{ ls.status }}</template>
												</Badge>
												<Badge type="splitted" size="small">
													<template #label>ID</template>
													<template #value>{{ ls.id }}</template>
												</Badge>
												<Badge type="splitted" size="small">
													<template #label>Created at</template>
													<template #value>
														{{ formatDate(ls.created_at, dFormats.date) }}
													</template>
												</Badge>
											</div>
										</template>
										<template #mainExtra>
											<div class="text-sm">
												{{ ls.lesson_text }}
											</div>
										</template>
									</CardEntity>
								</div>
							</n-collapse-item>
						</n-collapse>
					</template>
				</CardEntity>

				<n-collapse>
					<n-collapse-item title="Markdown" name="markdown">
						<CodeSource :code="data.markdown" lang="markdown" :max-height="500" />
					</n-collapse-item>
				</n-collapse>

				<p class="text-xs">Generated {{ formatDate(data.generated_at, dFormats.datetime) }} UTC</p>
			</div>
		</n-spin>

		<div class="border-border flex w-full items-center justify-between gap-2 border-t pt-4">
			<p class="text-sm">
				<template v-if="data">{{ data.total_lessons }} lesson(s) · {{ data.rooms.length }} room(s)</template>
			</p>
			<div class="flex items-center gap-2">
				<n-button size="small" :loading @click="load()">
					<template #icon>
						<Icon :name="RefreshIcon" :size="14" />
					</template>
					Refresh
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { PalaceConsolidation } from "@/types/aiAnalyst.d"
import { NButton, NCollapse, NCollapseItem, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	customerCode: string
}>()

const dFormats = useSettingsStore().dateFormat
const RefreshIcon = "carbon:renew"
const WarningIcon = "carbon:warning"

const message = useMessage()

const loading = ref(false)
const data = ref<PalaceConsolidation | null>(null)

interface SummaryTile {
	title: string
	value: number
	subtitle: string
	color?: CardLinkColor
}

const summaryTiles = computed<SummaryTile[]>(() => {
	const d = data.value
	if (!d) return []

	return [
		{ title: "Active", value: d.total_lessons, subtitle: `${d.total_pending} pending` },
		{ title: "Durable", value: d.total_durable, subtitle: "never expire", color: "success" },
		{ title: "One-off", value: d.total_one_off, subtitle: "7-day TTL", color: "warning" },
		{
			title: "Duplicates",
			value: d.duplicate_candidates.length,
			subtitle: "near-dupe pairs",
			color: d.duplicate_candidates.length ? "warning" : undefined
		}
	]
})

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

watch(
	() => props.customerCode,
	(code, prevCode) => {
		if (code && code !== prevCode) {
			load()
		}
	},
	{ immediate: true }
)
</script>
