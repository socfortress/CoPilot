<template>
	<!-- Every tab panel is a lazily-loaded chunk. Without a fallback the panel is
	     blank for as long as the chunk takes, which reads as an empty tab rather
	     than as one that is still arriving. -->
	<div class="flex flex-col gap-3 py-2" aria-busy="true">
		<n-skeleton text :height="14" class="w-1/4" />
		<n-skeleton :height="140" :sharp="false" class="rounded-lg" />
		<n-skeleton text :repeat="2" :height="14" />
	</div>
</template>

<script setup lang="ts">
import { NSkeleton } from "naive-ui"
</script>
