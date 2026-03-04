<template>
	<Badge>
		<template #value>
			<div class="flex items-center gap-2">
				<PlatformIcon :platform :size="14" />
				<span class="whitespace-nowrap">{{ platformName }}</span>
			</div>
		</template>
	</Badge>
</template>

<script setup lang="ts">
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import PlatformIcon from "@/components/common/PlatformIcon.vue"
import { getOS } from "@/utils"

const { platform } = defineProps<{ platform: string }>()

const platformName = computed(() => getOS(platform))
</script>
