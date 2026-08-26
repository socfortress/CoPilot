<template>
	<!--
		The first paint of the detail page.

		It mirrors the real layout block for block — header row, chip strip, overview
		card with its VirusTotal panel and fact grid, tab bar, panel — so the page
		does not visibly reflow when the data lands: the boxes are already where they
		will be, and only their contents change.

		Without it the page arrived in pieces (empty header, then one lone tab, then
		five more as the result filled in), which reads as something going wrong
		rather than as something loading.
	-->
	<div class="flex flex-col gap-4" aria-busy="true" aria-label="Loading analysis">
		<header class="flex flex-col gap-3">
			<div class="flex flex-wrap items-center gap-x-4 gap-y-3">
				<div class="flex min-w-0 grow basis-72 items-center gap-3">
					<n-skeleton :height="28" :width="96" :sharp="false" class="shrink-0 rounded-full" />
					<n-skeleton :height="20" :width="20" circle />
					<n-skeleton text :height="22" class="max-w-80 min-w-0 grow" />
				</div>
				<n-skeleton :height="28" :width="150" :sharp="false" class="ml-auto shrink-0 rounded-md" />
			</div>

			<div class="flex flex-wrap items-center gap-2">
				<n-skeleton v-for="w of CHIP_WIDTHS" :key="w" :height="22" :width="w" :sharp="false" class="rounded-md" />
			</div>
		</header>

		<div class="border-default flex flex-col overflow-hidden rounded-lg border">
			<div class="border-default flex flex-col gap-3 border-b p-4 lg:flex-row lg:gap-6">
				<div class="flex min-w-0 grow flex-col gap-2">
					<n-skeleton text :height="12" :width="120" />
					<n-skeleton text :repeat="2" :height="14" />
				</div>
				<div class="border-default bg-secondary shrink-0 rounded-lg border p-4 lg:w-96">
					<n-skeleton text :height="12" :width="90" class="mb-3" />
					<n-skeleton text :repeat="3" :height="14" />
				</div>
			</div>

			<div class="bg-border grid gap-px sm:grid-cols-2 lg:grid-cols-4">
				<div v-for="n of FACT_CELLS" :key="n" class="bg-secondary flex min-h-20 flex-col gap-2 p-4">
					<n-skeleton text :height="12" :width="70" />
					<n-skeleton text :height="16" class="w-4/5" />
				</div>
			</div>
		</div>

		<div class="border-default flex items-center gap-6 border-b pb-2">
			<n-skeleton v-for="w of TAB_WIDTHS" :key="w" text :height="16" :width="w" />
		</div>

		<div class="flex flex-col gap-3">
			<n-skeleton text :height="14" class="w-1/3" />
			<n-skeleton :height="180" :sharp="false" class="rounded-lg" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { NSkeleton } from "naive-ui"

// Uneven widths on purpose: a column of identical bars reads as a graphic, while
// ragged ones read as text that has not arrived yet.
const CHIP_WIDTHS = [110, 90, 150, 80]
const TAB_WIDTHS = [54, 58, 40, 76, 64]
const FACT_CELLS = 8
</script>
