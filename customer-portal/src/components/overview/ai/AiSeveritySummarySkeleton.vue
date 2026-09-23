<template>
	<!-- Mirrors AiSeveritySummary: headline row 29px, bar 6px, legend lines 16px. -->
	<div class="flex flex-col gap-4 p-5">
		<div class="flex h-[29px] items-center gap-2">
			<n-skeleton :height="26" :width="28" :sharp="false" />
			<n-skeleton :height="10" :width="96" :sharp="false" />
		</div>
		<n-skeleton :height="6" :sharp="false" />
		<div class="flex flex-col gap-1.5">
			<div
				v-for="(width, index) of LEGEND_WIDTHS"
				:key="index"
				class="flex h-4 items-center justify-between gap-3"
			>
				<n-skeleton :height="9" :width :sharp="false" />
				<n-skeleton :height="9" :width="10" :sharp="false" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NSkeleton } from "naive-ui"

const LEGEND_WIDTHS = ["38%", "52%"]
</script>
