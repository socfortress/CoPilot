<template>
	<section
		v-if="sla"
		class="item-sla border-default bg-secondary flex flex-col gap-3 rounded-lg border px-4 py-3"
		:data-testid="`item-sla-${entity}`"
		aria-label="Service level"
	>
		<header class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<Icon name="carbon:timer" :size="15" class="text-secondary" />
				<span :class="SECTION_LABEL">Service level</span>
				<SeverityTag :severity="sla.severity" />
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<n-tag
					v-if="sla.paused_at"
					size="small"
					round
					:bordered="false"
					data-testid="item-sla-paused"
					:title="`Waiting since ${formatWhen(sla.paused_at)}`"
				>
					<template #icon><Icon name="carbon:pause-outline" :size="12" /></template>
					Waiting on customer · clocks stopped
				</n-tag>
				<span
					v-else-if="sla.paused_seconds"
					class="text-tertiary font-mono text-xs"
					data-testid="item-sla-waited"
					title="Time spent waiting on the customer: not counted against the SOC"
				>
					waited {{ formatDuration(sla.paused_seconds) }}
				</span>
				<n-tag
					v-if="sla.business_hours"
					size="small"
					round
					:bordered="false"
					type="info"
					data-testid="item-sla-business-hours"
				>
					<template #icon><Icon name="carbon:calendar" :size="12" /></template>
					Business hours{{ sla.calendar_timezone ? ` · ${sla.calendar_timezone}` : "" }}
				</n-tag>
				<span v-if="sla.reopen_count" class="text-tertiary font-mono text-xs">
					reopened {{ sla.reopen_count }}×
				</span>
			</div>
		</header>

		<p v-if="!sla.tracked" class="text-tertiary m-0 text-xs">
			This {{ entity }} opened before SLA tracking began, so it carries no clock.
		</p>
		<div v-else class="grid gap-3 md:grid-cols-2">
			<div
				v-for="clock of clocks"
				:key="clock.key"
				class="flex flex-col gap-1.5"
				:data-testid="`item-sla-${clock.key}`"
			>
				<div class="flex items-center justify-between gap-2">
					<span class="text-secondary text-xs">{{ clock.title }}</span>
					<SlaStateTag :state="clock.state" />
				</div>
				<div
					class="clock-track h-1 overflow-hidden rounded-full"
					:style="{ backgroundColor: 'var(--border-color)' }"
					role="progressbar"
					:aria-valuenow="Math.round(clock.used)"
					aria-valuemin="0"
					aria-valuemax="100"
					:aria-label="`${clock.title}: ${Math.round(clock.used)}% of the target used`"
				>
					<div
						class="h-full rounded-full"
						:style="{ width: `${Math.min(100, clock.used)}%`, backgroundColor: clock.color }"
					/>
				</div>
				<span class="text-tertiary font-mono text-xs">{{ clock.detail }}</span>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
// The SLA of one alert or case, on its own page: the response and resolution clocks,
// how much of each target has been used, and who stopped them. Hidden — not an error —
// when the caller cannot read SLA data (portal users) or the request fails: it adds
// context to the page, it is not what the page is for.
import type { ItemSla, SlaClock, SlaEntity } from "@/types/soc-management"
import { NTag } from "naive-ui"
import { computed, shallowRef, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import SeverityTag from "./ui/SeverityTag.vue"
import SlaStateTag from "./ui/SlaStateTag.vue"
import { formatDuration, formatTarget, parseUtc, SLA_STATE_META, TONE_COLOR } from "./utils"

const {
	entity,
	itemId,
	refreshKey = ""
} = defineProps<{
	entity: SlaEntity
	itemId: number
	/** Changes whenever the item changes (status, assignee…), so the clocks reload. */
	refreshKey?: string
}>()

const emit = defineEmits<{ (e: "loaded", value: ItemSla | null): void }>()

const sla = shallowRef<ItemSla | null>(null)

watch(
	() => `${entity}:${itemId}:${refreshKey}`,
	async (_key, _old, onCleanup) => {
		const controller = new AbortController()
		onCleanup(() => controller.abort())
		try {
			sla.value = (await Api.socManagement.getItemSla(entity, itemId, controller.signal)).data
		} catch {
			if (controller.signal.aborted) return
			sla.value = null
		}
		emit("loaded", sla.value)
	},
	{ immediate: true }
)

function formatWhen(value: string | null): string {
	return parseUtc(value)?.local().format("ddd DD MMM, HH:mm") ?? "—"
}

/**
 * "12m of 1h · ana" once met or late; while running, "6h 20m left of 8h" — or, on
 * business hours, the due time itself: a countdown in wall-clock time would read
 * "64h left" over a weekend for a target of four working hours.
 */
function clockDetail(clock: SlaClock, openedAt: number, now: number, businessHours: boolean): string {
	const due = parseUtc(clock.due_at)?.valueOf() ?? null
	const achieved = parseUtc(clock.achieved_at)?.valueOf() ?? null
	const target = formatTarget(clock.target_minutes)
	if (clock.state === "not_tracked") return "no target for this severity"
	if (achieved != null)
		return `${formatDuration((achieved - openedAt) / 1000)} of ${target}${clock.by ? ` · ${clock.by}` : ""}`
	if (due == null) return "—"
	if (clock.state === "paused") return `stopped · ${target} target`
	if (now > due) return `${formatDuration((now - due) / 1000)} past ${target}`
	if (businessHours) return `due ${formatWhen(clock.due_at)} · ${target} working`
	return `${formatDuration((due - now) / 1000)} left of ${target}`
}

/**
 * How much of the window to the due time is used. Measured against the due time
 * rather than the target, so a business-hours window or one pushed back by waiting
 * on the customer still fills to exactly 100% when it falls due; a paused clock
 * stays where it stopped.
 */
function usedPercent(clock: SlaClock, openedAt: number, now: number, pausedAt: number | null): number {
	const due = parseUtc(clock.due_at)?.valueOf() ?? null
	if (due == null || due <= openedAt) return 0
	const reached = parseUtc(clock.achieved_at)?.valueOf() ?? pausedAt ?? now
	return Math.max(0, ((reached - openedAt) / (due - openedAt)) * 100)
}

function describe(clock: SlaClock, item: ItemSla, now: number) {
	const openedAt = parseUtc(item.opened_at)?.valueOf() ?? now
	const pausedAt = parseUtc(item.paused_at)?.valueOf() ?? null
	const tone = SLA_STATE_META[clock.state].tone
	return {
		state: clock.state,
		detail: clockDetail(clock, openedAt, now, item.business_hours),
		used: usedPercent(clock, openedAt, now, pausedAt),
		color:
			clock.state === "paused"
				? TONE_COLOR.neutral
				: tone === "neutral"
					? "var(--primary-color)"
					: TONE_COLOR[tone]
	}
}

const clocks = computed(() => {
	if (!sla.value) return []
	const now = parseUtc(sla.value.generated_at)?.valueOf() ?? Date.now()
	return [
		{ key: "ack", title: "Response", ...describe(sla.value.ack, sla.value, now) },
		{ key: "resolve", title: "Resolution", ...describe(sla.value.resolve, sla.value, now) }
	]
})
</script>
