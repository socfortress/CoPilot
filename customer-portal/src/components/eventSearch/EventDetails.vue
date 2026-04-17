<template>
	<n-drawer v-model:show="showDrawer" :width="600" class="max-w-[90vw]" :trap-focus="false">
		<n-drawer-content title="Event Details" closable :native-scrollbar="false">
			<div class="divide-border divide-y">
				<div
					v-for="[key, value] in sortedEventFields"
					:key
					class="group flex items-start justify-between gap-5 py-3"
				>
					<div class="shrink-0 font-mono text-xs font-semibold">
						{{ key }}
					</div>
					<div class="flex items-start justify-end gap-2">
						<div class="flex-1 text-right text-sm break-all">
							{{ formatValue(value) }}
						</div>
						<div
							class="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100"
						>
							<n-button title="Filter for this value" text @click="addFilter(key, String(value))">
								<template #icon>
									<Icon name="carbon:add" />
								</template>
							</n-button>
							<n-button title="Exclude this value" text @click="excludeFilter(key, String(value))">
								<template #icon>
									<Icon name="carbon:subtract" />
								</template>
							</n-button>
						</div>
					</div>
				</div>
			</div>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="tsx">
import type { EventSearchResult } from "@/types/siem"
import { NButton, NDrawer, NDrawerContent } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	event: EventSearchResult | null
}>()

const emit = defineEmits<{
	(e: "filter-add", field: string, value: string): void
	(e: "filter-exclude", field: string, value: string): void
	(e: "close"): void
}>()

const { event: selectedEvent } = toRefs(props)

const showDrawer = ref<boolean>(false)

const sortedEventFields = computed(() => {
	if (!selectedEvent.value) return []
	return Object.entries(selectedEvent.value)
		.filter(([key]) => !key.startsWith("_"))
		.sort(([a], [b]) => a.localeCompare(b))
})

function addFilter(field: string, value: string) {
	emit("filter-add", field, value)
}

function excludeFilter(field: string, value: string) {
	emit("filter-exclude", field, value)
}

function formatValue(value: unknown): string {
	if (value === null || value === undefined) return "-"
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}

watch(selectedEvent, newVal => {
	if (newVal) {
		showDrawer.value = true
	}
})

watch(showDrawer, newVal => {
	if (!newVal) {
		emit("close")
	}
})
</script>
