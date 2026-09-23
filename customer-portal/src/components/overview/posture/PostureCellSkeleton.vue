<template>
	<!-- Same heights as the loaded cell (headline 34, bar 6, legend 16): no layout shift. -->
	<n-skeleton :height="34" :width="96" :sharp="false" />
	<n-skeleton :height="6" :sharp="false" />
	<n-skeleton :height="16" :width="220" :sharp="false" />
</template>

<script setup lang="ts">
import { NSkeleton } from "naive-ui"
</script>
