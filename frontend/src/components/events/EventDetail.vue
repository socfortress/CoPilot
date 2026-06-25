<template>
	<div v-if="event" class="flex flex-col gap-3">
		<div class="flex items-center justify-between gap-3">
			<p class="text-secondary text-[10px] font-medium tracking-widest uppercase">Event fields</p>
			<span class="text-default font-mono text-xs tabular-nums">{{ sortedFields.length }}</span>
		</div>

		<dl class="border-border divide-border divide-y rounded-lg border">
			<div
				v-for="[key, value] in sortedFields"
				:key
				class="group hover:bg-hover-005 flex items-start gap-3 px-3 py-2.5 transition-colors"
			>
				<dt class="text-secondary max-w-44 min-w-36 shrink-0 truncate font-mono text-xs" :title="key">
					{{ key }}
				</dt>
				<dd class="flex min-w-0 flex-1 items-start justify-end gap-3">
					<span class="text-default min-w-0 flex-1 text-right font-mono text-xs break-all">
						{{ formatValue(value) }}
					</span>
					<div class="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
						<n-tooltip placement="top" class="px-2! py-1! text-xs!">
							<template #trigger>
								<n-button size="tiny" quaternary @click="emit('filter-add', key, String(value))">
									<template #icon>
										<Icon :name="FilterAddIcon" :size="14" />
									</template>
								</n-button>
							</template>
							Include in query
						</n-tooltip>
						<n-tooltip placement="top" class="px-2! py-1! text-xs!">
							<template #trigger>
								<n-button size="tiny" quaternary @click="emit('filter-exclude', key, String(value))">
									<template #icon>
										<Icon :name="FilterRemoveIcon" :size="14" />
									</template>
								</n-button>
							</template>
							Exclude from query
						</n-tooltip>
					</div>
				</dd>
			</div>
		</dl>
	</div>

	<n-empty v-else description="No event selected" class="h-48 justify-center" />
</template>

<script setup lang="ts">
import type { SafeAny } from "@/types/common"
import type { EventSearchResult } from "@/types/events"
import { NButton, NEmpty, NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	event: EventSearchResult | null
}>()

const emit = defineEmits<{
	"filter-add": [field: string, value: string]
	"filter-exclude": [field: string, value: string]
}>()

const FilterAddIcon = "carbon:filter"
const FilterRemoveIcon = "carbon:filter-remove"

const sortedFields = computed(() => {
	if (!props.event) return []
	return Object.entries(props.event)
		.filter(([key]) => !key.startsWith("_"))
		.sort(([a], [b]) => a.localeCompare(b))
})

function formatValue(value: SafeAny): string {
	if (value === null || value === undefined) return "—"
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}
</script>
