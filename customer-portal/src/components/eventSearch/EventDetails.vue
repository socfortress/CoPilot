<template>
	<!-- Event Detail Slide-over -->
	<div v-if="selectedEvent" class="fixed inset-0 z-50 overflow-hidden" @click="selectedEvent = null">
		<div class="absolute inset-0 bg-gray-500/50 transition-opacity"></div>
		<div class="fixed inset-y-0 right-0 flex max-w-full pl-10" @click.stop>
			<div class="w-screen max-w-lg">
				<div class="flex h-full flex-col overflow-y-scroll bg-white shadow-xl">
					<!-- Header -->
					<div class="border-b border-gray-200 bg-gray-50 px-4 py-6 sm:px-6">
						<div class="flex items-start justify-between">
							<h2 class="text-lg font-medium text-gray-900">Event Details</h2>
							<button
								class="rounded-md text-gray-400 hover:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
								@click="selectedEvent = null"
							>
								<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M6 18L18 6M6 6l12 12"
									></path>
								</svg>
							</button>
						</div>
					</div>

					<!-- Fields -->
					<div class="flex-1 px-4 py-4 sm:px-6">
						<dl class="divide-y divide-gray-200">
							<div
								v-for="[key, value] in sortedEventFields"
								:key
								class="group flex items-start justify-between py-3"
							>
								<dt class="min-w-0 shrink-0 font-mono text-xs font-semibold text-gray-500">
									{{ key }}
								</dt>
								<dd class="ml-4 min-w-0 flex-1 text-right text-sm break-all text-gray-900">
									{{ formatValue(value) }}
								</dd>
								<div
									class="ml-2 flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100"
								>
									<button
										title="Filter for this value"
										class="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
										@click="addFilter(key, String(value))"
									>
										<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 4v16m8-8H4"
											></path>
										</svg>
									</button>
									<button
										title="Exclude this value"
										class="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
										@click="excludeFilter(key, String(value))"
									>
										<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M20 12H4"
											></path>
										</svg>
									</button>
								</div>
							</div>
						</dl>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { EventSearchResult } from "@/types/siem"
import { computed, toRefs } from "vue"

const props = defineProps<{
	event: EventSearchResult | null
}>()

const emit = defineEmits<{
	(e: "filter-add", field: string, value: string): void
	(e: "filter-exclude", field: string, value: string): void
}>()

// -- Event detail --
const { event: selectedEvent } = toRefs(props)

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
</script>
