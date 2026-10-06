<template>
	<div class="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2" data-testid="uba-toolbar">
		<div class="flex flex-wrap items-center gap-2">
			<slot />
		</div>
		<div v-if="$slots.summary || $slots.hint" class="flex items-center gap-3">
			<span v-if="$slots.summary" class="text-tertiary font-mono text-[11px] tabular-nums" data-testid="uba-toolbar-summary">
				<slot name="summary" />
			</span>
			<n-popover v-if="$slots.hint" trigger="click" placement="bottom-end" style="max-width: 360px">
				<template #trigger>
					<n-button size="tiny" quaternary data-testid="uba-toolbar-hint">
						<template #icon><Icon name="carbon:information" :size="14" /></template>
						How it works
					</n-button>
				</template>
				<p class="m-0 text-xs leading-relaxed" data-testid="uba-toolbar-hint-text"><slot name="hint" /></p>
			</n-popover>
		</div>
	</div>
</template>

<script setup lang="ts">
// The row above a UBA list, always one line: its controls on the left (no field labels: placeholders
// and icons say what they are); on the right a short mono summary of what is listed and, when the
// list needs explaining, a "How it works" button that opens the explanation instead of printing it.
import { NButton, NPopover } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
</script>
