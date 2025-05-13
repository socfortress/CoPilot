<template>
	<div class="page page-wrapped page-mobile-full page-without-footer flex flex-col">
		<div class="relative flex h-full grow flex-col gap-4 overflow-hidden">
			<Filters class="max-mobile:px-5" @update="filters = $event" />
			<List :filters class="grow" />
		</div>
	</div>
</template>

<script setup lang="ts">
import Filters from "@/components/mitre/Filters.vue"
import List from "@/components/mitre/List.vue"
import { ref } from "vue"

const filters = ref<{ type: string; value: string }[]>([])
</script>
