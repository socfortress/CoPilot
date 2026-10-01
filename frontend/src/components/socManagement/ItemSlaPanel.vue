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
			<span v-if="sla.reopen_count" class="text-tertiary font-mono text-xs">
				reopened {{ sla.reopen_count }}×
			</span>
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

/** "12m of 1h · ana" once met or late, "6h 20m left of 8h" while running. */
function clockDetail(clock: SlaClock, openedAt: number, now: number): string {
	const due = parseUtc(clock.due_at)?.valueOf() ?? null
	const achieved = parseUtc(clock.achieved_at)?.valueOf() ?? null
	const target = formatTarget(clock.target_minutes)
	if (clock.state === "not_tracked") return "no target for this severity"
	if (achieved != null)
		return `${formatDuration((achieved - openedAt) / 1000)} of ${target}${clock.by ? ` · ${clock.by}` : ""}`
	if (due == null) return "—"
	if (now > due) return `${formatDuration((now - due) / 1000)} past ${target}`
	return `${formatDuration((due - now) / 1000)} left of ${target}`
}

function describe(clock: SlaClock, opened: string, now: number) {
	const openedAt = parseUtc(opened)?.valueOf() ?? now
	const achieved = parseUtc(clock.achieved_at)?.valueOf() ?? null
	const target = clock.target_minutes ? clock.target_minutes * 60_000 : null
	const used = target ? (((achieved ?? now) - openedAt) / target) * 100 : 0
	const tone = SLA_STATE_META[clock.state].tone
	return {
		state: clock.state,
		detail: clockDetail(clock, openedAt, now),
		used: Math.max(0, used),
		color: tone === "neutral" ? "var(--primary-color)" : TONE_COLOR[tone]
	}
}

const clocks = computed(() => {
	if (!sla.value) return []
	const now = parseUtc(sla.value.generated_at)?.valueOf() ?? Date.now()
	return [
		{ key: "ack", title: "Response", ...describe(sla.value.ack, sla.value.opened_at, now) },
		{ key: "resolve", title: "Resolution", ...describe(sla.value.resolve, sla.value.opened_at, now) }
	]
})
</script>
