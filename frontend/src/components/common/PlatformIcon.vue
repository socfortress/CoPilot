<template>
	<Icon :name="platformIcon" :size />
</template>

<script setup lang="ts">
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { getOS, iconFromOs } from "@/utils"

const { platform, size = 14 } = defineProps<{ platform: string; size?: number }>()

const platformIcon = computed(() => iconFromOs(getOS(platform)))
</script>
