<template>
	<div
		data-testid="waiting-on-you"
		class="border-waiting/40 bg-waiting/5 mb-4 flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border px-4 py-3"
		role="status"
	>
		<Icon name="carbon:user-follow" :size="22" class="text-waiting shrink-0" />
		<div class="min-w-0 grow basis-64">
			<div class="font-semibold">{{ $t("common.waitingOnYou.title") }}</div>
			<div class="text-secondary text-sm">
				{{ entity === "case" ? $t("common.waitingOnYou.body.case") : $t("common.waitingOnYou.body.alert") }}
			</div>
		</div>
		<n-button size="small" type="primary" secondary data-testid="waiting-on-you-reply" @click="emit('reply')">
			<template #icon>
				<Icon name="carbon:reply" />
			</template>
			{{ $t("common.waitingOnYou.reply") }}
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
