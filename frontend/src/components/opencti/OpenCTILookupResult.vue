<template>
	<div class="flex flex-col gap-3">
		<div v-if="!lookup.found" class="bg-secondary text-secondary rounded-lg border px-4 py-3 text-sm">
			<span class="font-mono break-all">{{ lookup.value }}</span>
			is not in OpenCTI.
		</div>
		<template v-else>
			<OpenCTIObservableCard v-for="observable of lookup.observables" :key="observable.id" :observable />
			<div v-if="lookup.total > lookup.observables.length" class="text-secondary text-xs">
				Showing {{ lookup.observables.length }} of {{ lookup.total }} matching observables.
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { OpenCTIObservableLookup } from "@/types/opencti"
import OpenCTIObservableCard from "./OpenCTIObservableCard.vue"

// One value can match several observables — the same string stored as both a
// Domain-Name and a Hostname — so every match gets its own card.
defineProps<{
	lookup: OpenCTIObservableLookup
}>()
</script>
