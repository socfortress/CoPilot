<template>
	<n-card content-class="p-0!">
		<div class="stat-card flex flex-col items-center justify-center p-4 text-center">
			<div class="label text-xs" :style="{ color: 'var(--fg-secondary-color)' }">{{ label }}</div>
			<div class="value mt-1 text-xl font-bold" :class="colorClass">
				{{ displayValue }}
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { computed, toRefs } from "vue"

const props = withDefaults(
	defineProps<{
		label: string
		value: number | null | undefined
		format?: "number" | "bytes" | "uptime" | "percent"
		decimals?: number
		colorThresholds?: { low: number; mid: number }
	}>(),
	{
		format: "number",
		decimals: 0
	}
)

const { label, value, format, decimals, colorThresholds } = toRefs(props)

function formatBytes(bytes: number): string {
	const units = ["B", "KB", "MB", "GB", "TB"]
	let i = 0
	let v = bytes
	while (v >= 1024 && i < units.length - 1) {
		v /= 1024
		i++
	}
	return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatUptime(seconds: number): string {
	const d = Math.floor(seconds / 86400)
	const h = Math.floor((seconds % 86400) / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	if (d > 0) return `${d}d ${h}h ${m}m`
	if (h > 0) return `${h}h ${m}m`
	return `${m}m`
}

const displayValue = computed(() => {
	if (value.value === null || value.value === undefined) return "—"
	const v = Number(value.value)
	switch (format.value) {
		case "bytes":
			return formatBytes(v)
		case "uptime":
			return formatUptime(v)
		case "percent":
			return `${v.toFixed(decimals.value)}%`
		default:
			return v.toFixed(decimals.value)
	}
})

const colorClass = computed(() => {
	if (!colorThresholds?.value || value.value === null || value.value === undefined) return ""
	const v = Number(value.value)
	if (v < colorThresholds.value.low) return "text-red-400"
	if (v < colorThresholds.value.mid) return "text-yellow-400"
	return "text-green-400"
})
</script>
