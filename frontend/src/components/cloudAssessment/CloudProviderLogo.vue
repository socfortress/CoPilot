<template>
	<span class="inline-flex items-center gap-1.5" :class="label ? 'min-w-0' : 'shrink-0'" :title="PROVIDER_LABELS[provider]">
		<!-- On a white tile in both themes: AWS's wordmark is dark ink, invisible on a dark surface. -->
		<span
			class="inline-flex shrink-0 items-center justify-center rounded-md bg-white ring-1 ring-black/10"
			:style="{ width: `${tile}px`, height: `${tile}px` }"
			data-testid="cloud-provider-logo"
		>
			<Icon :name="PROVIDER_ICONS[provider]" :size="glyph" />
		</span>
		<span v-if="label" class="truncate">{{ PROVIDER_LABELS[provider] }}</span>
	</span>
</template>

<script setup lang="ts">
import type { CloudProvider } from "@/types/cloud-assessment"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { PROVIDER_ICONS, PROVIDER_LABELS } from "./utils"

const { provider, size = 16, label = false } = defineProps<{ provider: CloudProvider; size?: number; label?: boolean }>()

// The tile is the size asked for; the logo sits inside it with a little room.
const tile = computed(() => Math.round(size * 1.25))
const glyph = computed(() => Math.round(size * 0.85))
</script>
