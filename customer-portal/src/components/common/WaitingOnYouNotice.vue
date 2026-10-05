<template>
	<div
		data-testid="waiting-on-you"
		class="border-primary/40 bg-primary/5 mb-4 flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border px-4 py-3"
		role="status"
	>
		<Icon name="carbon:user-follow" :size="22" class="text-primary shrink-0" />
		<div class="min-w-0 grow basis-64">
			<div class="font-semibold">The SOC is waiting on your reply</div>
			<div class="text-secondary text-sm">
				Their response clock for this {{ entity }} is paused until you answer. Reply in the comments to
				hand it back to the analysts.
			</div>
		</div>
		<n-button size="small" type="primary" secondary data-testid="waiting-on-you-reply" @click="emit('reply')">
			<template #icon>
				<Icon name="carbon:reply" />
			</template>
			Reply
		</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	entity: "alert" | "case"
}>()

const emit = defineEmits<{
	reply: []
}>()
</script>
