<template>
	<Badge>
		<template #iconLeft>
			<PlatformIcon :platform :size="14" />
		</template>
		<template #value>
			<span class="whitespace-nowrap">{{ platformName }}</span>
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
