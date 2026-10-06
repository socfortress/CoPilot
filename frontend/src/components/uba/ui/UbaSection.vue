<template>
	<section class="flex flex-col gap-2.5" :data-testid="testId">
		<header class="flex min-h-6 flex-wrap items-center justify-between gap-2">
			<div class="flex min-w-0 items-baseline gap-2">
				<span :class="SECTION_LABEL" class="shrink-0">{{ title }}</span>
				<span v-if="caption" class="text-tertiary min-w-0 truncate font-mono text-[11px]">{{ caption }}</span>
			</div>
			<div v-if="$slots.actions" class="flex items-center gap-2">
				<slot name="actions" />
			</div>
		</header>
		<p v-if="$slots.description" class="text-tertiary m-0 -mt-1 max-w-3xl text-xs leading-relaxed">
			<slot name="description" />
		</p>
		<slot />
	</section>
</template>

<script setup lang="ts">
// One block of a UBA drawer or tab: a section label, an optional mono caption (a count, a window)
// and actions on the right, an optional one-paragraph description, then the content. The same
// rhythm everywhere in the UBA page.
import { SECTION_LABEL } from "@/components/common/section-label"

const { title, caption, testId } = defineProps<{ title: string; caption?: string; testId?: string }>()
</script>
