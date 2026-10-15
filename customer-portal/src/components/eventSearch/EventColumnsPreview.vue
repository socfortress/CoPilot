<template>
	<div class="flex min-w-0 flex-col gap-2" data-testid="columns-preview">
		<div class="flex items-baseline justify-between gap-3">
			<span :class="HEAD" class="truncate">{{ title }}</span>
			<span class="text-tertiary shrink-0 font-mono text-xs tabular-nums">
				{{ columns.length }} {{ columns.length === 1 ? "column" : "columns" }}
			</span>
		</div>

		<!-- Every column, in display order: its position, its header, the field it reads. -->
		<div class="border-default overflow-hidden rounded-md border">
			<div
				class="bg-secondary border-default text-tertiary grid grid-cols-[1.75rem_minmax(0,1fr)_minmax(0,1.2fr)] border-b text-xxs font-medium tracking-[0.12em] uppercase"
			>
				<span class="px-2 py-1 text-right">#</span>
				<span class="px-2 py-1">Header</span>
				<span class="px-2 py-1">Field</span>
			</div>
			<div class="divide-border flex max-h-64 flex-col divide-y overflow-y-auto">
				<div
					v-for="(column, index) of columns"
					:key="`${index}-${column.key}`"
					class="grid grid-cols-[1.75rem_minmax(0,1fr)_minmax(0,1.2fr)] items-baseline"
					data-testid="columns-preview-column"
				>
					<span class="text-tertiary px-2 py-1 text-right font-mono text-xs tabular-nums">{{ index + 1 }}</span>
					<span class="text-default truncate px-2 py-1 text-xs" :title="column.label">{{ column.label }}</span>
					<span
						class="text-secondary truncate px-2 py-1 font-mono text-xs [font-variant-ligatures:none]"
						:title="columnSource(column, timeField)"
					>
						{{ columnSource(column, timeField) }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { EventColumn } from "./eventColumns"
import { columnSource } from "./eventColumns"

/**
 * A compact look at a column layout (#1258): every column in display order, with its header
 * and the field it reads. What the table would show, not what it would contain.
 */

const { columns, title, timeField } = defineProps<{
	columns: EventColumn[]
	title: string
	timeField?: string | null
}>()

const HEAD = "text-tertiary text-xxs font-medium tracking-[0.12em] uppercase"
</script>
