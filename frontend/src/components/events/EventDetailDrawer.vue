<template>
	<n-drawer v-model:show="show" display-directive="show" :trap-focus="false" style="max-width: 90vw; width: 600px">
		<n-drawer-content title="Event Details" closable :native-scrollbar="false">
			<template v-if="event">
				<div class="flex flex-col gap-1">
					<div
						v-for="[key, value] in sortedFields"
						:key
						class="field-row flex items-start gap-2 rounded px-2 py-1.5 hover:bg-[var(--hover-005-color)]"
					>
						<span class="min-w-36 shrink-0 font-mono text-xs font-semibold opacity-70">{{ key }}</span>
						<span class="min-w-0 flex-1 text-sm break-all">{{ formatValue(value) }}</span>
						<div class="actions-container flex shrink-0 gap-1">
							<n-button
								size="tiny"
								quaternary
								title="Filter for this value"
								@click="$emit('filter-add', key, String(value))"
							>
								<template #icon>
									<Icon :name="FilterAddIcon" :size="14" />
								</template>
							</n-button>
							<n-button
								size="tiny"
								quaternary
								title="Exclude this value"
								@click="$emit('filter-exclude', key, String(value))"
							>
								<template #icon>
									<Icon :name="FilterRemoveIcon" :size="14" />
								</template>
							</n-button>
						</div>
					</div>
				</div>
			</template>
			<n-empty v-else description="No event selected" class="h-48 justify-center" />
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import type { EventSearchResult } from "@/types/events.d"
import { NButton, NDrawer, NDrawerContent, NEmpty } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	event: EventSearchResult | null
}>()
defineEmits<{
	"filter-add": [field: string, value: string]
	"filter-exclude": [field: string, value: string]
}>()
const FilterAddIcon = "carbon:filter"
const FilterRemoveIcon = "carbon:filter-remove"

const show = defineModel<boolean>("show", { default: false })

const sortedFields = computed(() => {
	if (!props.event) return []
	return Object.entries(props.event)
		.filter(([key]) => !key.startsWith("_"))
		.sort(([a], [b]) => a.localeCompare(b))
})

function formatValue(value: unknown): string {
	if (value === null || value === undefined) return "-"
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}
</script>

<style scoped>
.actions-container {
	opacity: 0;
	transition: opacity 0.15s;
}

.field-row:hover .actions-container {
	opacity: 1;
}
</style>
