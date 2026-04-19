<template>
	<span class="inline-flex items-center gap-2">
		{{ value?.toString().trim() || "—" }}

		<n-tooltip v-if="value?.toString().trim()" class="px-2! py-1!">
			<template #trigger>
				<n-button v-if="isSupported" text @click="copy(value.toString())">
					<template #icon>
						<Icon name="carbon:copy" :size="12" />
					</template>
				</n-button>
			</template>
			<span class="text-xs">{{ copied ? "Copied" : "Copy" }}</span>
		</n-tooltip>
	</span>
</template>

<script setup lang="ts">
import { useClipboard } from "@vueuse/core"
import { NButton, NTooltip } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const { value } = defineProps<{ value: string | number | null }>()

const { copy, copied, isSupported } = useClipboard()
</script>
