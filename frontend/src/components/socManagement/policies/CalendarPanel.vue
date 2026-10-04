<template>
	<PanelSegment
		:title="scope ? `${scopeName} — business hours` : 'Business hours'"
		:caption
		data-testid="calendar-panel"
	>
		<template #actions>
			<n-tag size="small" :bordered="false" :type="SOURCE_META[source].type" round data-testid="calendar-source">
				<template #icon><Icon :name="SOURCE_META[source].icon" :size="12" /></template>
				{{ SOURCE_META[source].label }}
			</n-tag>
			<n-popconfirm v-if="isAdmin && hasOwn" @positive-click="onRemove">
				<template #trigger>
					<n-button size="tiny" quaternary type="error" :loading="saving" data-testid="calendar-remove">
						<template #icon><Icon name="carbon:reset" /></template>
						Follow global
					</n-button>
				</template>
				Remove {{ scope }}'s calendar? It will follow the global business hours again.
			</n-popconfirm>
		</template>

		<p class="text-secondary m-0 mb-4 text-xs leading-relaxed">
			Cells counted in
			<strong>business hours</strong>
			only spend these windows: an item opened on Friday evening starts counting on Monday morning, and a weekend
			or a holiday never breaches a target.
			<template v-if="scope && source !== 'customer'">
				{{ scopeName }} follows the {{ source === "global" ? "global calendar" : "built-in default" }} until you
				save one of its own.
			</template>
		</p>

		<n-alert v-if="loadError" type="error" :bordered="false" class="mb-4">
			Could not load the calendar: {{ loadError }}
		</n-alert>

		<n-spin :show="loading">
			<div v-if="draft" class="flex flex-col gap-5">
				<div class="flex flex-wrap items-center gap-x-6 gap-y-2">
					<label class="flex items-center gap-2 text-sm">
						<Icon name="carbon:earth" :size="14" class="text-tertiary" />
						<span class="text-secondary">Timezone</span>
						<n-select
							v-model:value="draft.timezone"
							:options="zones"
							filterable
							size="small"
							:disabled="!isAdmin"
							class="w-60!"
							data-testid="calendar-timezone"
						/>
					</label>
					<span class="text-tertiary font-mono text-xs" data-testid="calendar-weekly-hours">
						{{ weeklyHours }} working hours / week
					</span>
				</div>

				<WeekScheduleEditor v-model="draft.week" :readonly="!isAdmin" />

				<div class="flex flex-col gap-2">
					<span :class="SECTION_LABEL">Holidays</span>
					<HolidayList v-model="draft.holidays" :readonly="!isAdmin" />
				</div>
			</div>
		</n-spin>

		<template v-if="isAdmin" #footer>
			<label class="flex items-center gap-2 text-sm">
				<n-switch v-model:value="applyToOpen" size="small" data-testid="calendar-apply-open" />
				<span>Re-time open business-hours items</span>
			</label>
			<div class="flex items-center gap-2">
				<span v-if="error" class="inline-flex items-center gap-1 text-xs" :style="{ color: TONE_COLOR.bad }">
					<Icon name="carbon:warning-filled" :size="13" />
					{{ error }}
				</span>
				<n-button size="small" :disabled="!dirty || saving" @click="discard">Discard</n-button>
				<n-button
					size="small"
					type="primary"
					:disabled="!canSave"
					:loading="saving"
					data-testid="calendar-save"
					@click="onSave"
				>
					<template #icon><Icon name="carbon:save" /></template>
					Save calendar
				</n-button>
			</div>
		</template>
	</PanelSegment>
</template>

<script setup lang="ts">
// The business-hours calendar of the policy scope being edited. A customer without one
// follows the global calendar, and the global one falls back to Monday–Friday
// 09:00–17:00 UTC — the source tag always says which applies.
import type { CalendarSource } from "@/types/soc-management"
import { NAlert, NButton, NPopconfirm, NSelect, NSpin, NSwitch, NTag, useMessage } from "naive-ui"
import { computed, shallowRef, toRef, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useBusinessCalendar } from "../composables/useBusinessCalendar"
import PanelSegment from "../ui/PanelSegment.vue"
import { TONE_COLOR } from "../utils"
import { timezoneOptions, weeklyMinutes } from "./calendar"
import HolidayList from "./HolidayList.vue"
import WeekScheduleEditor from "./WeekScheduleEditor.vue"

const props = defineProps<{ scope: string | null; scopeName: string | null; isAdmin: boolean }>()
const emit = defineEmits<{ (e: "changed", customersWithCalendar: string[]): void }>()

const SOURCE_META: Record<CalendarSource, { label: string; icon: string; type: "success" | "info" | "default" }> = {
	customer: { label: "Customer calendar", icon: "carbon:user-profile", type: "success" },
	global: { label: "Global calendar", icon: "carbon:earth", type: "info" },
	default: { label: "Built-in default", icon: "carbon:settings", type: "default" }
}

const message = useMessage()
const applyToOpen = shallowRef(false)
const {
	draft,
	source,
	customersWithCalendar,
	loading,
	saving,
	loadError,
	dirty,
	error,
	hasOwn,
	save,
	remove,
	discard
} = useBusinessCalendar(toRef(props, "scope"))

const zones = computed(() => timezoneOptions(draft.value?.timezone))
const weeklyHours = computed(() => (draft.value ? Math.round((weeklyMinutes(draft.value) / 60) * 10) / 10 : 0))
// A scope that follows another (a customer following the global calendar, the global
// one still on the built-in default) can save the calendar it shows as its own, unchanged.
const ownSource = computed<CalendarSource>(() => (props.scope ? "customer" : "global"))
const canSave = computed(() => !!draft.value && !error.value && (dirty.value || source.value !== ownSource.value))
const caption = computed(() =>
	props.scope ? "overrides the global calendar" : "applies to every customer without one"
)

async function report(result: Promise<{ ok: boolean; message: string }>) {
	const { ok, message: text } = await result
	if (ok) {
		message.success(text)
		applyToOpen.value = false
	} else {
		message.error(text)
	}
}

function onSave() {
	report(save(applyToOpen.value))
}

function onRemove() {
	report(remove(applyToOpen.value))
}

watch(customersWithCalendar, codes => emit("changed", codes))
</script>
